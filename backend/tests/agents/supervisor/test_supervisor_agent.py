import uuid
from unittest.mock import AsyncMock

import pytest
from shared.contracts.event import EventType
from shared.contracts.execution import ExecutionResult, SupervisorDecision, TaskError
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
)

from app.agents.supervisor.agent import SupervisorAgent
from app.core.events.bus import EventBus


@pytest.fixture
def mock_event_bus():
    bus = AsyncMock(spec=EventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def supervisor(mock_event_bus):
    return SupervisorAgent(event_bus=mock_event_bus)


@pytest.fixture
def base_task():
    return Task(
        workflow_id=uuid.uuid4(),
        task_name="Test Task",
        description="A test task",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        expected_output="Success result",
        success_criteria=["Must return output"],
    )


@pytest.fixture
def base_state(base_task):
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=base_task.workflow_id, goal="Test Workflow"
        )
    )
    state.tasks[base_task.task_id] = base_task
    state.running_tasks.append(base_task.task_id)
    return state


@pytest.mark.asyncio
async def test_supervisor_passed_execution(
    supervisor, mock_event_bus, base_task, base_state
):
    result = ExecutionResult(
        task_id=base_task.task_id,
        workflow_id=base_task.workflow_id,
        success=True,
        output={"key": "value"},
    )

    validation = await supervisor.execute(base_task, result, base_state)

    assert validation.is_valid is True
    assert validation.decision == SupervisorDecision.PASSED
    assert validation.checks.get("execution_success") is True
    assert validation.checks.get("output_valid") is True

    # Check SWS updates
    assert base_task.task_id not in base_state.running_tasks
    assert base_task.task_id in base_state.completed_tasks
    assert base_task.status == TaskStatus.COMPLETED
    assert base_task.task_id in base_state.validations

    # Check SWS progress updates
    assert base_state.progress.total_tasks == 1
    assert base_state.progress.completed_tasks == 1
    assert base_state.progress.overall_percentage == 100.0

    # Check Supervisor retrieval helper
    retrieved_progress = supervisor.get_workflow_progress(base_state)
    assert retrieved_progress.overall_percentage == 100.0

    # Check Events
    assert mock_event_bus.publish.call_count == 2
    started_event = mock_event_bus.publish.call_args_list[0][0][0]
    completed_event = mock_event_bus.publish.call_args_list[1][0][0]

    assert started_event.event_type == EventType.SUPERVISION_STARTED
    assert completed_event.event_type == EventType.SUPERVISION_COMPLETED
    assert completed_event.payload["decision"] == SupervisorDecision.PASSED.value


@pytest.mark.asyncio
async def test_supervisor_failed_execution(
    supervisor, mock_event_bus, base_task, base_state
):
    result = ExecutionResult(
        task_id=base_task.task_id,
        workflow_id=base_task.workflow_id,
        success=False,
        error=TaskError(error_code="TEST_ERR", error_message="Failed intentionally"),
    )

    validation = await supervisor.execute(base_task, result, base_state)

    assert validation.is_valid is False
    assert validation.decision == SupervisorDecision.FAILED
    assert validation.checks.get("execution_success") is False

    # Check SWS updates
    assert base_task.task_id not in base_state.running_tasks
    assert base_task.task_id in base_state.failed_tasks
    assert base_task.status == TaskStatus.FAILED
    assert base_task.task_id in base_state.validations

    # Check Events
    completed_event = mock_event_bus.publish.call_args_list[1][0][0]
    assert completed_event.payload["decision"] == SupervisorDecision.FAILED.value


@pytest.mark.asyncio
async def test_supervisor_success_criteria_mismatch(
    supervisor, mock_event_bus, base_task, base_state
):
    # Success is true but no output/artifacts
    result = ExecutionResult(
        task_id=base_task.task_id,
        workflow_id=base_task.workflow_id,
        success=True,
        output={},
        artifacts=[],
    )

    validation = await supervisor.execute(base_task, result, base_state)

    assert validation.is_valid is False
    assert validation.decision == SupervisorDecision.FAILED
    assert validation.checks.get("execution_success") is True
    assert validation.checks.get("output_valid") is False
    assert len(validation.issues) == 2

    assert base_task.status == TaskStatus.FAILED
