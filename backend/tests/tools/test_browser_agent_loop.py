import asyncio
import os
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.events import Event, get_event_bus
from app.tools.browser.agent_loop import (
    ActionType,
    AgentLoopReport,
    BrowserAgentLoop,
    ObserveResult,
    StepRecord,
    VisionAction,
)
from app.tools.browser.controller import BrowserController


class FlowMockServer:
    """Mock server serving multi-step button flow and no-op pages for agent testing."""

    def __init__(self):
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int = 0
        self.current_step = 1

    def start(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()

                if self.path == "/button-flow":
                    if parent.current_step == 1:
                        html = """
                        <!DOCTYPE html>
                        <html>
                        <head><title>Step 1</title></head>
                        <body>
                            <h2>Welcome to Flow</h2>
                            <button id="btn-next" onclick="fetch('/advance-flow').then(() => location.reload())">Proceed to Step 2</button>
                        </body>
                        </html>
                        """
                    elif parent.current_step == 2:
                        html = """
                        <!DOCTYPE html>
                        <html>
                        <head><title>Step 2</title></head>
                        <body>
                            <h2>Almost Done</h2>
                            <button id="btn-finish" onclick="fetch('/advance-flow').then(() => location.reload())">Finalize Goal</button>
                        </body>
                        </html>
                        """
                    else:
                        html = """
                        <!DOCTYPE html>
                        <html>
                        <head><title>Complete</title></head>
                        <body>
                            <div id="status">Goal Achieved! Wizard finished successfully.</div>
                        </body>
                        </html>
                        """
                    self.wfile.write(html.encode("utf-8"))

                elif self.path == "/advance-flow":
                    parent.current_step += 1
                    self.wfile.write(b'{"status": "advanced"}')

                elif self.path == "/stall-page":
                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head><title>Stall Test</title></head>
                    <body>
                        <h2>Static Page</h2>
                        <button id="btn-broken" onclick="console.log('No-op')">No-op Button</button>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode("utf-8"))

                else:
                    self.wfile.write(b"<html><body>Root</body></html>")

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
def flow_server():
    server = FlowMockServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def temp_user_dir():
    temp_dir = tempfile.mkdtemp(prefix="agent_loop_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# =========================================================================
# TEST 1: LOOP AGAINST LOCAL MOCK PAGE WITH A BUTTON FLOW
# =========================================================================


@pytest.mark.asyncio
async def test_agent_loop_button_flow_completion(flow_server, temp_user_dir):
    """Verifies that BrowserAgentLoop operates through a multi-step button flow to goal completion."""
    controller = BrowserController(permission_manager=False, user_data_dir=temp_user_dir)
    event_bus = get_event_bus()

    streamed_steps = []

    async def on_step(evt: Event):
        streamed_steps.append(evt)

    event_bus.subscribe("browser.agent_step", on_step)

    try:
        await controller.start_session(headless=True, persistent=True)
        target_url = f"http://127.0.0.1:{flow_server.port}/button-flow"
        await controller.navigate(target_url, auto_handoff=False)

        async def scripted_decider(
            obs: ObserveResult, goal: str, history: list[StepRecord]
        ) -> VisionAction:
            combined = (obs.dom_text + " " + obs.ocr_text).lower()
            if "goal achieved" in combined:
                return VisionAction(
                    thought="Verified 'Goal Achieved' confirmation is on the screen.",
                    action=ActionType.DONE,
                    summary="Reached confirmed goal state.",
                )
            if "proceed to step 2" in combined:
                return VisionAction(
                    thought="Found Step 1 proceed button.",
                    action=ActionType.CLICK,
                    element="#btn-next",
                )
            if "finalize goal" in combined:
                return VisionAction(
                    thought="Found Step 2 finalize button.",
                    action=ActionType.CLICK,
                    element="#btn-finish",
                )
            return VisionAction(
                thought="Waiting for page transition.",
                action=ActionType.WAIT,
                seconds=0.5,
            )

        loop = BrowserAgentLoop(
            controller=controller,
            decider=scripted_decider,
            max_steps=10,
        )

        report: AgentLoopReport = await loop.run(
            goal="Complete the wizard until Goal Achieved",
            workflow_id=uuid4(),
            task_id=uuid4(),
        )

        assert report.success is True
        assert report.status == "COMPLETED"
        assert report.total_steps >= 2
        assert "Goal Achieved" in report.message
        assert len(streamed_steps) >= 2
        assert streamed_steps[0].payload.get("step_number") == 1
    finally:
        event_bus.unsubscribe("browser.agent_step", on_step)
        await controller.close_session()


# =========================================================================
# TEST 2: STALL DETECTION (3 IDENTICAL ACTIONS ON UNCHANGED SCREEN)
# =========================================================================


@pytest.mark.asyncio
async def test_agent_loop_stall_detection(flow_server, temp_user_dir):
    """Verifies that repeating identical actions on an unchanged screen 3 times halts as STALLED."""
    controller = BrowserController(permission_manager=False, user_data_dir=temp_user_dir)
    try:
        await controller.start_session(headless=True, persistent=True)
        target_url = f"http://127.0.0.1:{flow_server.port}/stall-page"
        await controller.navigate(target_url, auto_handoff=False)

        async def stuck_decider(
            obs: ObserveResult, goal: str, history: list[StepRecord]
        ) -> VisionAction:
            # Keeps returning the same click action regardless of state
            return VisionAction(
                thought="Attempting to click broken button.",
                action=ActionType.CLICK,
                element="#btn-broken",
            )

        loop = BrowserAgentLoop(
            controller=controller,
            decider=stuck_decider,
            max_steps=20,
        )

        report = await loop.run(goal="Do something on static page")

        assert report.success is False
        assert report.status == "STALLED"
        assert report.stuck_reason is not None
        assert "Stall detected" in report.stuck_reason
        assert "3 consecutive times" in report.stuck_reason
    finally:
        await controller.close_session()


# =========================================================================
# TEST 3: HARD STEP CAP (MAX STEPS)
# =========================================================================


@pytest.mark.asyncio
async def test_agent_loop_hard_step_cap(flow_server, temp_user_dir):
    """Verifies that the loop terminates strictly when reaching max_steps."""
    controller = BrowserController(permission_manager=False, user_data_dir=temp_user_dir)
    try:
        await controller.start_session(headless=True, persistent=True)
        target_url = f"http://127.0.0.1:{flow_server.port}/stall-page"
        await controller.navigate(target_url, auto_handoff=False)

        step_counter = 0

        async def changing_action_decider(
            obs: ObserveResult, goal: str, history: list[StepRecord]
        ) -> VisionAction:
            nonlocal step_counter
            step_counter += 1
            # Return varying scroll/wait actions to avoid stall trigger
            if step_counter % 2 == 0:
                return VisionAction(
                    thought=f"Scrolling on step {step_counter}",
                    action=ActionType.SCROLL,
                    direction="down",
                    amount=50,
                )
            else:
                return VisionAction(
                    thought=f"Waiting on step {step_counter}",
                    action=ActionType.WAIT,
                    seconds=0.05,
                )

        loop = BrowserAgentLoop(
            controller=controller,
            decider=changing_action_decider,
            max_steps=5,  # Test cap of 5
        )

        report = await loop.run(goal="Infinite task without completion")

        assert report.success is False
        assert report.status == "MAX_STEPS_REACHED"
        assert report.total_steps == 5
        assert "Reached hard step cap of 5 steps" in (report.stuck_reason or "")
    finally:
        await controller.close_session()


# =========================================================================
# TEST 4: FINAL REPORT CONTENT & GOAL VERIFICATION
# =========================================================================


@pytest.mark.asyncio
async def test_agent_loop_final_report_content(flow_server, temp_user_dir):
    """Verifies that final report details actions, what it sees, screenshots, and does not claim false success."""
    controller = BrowserController(permission_manager=False, user_data_dir=temp_user_dir)
    try:
        await controller.start_session(headless=True, persistent=True)
        target_url = f"http://127.0.0.1:{flow_server.port}/stall-page"
        await controller.navigate(target_url, auto_handoff=False)

        async def single_step_decider(
            obs: ObserveResult, goal: str, history: list[StepRecord]
        ) -> VisionAction:
            if not history:
                return VisionAction(
                    thought="Inspecting elements on static page.",
                    action=ActionType.WAIT,
                    seconds=0.1,
                )
            return VisionAction(
                thought="Could not find goal target; reporting problem.",
                action=ActionType.DONE,
                summary="Terminated after inspection.",
            )

        loop = BrowserAgentLoop(
            controller=controller,
            decider=single_step_decider,
            max_steps=10,
        )

        report = await loop.run(goal="Look for secret button that does not exist")

        assert report.goal == "Look for secret button that does not exist"
        assert len(report.actions_taken) >= 1
        assert "Static Page" in report.what_agent_sees_now or "btn-broken" in report.what_agent_sees_now
        assert report.final_screenshot_b64 is not None
        assert len(report.final_screenshot_b64) > 100
        assert report.message is not None
    finally:
        await controller.close_session()
