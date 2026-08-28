import pytest
from fastapi.testclient import TestClient

from app.core.events.bus import get_event_bus
from app.core.events.models import Event, EventType
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_notifications_rest_api():
    event_bus = get_event_bus()

    # Publish an event
    event = Event(
        workflow_id="wf-api-test",
        event_type=EventType.TASK_COMPLETED,
        source_component="WorkerAgent",
        payload={"task_name": "Data Extraction"},
    )
    await event_bus.publish(event)

    # Test GET /api/v1/notifications
    response = client.get("/api/v1/notifications?workflow_id=wf-api-test")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["workflow_id"] == "wf-api-test"
    assert data[0]["title"] == "Task Completed"

    notification_id = data[0]["id"]

    # Test POST /api/v1/notifications/{id}/read
    read_resp = client.post(f"/api/v1/notifications/{notification_id}/read")
    assert read_resp.status_code == 200
    assert read_resp.json()["success"] is True

    # Test POST /api/v1/notifications/read-all
    read_all_resp = client.post("/api/v1/notifications/read-all")
    assert read_all_resp.status_code == 200
    assert read_all_resp.json()["success"] is True


def test_notifications_websocket_api():
    with client.websocket_connect("/api/v1/notifications/ws") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"
