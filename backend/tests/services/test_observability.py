from uuid import UUID, uuid4

import pytest
from shared.contracts.task import Task, TaskCategory
from shared.contracts.workflow import (
    ProgressState,
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.core.events.bus import EventBus
from app.core.events.models import Event
from app.runtime.kernel import get_kernel
from app.services.observability import EventObservabilityService


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def obs_service(event_bus):
    return EventObservabilityService(event_bus=event_bus, max_events=10)


@pytest.mark.anyio
async def test_event_capture(obs_service, event_bus):
    event = Event(
        workflow_id=str(uuid4()),
        event_type="TestEvent",
        source_component="test_source",
        payload={"message": "hello"},
    )

    await event_bus.publish(event)
    assert len(obs_service.recent_events) == 1
    assert obs_service.recent_events[0].event_type == "TestEvent"

    recent = obs_service.get_recent_events()
    assert len(recent) == 1
    assert recent[0]["payload"]["message"] == "hello"


@pytest.mark.anyio
async def test_historical_workflow_capture(obs_service, event_bus):
    workflow_id = str(uuid4())
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=UUID(workflow_id) if hasattr(UUID, "int") else workflow_id,
            goal="Test Goal",
            status=WorkflowStatus.COMPLETED,
        ),
        progress=ProgressState(
            overall_percentage=100.0,
            execution_duration_seconds=12.5,
        ),
    )

    # Register in RuntimeKernel
    kernel = get_kernel()
    ctx = kernel.create_context(session_id="test_session", shared_state=state)

    try:
        # Publish workflow completed event
        event = Event(
            workflow_id=workflow_id,
            event_type="WorkflowCompleted",
            source_component="EXECUTION_ENGINE",
            payload={},
        )
        await event_bus.publish(event)

        # Check if saved in historical
        assert workflow_id in obs_service.historical_workflows
        hist = obs_service.historical_workflows[workflow_id]
        assert hist["goal"] == "Test Goal"
        assert hist["progress_percentage"] == 100.0
        assert hist["execution_duration"] == 12.5
    finally:
        kernel.remove_context(ctx.context_id)


@pytest.mark.anyio
async def test_get_stats_and_workflows(obs_service, event_bus):
    # Setup some dummy workflows
    workflow_id_1 = str(uuid4())
    state_1 = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=UUID(workflow_id_1) if hasattr(UUID, "int") else workflow_id_1,
            goal="Goal 1",
            status=WorkflowStatus.RUNNING,
        ),
        progress=ProgressState(
            overall_percentage=50.0,
            execution_duration_seconds=5.0,
        ),
    )
    task = Task(
        workflow_id=workflow_id_1,
        task_name="Task 1",
        description="Desc",
        required_tool="tool",
        category=TaskCategory.OTHER,
        expected_output="output",
    )
    task.retry_count = 2
    state_1.tasks[task.task_id] = task

    kernel = get_kernel()
    ctx_1 = kernel.create_context(session_id="test_session_1", shared_state=state_1)

    try:
        # Also add one historical completed workflow
        workflow_id_2 = str(uuid4())
        obs_service.historical_workflows[workflow_id_2] = {
            "workflow_id": workflow_id_2,
            "goal": "Goal 2",
            "status": "COMPLETED",
            "progress_percentage": 100.0,
            "tasks": {},
            "validations": {},
            "running_tasks": [],
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "pending_tasks": [],
            "execution_duration": 10.0,
        }

        workflows = obs_service.get_workflows()
        # Should contain both active and historical
        assert len(workflows) == 2

        stats = obs_service.get_stats()
        assert stats["total_workflows"] == 2
        assert stats["running_workflows"] == 1
        assert stats["completed_workflows"] == 1
        assert stats["total_retries"] == 2
        assert stats["average_duration"] == 7.5
    finally:
        kernel.remove_context(ctx_1.context_id)
