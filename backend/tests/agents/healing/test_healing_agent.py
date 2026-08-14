from uuid import uuid4

import pytest

from shared.contracts.event import EventType
from shared.contracts.execution import (
    ExecutionMetrics,
    ExecutionResult,
    FailureType,
    HealingRequest,
    HealingResult,
    HealingState,
    RecoveryStrategyType,
    RootCauseCategory,
    SupervisorDecision,
    SupervisorValidation,
    TaskError,
    TaskFailureReport,
)
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.workflow import (
    ExecutionMode,
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)
from app.agents.healing.agent import HealingAgent
from app.core.events.bus import EventBus
from app.core.exceptions import ValidationException


@pytest.fixture
def mock_event_bus():
    return EventBus()


@pytest.fixture
def healing_agent(mock_event_bus):
    return HealingAgent(event_bus=mock_event_bus, max_healing_attempts=3)


@pytest.fixture
def sample_workflow_context():
    workflow_id = uuid4()
    task_id = uuid4()

    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="Sample Web Search",
        description="Search for python documentation",
        required_tool="web_search",
        category=TaskCategory.SEARCH,
        expected_output="Search results",
        status=TaskStatus.FAILED,
        retry_count=0,
    )

    metadata = WorkflowMetadata(
        workflow_id=workflow_id,
        goal="Run automated search",
        execution_mode=ExecutionMode.SAFE,
        status=WorkflowStatus.RUNNING,
    )

    state = SharedWorkflowState(
        metadata=metadata,
        tasks={task_id: task},
        failed_tasks=[task_id],
    )

    return workflow_id, task_id, task, state


@pytest.mark.asyncio
async def test_agent_registration_and_lifecycle(healing_agent):
    registration = healing_agent.registration
    assert registration.name == "HealingAgent"
    assert registration.version == "1.0.0"

    await healing_agent.initialize()
    assert healing_agent.current_state == HealingState.IDLE
    await healing_agent.shutdown()


@pytest.mark.asyncio
async def test_valid_healing_request_execution(healing_agent, sample_workflow_context):
    workflow_id, task_id, task, state = sample_workflow_context

    request = HealingRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        error_message="Network request timed out",
        attempt_number=1,
    )

    result = await healing_agent.execute(request, state=state)

    assert isinstance(result, HealingResult)
    assert result.workflow_id == workflow_id
    assert result.task_id == task_id
    assert result.success is True
    assert result.recovery_strategy == RecoveryStrategyType.RETRY.value
    assert result.root_cause_category == RootCauseCategory.TIMEOUT
    assert result.healing_state == HealingState.COMPLETED
    assert len(result.replacement_tasks) == 1
    assert result.replacement_tasks[0].task_id == task_id
    assert result.replacement_tasks[0].retry_count == 1

    # Verify SWS update
    assert len(state.healing_history) == 1
    assert state.healing_history[0] == result
    assert task.status == TaskStatus.WAITING


@pytest.mark.asyncio
async def test_task_failure_report_input(healing_agent, sample_workflow_context):
    workflow_id, task_id, task, state = sample_workflow_context

    failure_report = TaskFailureReport(
        task_id=task_id,
        workflow_id=workflow_id,
        failure_type=FailureType.TIMEOUT,
        message="Browser step timed out",
        retryability=True,
    )

    result = await healing_agent.execute(failure_report, state=state)

    assert result.success is True
    assert result.root_cause_category == RootCauseCategory.TIMEOUT
    assert result.recovery_strategy == RecoveryStrategyType.RETRY.value


@pytest.mark.asyncio
async def test_execution_result_input(healing_agent, sample_workflow_context):
    workflow_id, task_id, task, state = sample_workflow_context

    exec_result = ExecutionResult(
        task_id=task_id,
        workflow_id=workflow_id,
        success=False,
        error=TaskError(
            error_code="TEMPORARY_NETWORK_ERROR",
            error_message="Connection reset by peer",
            is_recoverable=True,
        ),
    )

    result = await healing_agent.execute(exec_result, state=state)

    assert result.success is True
    assert result.root_cause_category == RootCauseCategory.NETWORK_ERROR
    assert result.recovery_strategy == RecoveryStrategyType.RETRY.value


@pytest.mark.asyncio
async def test_supervisor_validation_input(healing_agent, sample_workflow_context):
    workflow_id, task_id, task, state = sample_workflow_context

    validation = SupervisorValidation(
        task_id=task_id,
        workflow_id=workflow_id,
        is_valid=False,
        decision=SupervisorDecision.FAILED,
        issues=["Tool execution returned error output"],
    )

    result = await healing_agent.execute(validation, state=state)

    assert result.workflow_id == workflow_id
    assert result.task_id == task_id
    assert isinstance(result, HealingResult)


@pytest.mark.asyncio
async def test_dict_input(healing_agent, sample_workflow_context):
    workflow_id, task_id, task, state = sample_workflow_context

    dict_request = {
        "workflow_id": str(workflow_id),
        "task_id": str(task_id),
        "error_message": "Tool command not found",
        "attempt_number": 1,
    }

    result = await healing_agent.execute(dict_request, state=state)

    assert result.success is True
    assert result.root_cause_category == RootCauseCategory.TOOL_FAILURE
    assert result.recovery_strategy == RecoveryStrategyType.RESTART_TOOL.value


@pytest.mark.asyncio
async def test_unknown_workflow(healing_agent, sample_workflow_context):
    _, task_id, task, state = sample_workflow_context
    unknown_wf_id = uuid4()

    request = HealingRequest(
        workflow_id=unknown_wf_id,
        task_id=task_id,
        error_message="Some error",
    )

    result = await healing_agent.execute(request, state=state)

    assert result.success is False
    assert result.healing_state == HealingState.ESCALATED
    assert result.recovery_strategy == RecoveryStrategyType.ESCALATE.value
    assert result.root_cause_category == RootCauseCategory.WORKFLOW_ERROR
    assert "Unknown workflow ID" in (result.escalation_reason or "")


@pytest.mark.asyncio
async def test_unknown_task(healing_agent, sample_workflow_context):
    workflow_id, _, task, state = sample_workflow_context
    unknown_task_id = uuid4()

    request = HealingRequest(
        workflow_id=workflow_id,
        task_id=unknown_task_id,
        error_message="Some error",
    )

    result = await healing_agent.execute(request, state=state)

    assert result.success is False
    assert result.healing_state == HealingState.ESCALATED
    assert result.recovery_strategy == RecoveryStrategyType.ESCALATE.value
    assert result.root_cause_category == RootCauseCategory.WORKFLOW_ERROR
    assert "Unknown task ID" in (result.escalation_reason or "")


@pytest.mark.asyncio
async def test_max_attempts_exceeded_escalation(healing_agent, sample_workflow_context):
    workflow_id, task_id, task, state = sample_workflow_context
    task.retry_count = 3  # Max healing attempts is 3

    request = HealingRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        error_message="Network request timed out",
    )

    result = await healing_agent.execute(request, state=state)

    assert result.success is False
    assert result.healing_state == HealingState.ESCALATED
    assert result.recovery_strategy == RecoveryStrategyType.ESCALATE.value
    assert "Exceeded maximum healing attempts" in (result.escalation_reason or "")
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_non_retryable_failure_escalation(healing_agent, sample_workflow_context):
    workflow_id, task_id, task, state = sample_workflow_context

    failure_report = TaskFailureReport(
        task_id=task_id,
        workflow_id=workflow_id,
        failure_type=FailureType.PERMISSION_DENIED,
        message="Permission denied by OS",
        retryability=False,
    )

    result = await healing_agent.execute(failure_report, state=state)

    assert result.success is False
    assert result.healing_state == HealingState.ESCALATED
    assert result.recovery_strategy == RecoveryStrategyType.ESCALATE.value
    assert result.root_cause_category == RootCauseCategory.PERMISSION_DENIED


@pytest.mark.asyncio
async def test_invalid_healing_request_raises(healing_agent):
    with pytest.raises(ValidationException):
        await healing_agent.execute("invalid_string_payload")

    with pytest.raises(ValidationException):
        await healing_agent.execute(
            {"workflow_id": "not_a_valid_uuid", "task_id": "123"}
        )


@pytest.mark.asyncio
async def test_event_bus_publishing(
    healing_agent, mock_event_bus, sample_workflow_context
):
    workflow_id, task_id, task, state = sample_workflow_context
    emitted_events = []

    async def event_handler(event):
        emitted_events.append(event)

    mock_event_bus.subscribe_all(event_handler)

    request = HealingRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        error_message="Timeout during execution",
    )

    await healing_agent.execute(request, state=state)

    event_types = [e.event_type for e in emitted_events]
    assert EventType.HEALING_STARTED in event_types
    assert EventType.HEALING_COMPLETED in event_types
