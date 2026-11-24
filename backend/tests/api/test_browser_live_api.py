from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tools.browser.controller import get_browser_controller
from app.tools.browser.dom import InteractiveElement


@pytest.fixture
def client():
    return TestClient(app)


def test_mcp_browser_catalog_endpoint(client):
    response = client.get("/api/v1/mcp/browser/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert data["count"] >= 5
    tool_names = [t["name"] for t in data["tools"]]
    assert "browser_navigate" in tool_names
    assert "browser_click" in tool_names
    assert "browser_execute_step" in tool_names


def test_mcp_browser_status_endpoint(client):
    response = client.get("/api/v1/mcp/browser/status")
    assert response.status_code == 200
    data = response.json()
    assert "connected" in data
    assert data["connected"] is True


def test_mcp_browser_execute_endpoint(client):
    ctrl = get_browser_controller()
    with patch.object(ctrl, "navigate", new_callable=AsyncMock) as mock_nav:
        mock_nav.return_value = MagicMock(
            success=True, data={"url": "https://github.com", "title": "GitHub"}
        )
        response = client.post(
            "/api/v1/mcp/browser/execute",
            json={
                "name": "browser_navigate",
                "arguments": {"url": "https://github.com"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is False
        assert "Successfully navigated" in data["content"][0]["text"]


def test_browser_live_session_endpoints(client):
    ctrl = get_browser_controller()

    # 1. GET /session (idle)
    with patch.object(ctrl, "get_live_state", new_callable=AsyncMock) as mock_st:
        mock_st.return_value = {
            "active": False,
            "session_id": None,
            "state": "idle",
            "current_url": "about:blank",
            "page_title": "",
            "tab_count": 0,
            "active_tab_index": 0,
            "tabs": [],
            "last_action": None,
            "last_action_status": None,
            "last_verification": None,
            "live_frame_base64": None,
            "interactive_elements_count": 0,
        }
        res = client.get("/api/v1/browser/session")
        assert res.status_code == 200
        assert res.json()["state"] == "idle"

    # 2. POST /session/start
    with patch.object(
        ctrl, "start_session", new_callable=AsyncMock
    ) as mock_start, patch.object(
        ctrl, "get_live_state", new_callable=AsyncMock
    ) as mock_st:
        mock_start.return_value = MagicMock(
            success=True, data={"session_id": "test-uuid-123", "state": "ready"}
        )
        mock_st.return_value = {
            "active": True,
            "session_id": "test-uuid-123",
            "state": "ready",
            "current_url": "about:blank",
            "page_title": "Blank",
            "tab_count": 1,
            "active_tab_index": 0,
            "tabs": [],
        }
        res = client.post("/api/v1/browser/session/start", json={"headless": True})
        assert res.status_code == 200
        assert res.json()["success"] is True

    # 3. POST /navigate (Canva scenario)
    with patch.object(
        ctrl, "navigate", new_callable=AsyncMock
    ) as mock_nav, patch.object(
        ctrl, "get_live_state", new_callable=AsyncMock
    ) as mock_st:
        mock_nav.return_value = MagicMock(
            success=True, data={"url": "https://www.canva.com", "title": "Canva"}
        )
        mock_st.return_value = {
            "active": True,
            "current_url": "https://www.canva.com",
            "page_title": "Canva",
            "state": "ready",
        }
        res = client.post(
            "/api/v1/browser/navigate", json={"url": "https://www.canva.com"}
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

    # 4. POST /step (Observe-Act-Verify)
    with patch.object(
        ctrl, "execute_observe_act_verify", new_callable=AsyncMock
    ) as mock_step, patch.object(
        ctrl, "get_live_state", new_callable=AsyncMock
    ) as mock_st:
        mock_step.return_value = MagicMock(
            success=True,
            data={
                "action": "click",
                "target": "button#submit",
                "details": "Verified click",
            },
            error=None,
        )
        mock_st.return_value = {"state": "ready", "last_verification": "Verified click"}
        res = client.post(
            "/api/v1/browser/step",
            json={
                "action": "click",
                "target": "button#submit",
                "expected_outcome": "Form submitted",
            },
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

    # 5. GET /elements
    with patch.object(
        ctrl, "get_interactive_elements", new_callable=AsyncMock
    ) as mock_elem:
        mock_elem.return_value = [
            InteractiveElement(
                selector="a.nav-link",
                tag_name="a",
                text="Documentation",
                role="link",
                is_visible=True,
                is_enabled=True,
            )
        ]
        res = client.get("/api/v1/browser/elements")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 1
        assert data["elements"][0]["text"] == "Documentation"
