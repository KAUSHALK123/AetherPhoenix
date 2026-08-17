from uuid import uuid4

import pytest
from shared.contracts.event import EventType
from shared.contracts.execution import (
    FailureType,
    TaskError,
    TaskFailureReport,
)
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.self_healing_loop import HealingState, SelfHealingLoop
from app.core.events.bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def healing_loop(event_bus):
    return SelfHealingLoop(event_bus=event_bus, max_retries=3, max_healing_attempts=5)


@pytest.fixture
def workflow_state():
    metadata = WorkflowMetadata(goal="Self-Healing Loop Goal")
    metadata.status = WorkflowStatus.RUNNING
    return SharedWorkflowState(metadata=metadata)


def create_failed_task(workflow_id) -> Task:
    return Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Autonomous Task",
        description="Failing task for healing loop test",
        required_tool="browser_tool",
        category=TaskCategory.OTHER,
        expected_output="output_data",
        status=TaskStatus.FAILED,
        retry_count=0,
    )


@pytest.mark.anyio
async def test_healing_loop_lifecycle_registration(event_bus):
    loop = SelfHealingLoop(event_bus=event_bus)
    assert loop.registration.name == "HealingAgent"
    assert loop.current_state == HealingState.IDLE
    await loop.initialize()
    assert loop.current_state == HealingState.IDLE
    await loop.shutdown()


@pytest.mark.anyio
async def test_successful_recovery_flow(healing_loop, workflow_state, event_bus):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task
    workflow_state.failed_tasks.append(task.task_id)

    published_events = []

    async def capture(evt):
        published_events.append(evt)

    event_bus.subscribe_all(capture)

    err = TaskError(
        error_code="NETWORK_TIMEOUT",
        error_message="Connection timed out while fetching webpage",
        is_recoverable=True,
    )

    result = await healing_loop.process_failure(task, err, workflow_state)

    assert result.success is True
    assert result.attempt_number == 1
    assert result.root_cause == "NETWORK"
    assert task.retry_count == 1
    assert task.status == TaskStatus.WAITING
    assert task.task_id in workflow_state.execution_queue
    assert len(workflow_state.healing_history) == 1
    assert healing_loop.current_state == HealingState.COMPLETED

    event_types = [e.event_type for e in published_events]
    assert EventType.HEALING_STARTED in event_types
    assert EventType.HEALING_COMPLETED in event_types


@pytest.mark.anyio
async def test_non_recoverable_permission_failure(
    healing_loop, workflow_state, event_bus
):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task
    workflow_state.failed_tasks.append(task.task_id)

    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=workflow_state.metadata.workflow_id,
        failure_type=FailureType.PERMISSION_DENIED,
        message="Access denied: missing root filesystem permission",
        retryability=False,
    )

    result = await healing_loop.process_failure(task, report, workflow_state)

    assert result.success is False
    assert result.root_cause == "PERMISSION"
    assert task.retry_count == 0
    assert task.task_id not in workflow_state.execution_queue
    assert len(workflow_state.healing_history) == 1
    assert healing_loop.current_state == HealingState.FAILED


@pytest.mark.anyio
async def test_maximum_healing_attempts_enforced(event_bus, workflow_state):
    loop = SelfHealingLoop(event_bus=event_bus, max_retries=5, max_healing_attempts=2)
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    err = TaskError(
        error_code="NETWORK_TIMEOUT",
        error_message="Network connection timed out",
        is_recoverable=True,
    )

    # Attempt 1 -> Success
    res1 = await loop.process_failure(task, err, workflow_state)
    assert res1.success is True

    # Attempt 2 -> Success
    res2 = await loop.process_failure(task, err, workflow_state)
    assert res2.success is True

    # Attempt 3 -> Reaches limit of 2 max healing attempts -> Fails
    res3 = await loop.process_failure(task, err, workflow_state)
    assert res3.success is False
    assert loop.current_state in (HealingState.EXHAUSTED, HealingState.FAILED)


@pytest.mark.anyio
async def test_infinite_healing_loop_protection(healing_loop, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    err = TaskError(
        error_code="RUNTIME_CRASH",
        error_message="Repeated identical internal crash",
        is_recoverable=True,
    )

    # Simulate 3 prior identical attempts in retry engine
    sig = (
        str(task.task_id),
        "RUNTIME",
        "General runtime execution failure during task processing.",
    )
    healing_loop.retry_engine._failure_signature_counts[sig] = 3

    result = await healing_loop.process_failure(task, err, workflow_state)

    assert result.success is False
    assert healing_loop.current_state == HealingState.FAILED


@pytest.mark.anyio
async def test_alternative_tool_recovery(healing_loop, workflow_state):
    task = create_failed_task(workflow_state.metadata.workflow_id)
    task.required_tool = "browser_tool"
    workflow_state.tasks[task.task_id] = task
    workflow_state.failed_tasks.append(task.task_id)

    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=workflow_state.metadata.workflow_id,
        failure_type=FailureType.TOOL_UNAVAILABLE,
        message="browser_tool is disabled or not installed",
        retryability=False,
    )

    result = await healing_loop.process_failure(task, report, workflow_state)

    assert result.success is True
    assert len(result.replacement_tasks) == 1
    rep = result.replacement_tasks[0]
    assert rep.required_tool == "web_research_tool"
    assert rep.task_id in workflow_state.execution_queue
