from uuid import uuid4

import pytest
from shared.contracts.execution import TaskError
from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)
from shared.contracts.task import RollbackInfo, Task, TaskCategory, TaskStatus
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.supervisor.agent import SupervisorAgent
from app.core.events.bus import EventBus
from app.core.events.models import EventType


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def supervisor(event_bus):
    return SupervisorAgent(event_bus=event_bus, max_retries=3)


@pytest.fixture
def workflow_state():
    metadata = WorkflowMetadata(goal="Test Retry Goal")
    metadata.status = WorkflowStatus.RUNNING
    return SharedWorkflowState(metadata=metadata)


def create_failed_task(workflow_id) -> Task:
    return Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Test Task",
        description="A task that fails",
        required_tool="dummy_tool",
        category=TaskCategory.OTHER,
        expected_output="dummy expected output",
        status=TaskStatus.FAILED,
        retry_count=0,
    )


def test_supervisor_registration(supervisor):
    reg = supervisor.registration
    assert reg.name == "SupervisorAgent"
    assert reg.version == "1.0.0"
    assert "retr" in reg.description.lower()


@pytest.mark.anyio
async def test_supervisor_lifecycle(event_bus):
    # Test initialize / shutdown subscriptions
    agent = SupervisorAgent(event_bus=event_bus)
    assert len(event_bus._subscribers[EventType.TASK_FAILED]) == 0
    await agent.initialize()
    assert len(event_bus._subscribers[EventType.TASK_FAILED]) == 1
    await agent.shutdown()
    assert len(event_bus._subscribers[EventType.TASK_FAILED]) == 0


def test_is_eligible_for_retry_success(supervisor, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    # Under standard failure with no constraints, it is eligible
    assert supervisor.is_eligible_for_retry(task, workflow_state) is True


def test_is_eligible_for_retry_max_retries(supervisor, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    # 3 retries max, task has 2. Still eligible
    task.retry_count = 2
    assert supervisor.is_eligible_for_retry(task, workflow_state) is True

    # Reached limit. Not eligible
    task.retry_count = 3
    assert supervisor.is_eligible_for_retry(task, workflow_state) is False

    # Over limit. Not eligible
    task.retry_count = 4
    assert supervisor.is_eligible_for_retry(task, workflow_state) is False


def test_is_eligible_for_retry_invalid_task_status(supervisor, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    for status in [
        TaskStatus.CREATED,
        TaskStatus.READY,
        TaskStatus.RUNNING,
        TaskStatus.COMPLETED,
    ]:
        task.status = status
        assert supervisor.is_eligible_for_retry(task, workflow_state) is False


def test_is_eligible_for_retry_invalid_workflow_status(supervisor, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    for status in [
        WorkflowStatus.CREATED,
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
    ]:
        workflow_state.metadata.status = status
        assert supervisor.is_eligible_for_retry(task, workflow_state) is False


def test_is_eligible_for_retry_dependencies(supervisor, workflow_state):
    parent = Task(
        task_id=uuid4(),
        workflow_id=workflow_state.metadata.workflow_id,
        task_name="Parent Task",
        description="Must run first",
        required_tool="dummy_tool",
        category=TaskCategory.OTHER,
        expected_output="dummy parent output",
        status=TaskStatus.FAILED,
    )
    task = create_failed_task(workflow_state.metadata.workflow_id)
    task.dependencies.append(parent.task_id)

    workflow_state.tasks[task.task_id] = task
    workflow_state.tasks[parent.task_id] = parent

    # Dependency failed -> not eligible
    assert supervisor.is_eligible_for_retry(task, workflow_state) is False

    # Dependency running -> not eligible
    parent.status = TaskStatus.RUNNING
    assert supervisor.is_eligible_for_retry(task, workflow_state) is False

    # Dependency completed -> eligible
    parent.status = TaskStatus.COMPLETED
    assert supervisor.is_eligible_for_retry(task, workflow_state) is True


def test_is_eligible_for_retry_pending_or_rejected_permissions(
    supervisor, workflow_state
):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    # Eligible initially
    assert supervisor.is_eligible_for_retry(task, workflow_state) is True

    # PENDING permission -> not eligible
    perm = PermissionRequest(
        workflow_id=workflow_state.metadata.workflow_id,
        task_id=task.task_id,
        permission_type=PermissionType.FILE_SYSTEM,
        reason="Test permission",
        risk_level=RiskLevel.LOW,
        status=PermissionStatus.PENDING,
    )
    workflow_state.permissions.append(perm)
    assert supervisor.is_eligible_for_retry(task, workflow_state) is False

    # REJECTED permission -> not eligible
    perm.status = PermissionStatus.REJECTED
    assert supervisor.is_eligible_for_retry(task, workflow_state) is False

    # GRANTED permission -> eligible
    perm.status = PermissionStatus.GRANTED
    assert supervisor.is_eligible_for_retry(task, workflow_state) is True


def test_is_eligible_for_retry_missing_required_permissions(supervisor, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    task.permissions.append("FILE_SYSTEM")
    workflow_state.tasks[task.task_id] = task

    # No permission request granted -> not eligible
    assert supervisor.is_eligible_for_retry(task, workflow_state) is False

    # Grant permission request -> eligible
    perm = PermissionRequest(
        workflow_id=workflow_state.metadata.workflow_id,
        permission_type=PermissionType.FILE_SYSTEM,
        reason="Test permission",
        risk_level=RiskLevel.LOW,
        status=PermissionStatus.GRANTED,
    )
    workflow_state.permissions.append(perm)
    assert supervisor.is_eligible_for_retry(task, workflow_state) is True


def test_is_eligible_for_retry_error_recoverable(supervisor, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    # Recoverable -> eligible
    err = TaskError(
        error_code="TIMEOUT", error_message="Task timed out", is_recoverable=True
    )
    assert supervisor.is_eligible_for_retry(task, workflow_state, error=err) is True

    # Non-recoverable flag -> not eligible
    err.is_recoverable = False
    assert supervisor.is_eligible_for_retry(task, workflow_state, error=err) is False


def test_is_eligible_for_retry_non_retryable_codes(supervisor, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    # Permission denied code -> not eligible
    err = TaskError(
        error_code="PERMISSION_DENIED",
        error_message="Access denied",
        is_recoverable=True,
    )
    assert supervisor.is_eligible_for_retry(task, workflow_state, error=err) is False

    # Tool not found code -> not eligible
    err2 = TaskError(
        error_code="TOOL_NOT_FOUND", error_message="Missing tool", is_recoverable=True
    )
    assert supervisor.is_eligible_for_retry(task, workflow_state, error=err2) is False


def test_is_eligible_for_retry_destructive_operation(supervisor, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    task.risk_level = "HIGH"
    workflow_state.tasks[task.task_id] = task

    # Destructive task with non-transient error -> not eligible
    err = TaskError(
        error_code="EXECUTION_FAILED",
        error_message="Write file failed",
        is_recoverable=True,
    )
    assert supervisor.is_eligible_for_retry(task, workflow_state, error=err) is False

    # Destructive task with transient TIMEOUT error -> eligible
    err_transient = TaskError(
        error_code="TIMEOUT", error_message="Operation timed out", is_recoverable=True
    )
    assert (
        supervisor.is_eligible_for_retry(task, workflow_state, error=err_transient)
        is True
    )

    # Task with rollback info (also destructive) -> same logic
    task.risk_level = "LOW"
    task.rollback_info = RollbackInfo(rollback_point="git_reset")
    assert supervisor.is_eligible_for_retry(task, workflow_state, error=err) is False
    assert (
        supervisor.is_eligible_for_retry(task, workflow_state, error=err_transient)
        is True
    )


@pytest.mark.anyio
async def test_supervisor_execute_triggers_retry(supervisor, workflow_state, event_bus):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task
    workflow_state.failed_tasks.append(task.task_id)

    # Mock event bus publication
    published_events = []

    async def capture_event(evt):
        published_events.append(evt)

    event_bus.subscribe_all(capture_event)

    err = TaskError(
        error_code="TIMEOUT", error_message="Timed out", is_recoverable=True
    )

    # Run execute
    result = await supervisor.execute(task, workflow_state, error=err)

    assert result is True
    # Verify retry count incremented
    assert task.retry_count == 1
    # Verify removed from failed tasks
    assert task.task_id not in workflow_state.failed_tasks
    # Verify enqueued in execution queue
    assert task.task_id in workflow_state.execution_queue
    # Verify status is transitioned to WAITING
    assert task.status == TaskStatus.WAITING
    # Verify event published
    assert len(published_events) >= 1
    assert published_events[0].event_type in (
        "TaskRetried",
        "TASK_RETRIED",
        EventType.TASK_RETRIED,
    )
    assert published_events[0].payload["retry_count"] == 1


@pytest.mark.anyio
async def test_supervisor_execute_not_eligible(supervisor, workflow_state, event_bus):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    task.retry_count = 3  # Max is 3
    workflow_state.tasks[task.task_id] = task
    workflow_state.failed_tasks.append(task.task_id)

    # Run execute
    result = await supervisor.execute(task, workflow_state)

    assert result is False
    # No changes
    assert task.retry_count == 3
    assert task.status == TaskStatus.FAILED
    assert task.task_id in workflow_state.failed_tasks
    assert task.task_id not in workflow_state.execution_queue
