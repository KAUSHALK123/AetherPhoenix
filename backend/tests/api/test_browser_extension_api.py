import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tools.browser_extension.connection_manager import get_connection_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_extension_status_endpoint(client):
    response = client.get("/api/v1/browser-extension/status")
    assert response.status_code == 200
    data = response.json()
    assert "connected" in data
    assert data["connected"] is False


def test_extension_websocket_lifecycle(client):
    manager = get_connection_manager()
    assert not manager.is_connected

    with client.websocket_connect("/api/v1/browser-extension/ws") as websocket:
        assert manager.is_connected
        status_res = client.get("/api/v1/browser-extension/status")
        assert status_res.status_code == 200
        assert status_res.json()["connected"] is True

        # Send heartbeat message
        websocket.send_json(
            {
                "type": "heartbeat",
                "active_tab_url": "https://aetherphoenix.ai",
                "active_tab_title": "AetherPhoenix AI",
            }
        )

    # After websocket closes context, connection should disconnect
    assert not manager.is_connected
