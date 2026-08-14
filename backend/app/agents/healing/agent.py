import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from shared.contracts.escalation import (
    EscalationReason,
    EscalationRequest,
    EscalationResult,
)
from shared.contracts.execution import HealingResult, TaskError
from shared.contracts.permission import RiskLevel
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.escalation import EscalationHandler
from app.core.events.bus import EventBus
from app.core.events.models import Event as ModelEvent
from app.core.events.models import EventType as ModelEventType
from app.runtime.interfaces import AgentRegistration, BaseAgent

logger = logging.getLogger(__name__)

NON_RECOVERABLE_ERROR_CODES = {
    "PERMISSION_DENIED",
    "UNSUPPORTED_ERROR",
    "HARDWARE_FAILURE",
    "USER_REJECTED",
    "INVALID_PERMISSION",
}


class HealingAgent(BaseAgent):
    """Healing Agent responsible for recovering failed workflow executions.

    Analyzes failures, generates recovery strategies, and delegates unrecoverable
    or high-risk failures to the EscalationHandler.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        escalation_handler: Optional[EscalationHandler] = None,
        max_healing_attempts: int = 3,
    ) -> None:
        self.event_bus = event_bus
        self.escalation_handler = escalation_handler or EscalationHandler(
            event_bus=event_bus
        )
        self.max_healing_attempts = max_healing_attempts
        self.healing_history: List[HealingResult] = []

    @property
    def registration(self) -> AgentRegistration:
        """Returns registration metadata for the Healing Agent."""
        return AgentRegistration(
            name="HealingAgent",
            version="1.0.0",
            description=(
                "Analyzes task failures, plans autonomous recovery strategies, "
                "and escalates unrecoverable failures."
            ),
        )

    async def initialize(self) -> None:
        """Lifecycle hook: Called when the agent is registered with the kernel."""
        logger.info("HealingAgent initialized.")
        if self.event_bus:
            self.event_bus.subscribe(
                ModelEventType.HEALING_FAILED, self.handle_healing_failed_event
            )

    async def shutdown(self) -> None:
        """Lifecycle hook: Called when the kernel shuts down."""
        logger.info("HealingAgent shut down.")
        if self.event_bus:
            self.event_bus.unsubscribe(
                ModelEventType.HEALING_FAILED, self.handle_healing_failed_event
            )

    async def handle_healing_failed_event(self, event: ModelEvent) -> None:
        """Event handler for HEALING_FAILED events."""
        logger.warning("HealingAgent received HEALING_FAILED event: %s", event.payload)

    def is_recoverable(
        self,
        error_code: Optional[str],
        attempt_number: int,
        risk_level: Optional[RiskLevel] = None,
    ) -> Tuple[bool, Optional[EscalationReason]]:
        """Determines if a failure is recoverable or requires escalation."""
        if (
            error_code in NON_RECOVERABLE_ERROR_CODES
            or error_code == "PERMISSION_DENIED"
        ):
            return False, EscalationReason.PERMISSION_DENIED

        if risk_level == RiskLevel.CRITICAL or risk_level == RiskLevel.HIGH:
            return False, EscalationReason.HIGH_RISK_OPERATION

        if attempt_number >= self.max_healing_attempts:
            return False, EscalationReason.MAX_HEALING_ATTEMPTS_EXCEEDED

        return True, None

    async def evaluate_and_heal(
        self,
        workflow_id: UUID,
        task_id: UUID,
        error: TaskError,
        attempt_number: int = 1,
        risk_level: Optional[RiskLevel] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        sws: Optional[SharedWorkflowState] = None,
    ) -> Union[HealingResult, EscalationResult]:
        """Evaluates a failure report.

        Generates a HealingResult if recoverable, or delegates to EscalationHandler
        if unrecoverable.
        """
        execution_context = execution_context or {}
        recoverable, escalation_reason = self.is_recoverable(
            error.error_code, attempt_number, risk_level
        )

        if not recoverable and escalation_reason:
            logger.warning(
                "Task failure is unrecoverable (Reason: %s). "
                "Delegating to EscalationHandler.",
                escalation_reason.value,
            )
            request = EscalationRequest(
                workflow_id=workflow_id,
                task_id=task_id,
                reason=escalation_reason,
                details=f"Unrecoverable failure: {error.error_message}",
                failure_context={
                    "error_code": error.error_code,
                    "error_message": error.error_message,
                    "stack_trace": error.stack_trace,
                    "execution_context": execution_context,
                },
                healing_history=list(self.healing_history),
                attempt_number=attempt_number,
                risk_level=risk_level,
            )
            return await self.escalation_handler.handle_escalation(request, sws=sws)

        # Autonomous healing path:
        healing_result = HealingResult(
            task_id=task_id,
            workflow_id=workflow_id,
            root_cause=f"Tool error: {error.error_code}",
            recovery_strategy="RETRY_TASK",
            replacement_tasks=[],
            attempt_number=attempt_number,
            success=True,
        )
        self.healing_history.append(healing_result)
        if sws:
            sws.healing_history.append(healing_result)
        return healing_result

    async def execute(self, *args, **kwargs) -> Any:
        """Main execution entry point for HealingAgent."""
        return await self.evaluate_and_heal(*args, **kwargs)
