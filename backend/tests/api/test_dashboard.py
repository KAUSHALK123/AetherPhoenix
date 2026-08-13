from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from shared.contracts.workflow import (
    ProgressState,
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.core.events.bus import get_event_bus
from app.core.events.models import Event
from app.main import app
from app.runtime.kernel import get_kernel
from app.services.observability import get_observability_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def obs_service():
    return get_observability_service()


@pytest.mark.anyio
async def test_get_dashboard_ui(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert "AetherPhoenix" in response.text
    assert "html" in response.text


@pytest.mark.anyio
async def test_get_dashboard_stats(client, obs_service):
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_workflows" in data
    assert "running_workflows" in data
    assert "completed_workflows" in data
    assert "failed_workflows" in data
    assert "total_retries" in data


@pytest.mark.anyio
async def test_get_dashboard_workflows(client, obs_service):
    # Setup dummy active workflow in RuntimeKernel
    workflow_id = str(uuid4())
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=UUID(workflow_id) if hasattr(UUID, "int") else workflow_id,
            goal="API Test Goal",
            status=WorkflowStatus.RUNNING,
        ),
        progress=ProgressState(
            overall_percentage=45.0,
            execution_duration_seconds=1.5,
        ),
    )

    kernel = get_kernel()
    ctx = kernel.create_context(session_id="api_test_session", shared_state=state)

    try:
        response = client.get("/api/v1/dashboard/workflows")
        assert response.status_code == 200
        workflows = response.json()
        assert len(workflows) >= 1
        goals = [w["goal"] for w in workflows]
        assert "API Test Goal" in goals

        # Test single workflow route
        detail_response = client.get(f"/api/v1/dashboard/workflows/{workflow_id}")
        assert detail_response.status_code == 200
        wf_data = detail_response.json()
        assert wf_data["goal"] == "API Test Goal"
        assert wf_data["progress_percentage"] == 45.0
    finally:
        kernel.remove_context(ctx.context_id)


@pytest.mark.anyio
async def test_get_dashboard_events(client, obs_service):
    event_bus = get_event_bus()
    event = Event(
        workflow_id=str(uuid4()),
        event_type="APIEvent",
        source_component="test_api",
        payload={"key": "val"},
    )
    await event_bus.publish(event)

    response = client.get("/api/v1/dashboard/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    event_types = [e["event_type"] for e in events]
    assert "APIEvent" in event_types
