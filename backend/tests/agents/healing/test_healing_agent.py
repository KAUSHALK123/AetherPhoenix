from uuid import uuid4

import pytest
from shared.contracts.escalation import (
    EscalationReason,
    EscalationResult,
    EscalationSeverity,
)
from shared.contracts.execution import HealingResult, TaskError
from shared.contracts.permission import RiskLevel

from app.agents.healing.agent import HealingAgent
from app.agents.healing.escalation import EscalationHandler
from app.core.events.bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def healing_agent(event_bus):
    handler = EscalationHandler(event_bus=event_bus)
    return HealingAgent(
        event_bus=event_bus, escalation_handler=handler, max_healing_attempts=3
    )


@pytest.mark.asyncio
async def test_healing_agent_registration(healing_agent):
    reg = healing_agent.registration
    assert reg.name == "HealingAgent"
    assert reg.version == "1.0.0"


@pytest.mark.asyncio
async def test_healing_agent_recoverable_failure(healing_agent):
    workflow_id = uuid4()
    task_id = uuid4()
    error = TaskError(
        error_code="TIMEOUT",
        error_message="Network request timed out",
        is_recoverable=True,
    )

    result = await healing_agent.evaluate_and_heal(
        workflow_id=workflow_id,
        task_id=task_id,
        error=error,
        attempt_number=1,
    )

    assert isinstance(result, HealingResult)
    assert result.success is True
    assert result.task_id == task_id
    assert result.recovery_strategy == "RETRY_TASK"


@pytest.mark.asyncio
async def test_healing_agent_delegates_permission_denied_to_escalation(
    healing_agent,
):
    workflow_id = uuid4()
    task_id = uuid4()
    error = TaskError(
        error_code="PERMISSION_DENIED",
        error_message="Access to file denied",
        is_recoverable=False,
    )

    result = await healing_agent.evaluate_and_heal(
        workflow_id=workflow_id,
        task_id=task_id,
        error=error,
        attempt_number=1,
    )

    assert isinstance(result, EscalationResult)
    assert result.reason == EscalationReason.PERMISSION_DENIED
    assert result.severity == EscalationSeverity.HIGH
    assert result.requires_user_intervention is True


@pytest.mark.asyncio
async def test_healing_agent_delegates_max_attempts_to_escalation(
    healing_agent,
):
    workflow_id = uuid4()
    task_id = uuid4()
    error = TaskError(
        error_code="TOOL_ERROR",
        error_message="Tool failed continuously",
        is_recoverable=True,
    )

    result = await healing_agent.evaluate_and_heal(
        workflow_id=workflow_id,
        task_id=task_id,
        error=error,
        attempt_number=3,  # Max healing attempts reached
    )

    assert isinstance(result, EscalationResult)
    assert result.reason == EscalationReason.MAX_HEALING_ATTEMPTS_EXCEEDED
    assert result.requires_user_intervention is True


@pytest.mark.asyncio
async def test_healing_agent_delegates_high_risk_to_escalation(healing_agent):
    workflow_id = uuid4()
    task_id = uuid4()
    error = TaskError(
        error_code="HIGH_RISK_ACTION",
        error_message="Risk score exceeded safety threshold",
        is_recoverable=False,
    )

    result = await healing_agent.evaluate_and_heal(
        workflow_id=workflow_id,
        task_id=task_id,
        error=error,
        attempt_number=1,
        risk_level=RiskLevel.CRITICAL,
    )

    assert isinstance(result, EscalationResult)
    assert result.reason == EscalationReason.HIGH_RISK_OPERATION
    assert result.severity == EscalationSeverity.CRITICAL
