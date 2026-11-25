import asyncio
import os
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from uuid import uuid4

import pytest
from shared.contracts.permission import RiskLevel
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus, TaskType

from app.core.events import Event, EventType, get_event_bus
from app.core.permissions.policies import SafeExecutionPolicy
from app.tools.browser.controller import BrowserActionError, BrowserController
from app.tools.browser.interface import BrowserAdapter


class MockLoginServer:
    """Lightweight local HTTP server for testing human handoff login walls."""

    def __init__(self):
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int = 0
        self.is_logged_in = False

    def start(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/login":
                    if parent.is_logged_in:
                        # Redirect to dashboard
                        self.send_response(302)
                        self.send_header("Location", "/dashboard")
                        self.end_headers()
                        return

                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head><title>Sign in to Service</title></head>
                    <body>
                        <h2>Sign in</h2>
                        <form action="/login" method="post">
                            <input type="text" name="username" placeholder="Username" />
                            <input type="password" name="password" placeholder="Password" />
                            <button type="submit">Sign in</button>
                        </form>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode("utf-8"))

                elif self.path == "/dashboard":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head><title>Dashboard</title></head>
                    <body>
                        <h1>Welcome to Dashboard</h1>
                        <button id="submit-order-btn">Submit Order</button>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body>Home</body></html>")

            def do_POST(self):
                if self.path == "/login":
                    parent.is_logged_in = True
                    self.send_response(302)
                    self.send_header("Location", "/dashboard")
                    self.end_headers()

            def log_message(self, format, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


@pytest.fixture
def mock_server():
    server = MockLoginServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def temp_profile_dir():
    temp_dir = tempfile.mkdtemp(prefix="browser_agent_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# =========================================================================
# TEST 1: VISIBLE AGENT CURSOR OVERLAY
# =========================================================================


@pytest.mark.asyncio
async def test_agent_cursor_overlay_present_in_dom(temp_profile_dir):
    """Verifies that the agent cursor overlay and styles are injected into the page DOM."""
    controller = BrowserController(permission_manager=False, user_data_dir=temp_profile_dir)
    try:
        res = await controller.start_session(headless=True, persistent=True)
        assert res.success is True

        nav_res = await controller.navigate("data:text/html,<html><body><h1>Test Page</h1></body></html>", auto_handoff=False)
        assert nav_res.success is True

        # Check DOM for injected cursor and styles
        cursor_count = await controller.page.locator("#__antigravity_agent_cursor__").count()
        assert cursor_count == 1, "Agent cursor overlay element must be present in the page DOM"

        style_count = await controller.page.locator("#__antigravity_cursor_styles__").count()
        assert style_count == 1, "Agent cursor CSS styles must be present in the page DOM"

        # Test cursor movement helper
        await controller._animate_cursor(150.0, 200.0, click=True)
    finally:
        await controller.close_session()


# =========================================================================
# TEST 2: PERSISTENT BROWSER SESSION ACROSS TWO RUNS
# =========================================================================


@pytest.mark.asyncio
async def test_browser_session_persistence_across_two_runs(temp_profile_dir, mock_server):
    """Verifies that cookies/localStorage survive browser restarts with persistent context."""
    test_url = f"http://127.0.0.1:{mock_server.port}/"

    # RUN 1: Start session, set state in localStorage, and close
    c1 = BrowserController(permission_manager=False, user_data_dir=temp_profile_dir)
    try:
        await c1.start_session(headless=True, persistent=True)
        await c1.navigate(test_url, auto_handoff=False)

        await c1.page.evaluate("() => localStorage.setItem('agent_session_key', 'persisted_12345')")
        saved_val = await c1.page.evaluate("() => localStorage.getItem('agent_session_key')")
        assert saved_val == "persisted_12345"
    finally:
        await c1.close_session()

    # RUN 2: Re-open with the same user-data-dir and verify state is intact
    c2 = BrowserController(permission_manager=False, user_data_dir=temp_profile_dir)
    try:
        await c2.start_session(headless=True, persistent=True)
        await c2.navigate(test_url, auto_handoff=False)

        persisted_val = await c2.page.evaluate("() => localStorage.getItem('agent_session_key')")
        assert persisted_val == "persisted_12345", "Storage state must persist across sessions with persistent context"
    finally:
        await c2.close_session()


# =========================================================================
# TEST 3: HUMAN HANDOFF PAUSE & RESUME
# =========================================================================


@pytest.mark.asyncio
async def test_human_handoff_pause_and_resume(temp_profile_dir, mock_server):
    """
    Verifies human handoff flow:
    1. Detects login barrier on /login
    2. Emits 'task.needs_human' EventBus event with reason & screenshot
    3. Keeps browser open while paused
    4. Resumes on resume signal once wall is cleared
    """
    controller = BrowserController(permission_manager=False, user_data_dir=temp_profile_dir)
    event_bus = get_event_bus()

    received_events = []

    async def on_needs_human(evt: Event):
        received_events.append(evt)

    event_bus.subscribe("task.needs_human", on_needs_human)

    try:
        await controller.start_session(headless=True, persistent=True)
        login_url = f"http://127.0.0.1:{mock_server.port}/login"

        # Navigate in background task because it will pause for handoff
        wf_id = uuid4()
        t_id = uuid4()

        handoff_task = asyncio.create_task(
            controller.navigate(
                login_url,
                auto_handoff=True,
                handoff_timeout=15.0,
                workflow_id=wf_id,
                task_id=t_id,
            )
        )

        # Wait briefly for detection and pause
        await asyncio.sleep(0.8)

        # Verify event was emitted
        assert len(received_events) >= 1
        handoff_evt = received_events[0]
        assert "login" in str(handoff_evt.payload.get("url", "")).lower()
        assert "Password" in handoff_evt.payload.get("reason", "") or "Sign-in" in handoff_evt.payload.get("reason", "")
        assert handoff_evt.payload.get("status") == "WAITING_FOR_HUMAN"
        assert handoff_evt.payload.get("screenshot") is not None
        assert controller._handoff_active is True

        # Verify browser remains open while waiting
        assert controller.page is not None

        # Simulate user logging in on the mock server
        mock_server.is_logged_in = True

        # Human clicks Resume button (which calls resume_human_handoff)
        await controller.page.goto(f"http://127.0.0.1:{mock_server.port}/dashboard")
        resumed = controller.resume_human_handoff(workflow_id=wf_id, task_id=t_id)
        assert resumed is True

        # Task finishes without error
        res = await handoff_task
        assert res.success is True
        assert controller._handoff_active is False
    finally:
        event_bus.unsubscribe("task.needs_human", on_needs_human)
        await controller.close_session()


@pytest.mark.asyncio
async def test_human_handoff_timeout_fails_cleanly(temp_profile_dir, mock_server):
    """Verifies that human handoff raises a clear timeout error if not resumed."""
    controller = BrowserController(permission_manager=False, user_data_dir=temp_profile_dir)
    try:
        await controller.start_session(headless=True, persistent=True)
        login_url = f"http://127.0.0.1:{mock_server.port}/login"

        # Set a short timeout for test
        res = await controller.navigate(login_url, auto_handoff=True, handoff_timeout=0.6)
        assert res.success is False
        assert "timed out" in res.error.lower()
    finally:
        await controller.close_session()


# =========================================================================
# TEST 4: PERMISSION MANAGER RISK GATING
# =========================================================================


def test_permission_manager_gating_high_risk_actions():
    """Verifies that opening new sites and clicking submit/delete/pay are gated as HIGH risk."""
    # 1. Opening new external sites
    nav_risk = SafeExecutionPolicy.classify_risk(
        "navigate",
        context={"url": "https://untrusted-new-domain.org/checkout"},
    )
    assert nav_risk == RiskLevel.HIGH, "Opening new untrusted sites must be classified as HIGH risk"

    # Explicit new_site flag
    new_site_risk = SafeExecutionPolicy.classify_risk(
        "browser_navigate",
        context={"url": "https://example.com", "new_site": True},
    )
    assert new_site_risk == RiskLevel.HIGH

    # 2. Clicking submit, delete, pay, checkout
    submit_click_risk = SafeExecutionPolicy.classify_risk(
        "interact",
        context={"selector": "button#submit-order", "interaction_action": "click"},
    )
    assert submit_click_risk == RiskLevel.HIGH, "Clicks with 'submit' selector must be classified as HIGH risk"

    pay_click_risk = SafeExecutionPolicy.classify_risk(
        "interact",
        context={"selector": ".pay-now-button", "interaction_action": "click"},
    )
    assert pay_click_risk == RiskLevel.HIGH, "Clicks with 'pay' selector must be classified as HIGH risk"

    delete_click_risk = SafeExecutionPolicy.classify_risk(
        "interact",
        context={"selector": "a.delete-account", "interaction_action": "click"},
    )
    assert delete_click_risk == RiskLevel.HIGH, "Clicks with 'delete' selector must be classified as HIGH risk"

    # Normal harmless click remains MEDIUM/LOW
    normal_click_risk = SafeExecutionPolicy.classify_risk(
        "interact",
        context={"selector": "#tab-overview", "interaction_action": "click"},
    )
    assert normal_click_risk == RiskLevel.MEDIUM
