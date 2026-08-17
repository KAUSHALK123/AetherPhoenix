from uuid import uuid4

import pytest
from shared.contracts.escalation import (
    EscalationReason,
    EscalationRequest,
    EscalationSeverity,
)
from shared.contracts.execution import HealingResult
from shared.contracts.permission import RiskLevel
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.workflow import (
    ExecutionMode,
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.escalation import EscalationHandler
from app.core.events.bus import EventBus
from app.core.events.models import Event as ModelEvent
from app.core.events.models import EventType as ModelEventType


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def escalation_handler(event_bus):
    return EscalationHandler(event_bus=event_bus)


@pytest.fixture
def sample_sws():
    workflow_id = uuid4()
    task_id = uuid4()
    metadata = WorkflowMetadata(
        workflow_id=workflow_id,
        goal="Test execution workflow",
        execution_mode=ExecutionMode.ASSISTED,
        status=WorkflowStatus.RUNNING,
    )
    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="Sample Task",
        description="Sample test task",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        priority=TaskPriority.MEDIUM,
        expected_output="Output",
        status=TaskStatus.RUNNING,
    )
    sws = SharedWorkflowState(
        metadata=metadata,
        tasks={task_id: task},
        execution_queue=[task_id],
        running_tasks=[task_id],
    )
    return sws, workflow_id, task_id


@pytest.mark.asyncio
async def test_permission_denial_escalation(escalation_handler, sample_sws):
    sws, workflow_id, task_id = sample_sws

    request = EscalationRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        reason=EscalationReason.PERMISSION_DENIED,
        details="User rejected file write permission",
        failure_context={"error_code": "PERMISSION_DENIED", "path": "/etc/config"},
        risk_level=RiskLevel.HIGH,
    )

    result = await escalation_handler.handle_escalation(request, sws=sws)

    assert result.workflow_id == workflow_id
    assert result.task_id == task_id
    assert result.reason == EscalationReason.PERMISSION_DENIED
    assert result.severity == EscalationSeverity.HIGH
    assert result.requires_user_intervention is True
    assert result.user_action_required is not None
    assert "Permission approval required" in result.user_action_required

    # Workflow state verification:
    assert sws.metadata.status == WorkflowStatus.BLOCKED
    assert sws.tasks[task_id].status == TaskStatus.BLOCKED
    assert task_id not in sws.execution_queue
    assert task_id not in sws.running_tasks
    assert task_id in sws.failed_tasks
    assert len(sws.escalations) == 1


@pytest.mark.asyncio
async def test_maximum_retry_reached_escalation(escalation_handler, sample_sws):
    sws, workflow_id, task_id = sample_sws

    request = EscalationRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        reason=EscalationReason.MAX_RETRIES_EXCEEDED,
        details="Task failed after 3 retries",
        failure_context={"retry_count": 3},
    )

    result = await escalation_handler.handle_escalation(request, sws=sws)

    assert result.reason == EscalationReason.MAX_RETRIES_EXCEEDED
    assert result.severity == EscalationSeverity.MEDIUM
    assert result.requires_user_intervention is True
    assert "Maximum task retries exceeded" in result.user_action_required
    assert task_id not in sws.execution_queue


@pytest.mark.asyncio
async def test_maximum_healing_attempts_reached(escalation_handler, sample_sws):
    sws, workflow_id, task_id = sample_sws

    request = EscalationRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        reason=EscalationReason.MAX_HEALING_ATTEMPTS_EXCEEDED,
        details="Healing agent attempt 3 failed to recover task",
        attempt_number=3,
    )

    result = await escalation_handler.handle_escalation(request, sws=sws)

    assert result.reason == EscalationReason.MAX_HEALING_ATTEMPTS_EXCEEDED
    assert result.severity == EscalationSeverity.HIGH
    assert result.requires_user_intervention is True
    assert (
        "Maximum autonomous healing recovery attempts reached"
        in result.user_action_required
    )


@pytest.mark.asyncio
async def test_unknown_critical_error_escalation(escalation_handler, sample_sws):
    sws, workflow_id, task_id = sample_sws

    request = EscalationRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        reason=EscalationReason.UNKNOWN_CRITICAL_FAILURE,
        details="Unhandled NullReferenceException in core engine",
        failure_context={"exception": "NullReferenceException", "trace": "line 42"},
    )

    result = await escalation_handler.handle_escalation(request, sws=sws)

    assert result.reason == EscalationReason.UNKNOWN_CRITICAL_FAILURE
    assert result.severity == EscalationSeverity.CRITICAL
    assert result.requires_user_intervention is True
    assert sws.metadata.status == WorkflowStatus.BLOCKED


@pytest.mark.asyncio
async def test_high_risk_operation_escalation(escalation_handler, sample_sws):
    sws, workflow_id, task_id = sample_sws

    request = EscalationRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        reason=EscalationReason.HIGH_RISK_OPERATION,
        details="Attempted registry modification",
        risk_level=RiskLevel.CRITICAL,
    )

    result = await escalation_handler.handle_escalation(request, sws=sws)

    assert result.reason == EscalationReason.HIGH_RISK_OPERATION
    assert result.severity == EscalationSeverity.CRITICAL
    assert result.requires_user_intervention is True
    assert "High-risk operation detected" in result.user_action_required


@pytest.mark.asyncio
async def test_user_intervention_required(escalation_handler):
    request = EscalationRequest(
        workflow_id=uuid4(),
        task_id=uuid4(),
        reason=EscalationReason.USER_INTERVENTION_REQUIRED,
        details="Manual captcha solving needed",
    )

    result = await escalation_handler.handle_escalation(request)

    assert result.requires_user_intervention is True
    assert result.user_action_required is not None


@pytest.mark.asyncio
async def test_non_critical_escalation(escalation_handler, sample_sws):
    sws, workflow_id, task_id = sample_sws

    request = EscalationRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        reason=EscalationReason.UNSUPPORTED_ERROR,
        details="Unsupported capability requested",
        risk_level=RiskLevel.LOW,
    )

    result = await escalation_handler.handle_escalation(request, sws=sws)

    assert result.reason == EscalationReason.UNSUPPORTED_ERROR
    assert result.severity == EscalationSeverity.MEDIUM


@pytest.mark.asyncio
async def test_duplicate_escalation_request(escalation_handler, sample_sws):
    sws, workflow_id, task_id = sample_sws

    request = EscalationRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        reason=EscalationReason.PERMISSION_DENIED,
        details="First escalation request",
    )

    res1 = await escalation_handler.handle_escalation(request, sws=sws)
    res2 = await escalation_handler.handle_escalation(request, sws=sws)

    assert res1.escalation_id == res2.escalation_id
    assert len(sws.escalations) == 1


@pytest.mark.asyncio
async def test_failure_context_and_healing_history_preservation(
    escalation_handler, sample_sws
):
    sws, workflow_id, task_id = sample_sws

    prior_healing = HealingResult(
        task_id=task_id,
        workflow_id=workflow_id,
        root_cause="Timeout",
        recovery_strategy="Retry",
        attempt_number=1,
        success=False,
    )

    failure_ctx = {
        "error_code": "NETWORK_TIMEOUT",
        "logs": ["Attempting request...", "Timed out after 30s"],
    }

    request = EscalationRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        reason=EscalationReason.MAX_HEALING_ATTEMPTS_EXCEEDED,
        details="Healing attempt failed",
        failure_context=failure_ctx,
        healing_history=[prior_healing],
    )

    result = await escalation_handler.handle_escalation(request, sws=sws)

    assert result.failure_context == failure_ctx
    assert len(result.healing_history) == 1
    assert result.healing_history[0].task_id == task_id
    assert result.healing_history[0].recovery_strategy == "Retry"


@pytest.mark.asyncio
async def test_event_generation(event_bus, escalation_handler):
    emitted_events = []

    async def callback(event: ModelEvent):
        emitted_events.append(event)

    event_bus.subscribe(ModelEventType.ESCALATION_REQUESTED, callback)
    event_bus.subscribe(ModelEventType.HEALING_ESCALATED, callback)

    workflow_id = uuid4()
    task_id = uuid4()
    request = EscalationRequest(
        workflow_id=workflow_id,
        task_id=task_id,
        reason=EscalationReason.PERMISSION_DENIED,
        details="Event emission test",
    )

    result = await escalation_handler.handle_escalation(request)

    assert len(emitted_events) == 2
    event_types = [e.event_type for e in emitted_events]
    assert ModelEventType.ESCALATION_REQUESTED in event_types
    assert ModelEventType.HEALING_ESCALATED in event_types
    assert emitted_events[0].payload["escalation_id"] == str(result.escalation_id)
