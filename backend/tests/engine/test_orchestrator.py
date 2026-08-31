from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from shared.contracts.event import EventType
from shared.contracts.execution import (
    ExecutionResult,
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

from app.agents.healing.agent import HealingAgent
from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus
from app.engine.orchestrator import PipelineOrchestrator


@pytest.fixture
def mock_components():
    worker = MagicMock(spec=WorkerAgent)
    worker.execute = AsyncMock()

    supervisor = MagicMock(spec=SupervisorAgent)
    supervisor.execute = AsyncMock()
    supervisor.monitor = MagicMock()
    supervisor.monitor.parallel_monitor = MagicMock()

    # default to allow task execution
    supervisor.monitor.parallel_monitor.check_prerequisites.return_value = "READY"

    # Mock progress update calculations on the state
    def mock_update_progress_state(state):
        completed = sum(
            1 for t in state.tasks.values() if t.status == TaskStatus.COMPLETED
        )
        failed = sum(1 for t in state.tasks.values() if t.status == TaskStatus.FAILED)
        blocked = sum(1 for t in state.tasks.values() if t.status == TaskStatus.BLOCKED)

        state.progress.completed_tasks = completed
        state.progress.failed_tasks = failed
        state.progress.blocked_tasks = blocked
        state.progress.total_tasks = len(state.tasks)

    supervisor.monitor.update_progress_state = MagicMock(
        side_effect=mock_update_progress_state
    )

    # Mock default supervision validation result (success)
    validation_ok = MagicMock()
    validation_ok.is_valid = True
    supervisor.execute.return_value = validation_ok

    event_bus = MagicMock(spec=EventBus)
    event_bus.publish = AsyncMock()

    healing = MagicMock(spec=HealingAgent)
    healing.execute = AsyncMock()

    return {
        "worker": worker,
        "supervisor": supervisor,
        "event_bus": event_bus,
        "healing": healing,
    }


@pytest.fixture
def simple_workflow():
    workflow_id = uuid4()
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Test Orchestrator Goal",
            status=WorkflowStatus.CREATED,
        )
    )

    # Add a single task
    task = Task(
        workflow_id=workflow_id,
        task_name="Task 1",
        description="First test task",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        expected_output="Done 1",
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    return state


@pytest.mark.asyncio
async def test_orchestrator_successful_execution(mock_components, simple_workflow):
    """Verify orchestrator runs workflow and finishes successfully."""
    orchestrator = PipelineOrchestrator(
        worker_agent=mock_components["worker"],
        supervisor_agent=mock_components["supervisor"],
        event_bus=mock_components["event_bus"],
        healing_agent=mock_components["healing"],
    )

    task_id = simple_workflow.execution_queue[0]
    task = simple_workflow.tasks[task_id]

    # Setup worker to return success result
    mock_components["worker"].execute.return_value = ExecutionResult(
        task_id=task_id,
        workflow_id=simple_workflow.metadata.workflow_id,
        success=True,
        output={"result": "ok"},
    )

    final_state = await orchestrator.run_workflow(simple_workflow)

    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED

    # Verify key steps called
    mock_components["worker"].execute.assert_called_once_with(task)
    mock_components["supervisor"].execute.assert_called_once()
    mock_components["supervisor"].monitor.update_progress_state.assert_called()

    # Verify event publishing
    published_types = [
        call.args[0].event_type
        for call in mock_components["event_bus"].publish.call_args_list
    ]
    assert EventType.WORKFLOW_STARTED in published_types
    assert EventType.TASK_STARTED in published_types
    assert EventType.TASK_COMPLETED in published_types
    assert EventType.WORKFLOW_COMPLETED in published_types


@pytest.mark.asyncio
async def test_orchestrator_handles_worker_exception(mock_components, simple_workflow):
    """Verify orchestrator fails workflow on unretryable worker exception."""
    orchestrator = PipelineOrchestrator(
        worker_agent=mock_components["worker"],
        supervisor_agent=mock_components["supervisor"],
        event_bus=mock_components["event_bus"],
    )

    task_id = simple_workflow.execution_queue[0]
    task = simple_workflow.tasks[task_id]

    # Worker raises exception
    mock_components["worker"].execute.side_effect = RuntimeError("Worker crash")

    # Supervisor validation fails on failure
    validation_fail = MagicMock()
    validation_fail.is_valid = False
    mock_components["supervisor"].execute.return_value = validation_fail

    # Supervisor retry choice -> False (no retry)
    mock_components["supervisor"].execute.side_effect = [validation_fail, False]

    # Mock supervisor failure detector to return a structured Failure Report
    report = TaskFailureReport(
        task_id=task_id,
        workflow_id=simple_workflow.metadata.workflow_id,
        failure_type=FailureType.UNEXPECTED_EXCEPTION,
        message="Task execution failed due to error",
        retryability=False,
        detected_at=datetime.now(timezone.utc),
    )
    mock_components["supervisor"].failure_detector = MagicMock()
    mock_components["supervisor"].failure_detector.check_failure.return_value = report

    final_state = await orchestrator.run_workflow(simple_workflow)

    assert final_state.metadata.status == WorkflowStatus.FAILED
    assert task.status == TaskStatus.FAILED

    # Verify error details captured
    published_types = [
        call.args[0].event_type
        for call in mock_components["event_bus"].publish.call_args_list
    ]
    assert EventType.TASK_FAILED in published_types
    assert EventType.WORKFLOW_FAILED in published_types


@pytest.mark.asyncio
async def test_orchestrator_deadlock_detection(mock_components, simple_workflow):
    """Verify orchestrator breaks loop and halts on deadlock."""
    orchestrator = PipelineOrchestrator(
        worker_agent=mock_components["worker"],
        supervisor_agent=mock_components["supervisor"],
        event_bus=mock_components["event_bus"],
    )

    # Set check_prerequisites to PENDING so no tasks ever start executing
    mock_components[
        "supervisor"
    ].monitor.parallel_monitor.check_prerequisites.return_value = "PENDING"

    final_state = await orchestrator.run_workflow(simple_workflow)

    # Workflow fails/remains running and terminates
    assert len(final_state.execution_queue) == 1
    mock_components["worker"].execute.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_controlled_retry(mock_components, simple_workflow):
    """Verify orchestrator processes task retry when supervisor allows it."""
    orchestrator = PipelineOrchestrator(
        worker_agent=mock_components["worker"],
        supervisor_agent=mock_components["supervisor"],
        event_bus=mock_components["event_bus"],
    )

    task_id = simple_workflow.execution_queue[0]
    task = simple_workflow.tasks[task_id]

    # First attempt fails, second succeeds
    mock_components["worker"].execute.side_effect = [
        ExecutionResult(
            task_id=task_id,
            workflow_id=task.workflow_id,
            success=False,
            error=TaskError(error_code="FAIL", error_message=""),
        ),
        ExecutionResult(
            task_id=task_id, workflow_id=task.workflow_id, success=True, output={}
        ),
    ]

    validation_fail = MagicMock()
    validation_fail.is_valid = False
    validation_ok = MagicMock()
    validation_ok.is_valid = True

    # Single callable side_effect to track calls and execute retry actions
    call_count = 0

    async def supervisor_execute_mock(t, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return validation_fail
        elif call_count == 2:
            state = args[0] if args else kwargs.get("state")
            state.execution_queue.append(t.task_id)
            t.status = TaskStatus.WAITING
            if t.task_id in state.failed_tasks:
                state.failed_tasks.remove(t.task_id)
            t.retry_count += 1
            return True
        elif call_count == 3:
            return validation_ok
        return True

    mock_components["supervisor"].execute.side_effect = supervisor_execute_mock

    final_state = await orchestrator.run_workflow(simple_workflow)

    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED

    # Check for retry event
    published_types = [
        call.args[0].event_type
        for call in mock_components["event_bus"].publish.call_args_list
    ]
    assert EventType.TASK_RETRIED in published_types


@pytest.mark.asyncio
async def test_orchestrator_blocked_prerequisites(mock_components, simple_workflow):
    """Verify orchestrator marks tasks BLOCKED if prerequisites fail."""
    orchestrator = PipelineOrchestrator(
        worker_agent=mock_components["worker"],
        supervisor_agent=mock_components["supervisor"],
        event_bus=mock_components["event_bus"],
    )

    task_id = simple_workflow.execution_queue[0]
    task = simple_workflow.tasks[task_id]

    # Set check_prerequisites to BLOCKED
    mock_components[
        "supervisor"
    ].monitor.parallel_monitor.check_prerequisites.return_value = "BLOCKED"

    final_state = await orchestrator.run_workflow(simple_workflow)

    assert task.status == TaskStatus.BLOCKED
    assert len(final_state.execution_queue) == 0
    mock_components["worker"].execute.assert_not_called()
