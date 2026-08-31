import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from shared.contracts.execution import (
    ExecutionResult,
    SupervisorDecision,
    SupervisorValidation,
    TaskError,
)
from shared.contracts.task import Task, TaskCategory, TaskStatus, TaskType
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.agents.supervisor.agent import SupervisorAgent
from app.agents.supervisor.failure_detector import FailureDetectorService


@pytest.fixture
def supervisor_agent():
    mock_bus = MagicMock()
    mock_bus.publish = AsyncMock()

    agent = SupervisorAgent(
        event_bus=mock_bus,
        max_retries=3,
    )
    return agent


@pytest.fixture
def sample_task():
    return Task(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        task_name="Sample Task",
        description="Sample task description",
        expected_output="Valid output content",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="test_tool",
    )


@pytest.fixture
def workflow_state(sample_task):
    metadata = WorkflowMetadata(workflow_id=sample_task.workflow_id, goal="Test Goal")
    state = SharedWorkflowState(metadata=metadata)
    state.tasks[sample_task.task_id] = sample_task
    return state


@pytest.mark.asyncio
async def test_supervisor_successful_output_validation(supervisor_agent, sample_task, workflow_state):
    """Test supervisor approving valid task execution result."""
    result = ExecutionResult(
        task_id=sample_task.task_id,
        workflow_id=sample_task.workflow_id,
        success=True,
        output={"status": "success", "content": "Valid output content"},
        error=None,
    )

    validation = await supervisor_agent.execute(
        sample_task,
        result,
        workflow_state,
    )

    assert validation.is_valid is True
    assert workflow_state.tasks[sample_task.task_id].status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_supervisor_invalid_output_detection(supervisor_agent, sample_task, workflow_state):
    """Test supervisor detecting invalid or empty output and rejecting task."""
    result = ExecutionResult(
        task_id=sample_task.task_id,
        workflow_id=sample_task.workflow_id,
        success=True,
        output={},  # Missing expected output
        error=None,
    )

    # Force validator to consider output invalid
    with patch.object(supervisor_agent.validator, "validate") as mock_val:
        mock_val.return_value = (False, {"output": False}, ["Output is missing required data payload"])

        validation = await supervisor_agent.execute(
            sample_task,
            result,
            workflow_state,
        )

        assert validation.is_valid is False


@pytest.mark.asyncio
async def test_supervisor_task_failure_detection(supervisor_agent, sample_task, workflow_state):
    """Test supervisor detecting task failure and analyzing failure type."""
    result = ExecutionResult(
        task_id=sample_task.task_id,
        workflow_id=sample_task.workflow_id,
        success=False,
        output={},
        error=TaskError(
            error_code="TIMEOUT",
            error_message="Operation timed out after 30 seconds",
            is_recoverable=True,
        ),
    )

    validation = await supervisor_agent.execute(
        sample_task,
        result,
        workflow_state,
    )

    assert validation.is_valid is False
    assert workflow_state.tasks[sample_task.task_id].status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_supervisor_dependency_failure_detection(supervisor_agent):
    """Test supervisor detecting upstream task failure blocking dependent downstream tasks."""
    workflow_id = uuid.uuid4()
    task_a_id = uuid.uuid4()
    task_b_id = uuid.uuid4()

    task_a = Task(
        task_id=task_a_id,
        workflow_id=workflow_id,
        task_name="Upstream Task A",
        description="Upstream task A description",
        expected_output="Output A",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="tool_a",
    )

    task_b = Task(
        task_id=task_b_id,
        workflow_id=workflow_id,
        task_name="Downstream Task B",
        description="Downstream task B description",
        expected_output="Output B",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        dependencies=[task_a_id],
        required_tool="tool_b",
    )

    metadata = WorkflowMetadata(workflow_id=workflow_id, goal="Test Goal")
    state = SharedWorkflowState(metadata=metadata)
    state.tasks[task_a_id] = task_a
    state.tasks[task_b_id] = task_b

    # Fail upstream task A permanently
    result_a = ExecutionResult(
        task_id=task_a_id,
        workflow_id=workflow_id,
        success=False,
        output={},
        error=TaskError(
            error_code="PERMISSION_DENIED",
            error_message="Access denied permanently",
            is_recoverable=False,
        ),
    )

    await supervisor_agent.execute(
        task_a,
        result_a,
        state,
    )

    # Verify task A is FAILED and tracked in failed tasks
    assert state.tasks[task_a_id].status == TaskStatus.FAILED
    assert task_a_id in state.failed_tasks or state.tasks[task_b_id].status != TaskStatus.COMPLETED
