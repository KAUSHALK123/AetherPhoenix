import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID

from shared.contracts.escalation import (
    EscalationReason,
    EscalationRequest,
    EscalationResult,
    EscalationSeverity,
)
from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.permission import RiskLevel
from shared.contracts.task import TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowStatus

from app.core.events.bus import EventBus
from app.core.events.models import Event as ModelEvent
from app.core.events.models import EventType as ModelEventType

logger = logging.getLogger(__name__)


class EscalationHandler:
    """Escalation Handler for failures that cannot be safely or automatically

    recovered by the Healing Agent. Provides a controlled boundary between
    autonomous recovery and human intervention.
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        # Track active/processed escalations to prevent duplicate escalation loops:
        self._processed_escalations: Dict[Tuple[UUID, UUID], EscalationResult] = {}

    def classify_severity(
        self, reason: EscalationReason, risk_level: Optional[RiskLevel] = None
    ) -> EscalationSeverity:
        """Classifies escalation severity based on escalation reason and risk level."""
        if (
            reason
            in (
                EscalationReason.UNKNOWN_CRITICAL_FAILURE,
                EscalationReason.HARDWARE_FAILURE,
            )
            or risk_level == RiskLevel.CRITICAL
        ):
            return EscalationSeverity.CRITICAL

        if (
            reason
            in (
                EscalationReason.PERMISSION_DENIED,
                EscalationReason.MAX_HEALING_ATTEMPTS_EXCEEDED,
                EscalationReason.HIGH_RISK_OPERATION,
            )
            or risk_level == RiskLevel.HIGH
        ):
            return EscalationSeverity.HIGH

        if (
            reason
            in (
                EscalationReason.MAX_RETRIES_EXCEEDED,
                EscalationReason.UNSUPPORTED_ERROR,
                EscalationReason.USER_INTERVENTION_REQUIRED,
            )
            or risk_level == RiskLevel.MEDIUM
        ):
            return EscalationSeverity.MEDIUM

        return EscalationSeverity.LOW

    def determine_user_intervention(
        self, reason: EscalationReason, severity: EscalationSeverity
    ) -> Tuple[bool, Optional[str]]:
        """Determines whether human user intervention is required and formulates

        user action text.
        """
        requires_intervention = reason in (
            EscalationReason.PERMISSION_DENIED,
            EscalationReason.HIGH_RISK_OPERATION,
            EscalationReason.MAX_HEALING_ATTEMPTS_EXCEEDED,
            EscalationReason.MAX_RETRIES_EXCEEDED,
            EscalationReason.USER_INTERVENTION_REQUIRED,
            EscalationReason.UNKNOWN_CRITICAL_FAILURE,
            EscalationReason.HARDWARE_FAILURE,
        ) or severity in (EscalationSeverity.HIGH, EscalationSeverity.CRITICAL)

        if not requires_intervention:
            return False, None

        action_messages = {
            EscalationReason.PERMISSION_DENIED: (
                "Permission approval required. Please review permission request "
                "and authorize required tool execution."
            ),
            EscalationReason.HIGH_RISK_OPERATION: (
                "High-risk operation detected. Explicit user authorization is required "
                "before continuing execution."
            ),
            EscalationReason.MAX_HEALING_ATTEMPTS_EXCEEDED: (
                "Maximum autonomous healing recovery attempts reached. "
                "Manual intervention required to inspect task failure."
            ),
            EscalationReason.MAX_RETRIES_EXCEEDED: (
                "Maximum task retries exceeded. Manual inspection of environment "
                "or task parameters required."
            ),
            EscalationReason.UNKNOWN_CRITICAL_FAILURE: (
                "Critical unknown failure encountered. System execution paused for "
                "technical log inspection."
            ),
            EscalationReason.HARDWARE_FAILURE: (
                "Hardware component or physical device unavailable. Please inspect "
                "hardware state."
            ),
            EscalationReason.USER_INTERVENTION_REQUIRED: (
                "Manual user intervention required to proceed with workflow execution."
            ),
        }

        user_action = action_messages.get(
            reason, "User intervention required to resolve escalated failure."
        )
        return True, user_action

    async def handle_escalation(
        self,
        request: EscalationRequest,
        sws: Optional[SharedWorkflowState] = None,
    ) -> EscalationResult:
        """Processes an escalation request, classifies severity, updates workflow state,

        emits escalation events, logs details, and halts further retries.
        """
        cache_key = (request.workflow_id, request.task_id)

        # Check for duplicate escalation request for same workflow and task:
        if cache_key in self._processed_escalations:
            existing = self._processed_escalations[cache_key]
            logger.warning(
                "Duplicate escalation request received for workflow %s, task %s. "
                "Returning existing escalation %s.",
                request.workflow_id,
                request.task_id,
                existing.escalation_id,
            )
            return existing

        severity = self.classify_severity(request.reason, request.risk_level)
        (
            requires_user_intervention,
            user_action_required,
        ) = self.determine_user_intervention(request.reason, severity)

        escalation_result = EscalationResult(
            workflow_id=request.workflow_id,
            task_id=request.task_id,
            reason=request.reason,
            severity=severity,
            requires_user_intervention=requires_user_intervention,
            user_action_required=user_action_required,
            failure_context=request.failure_context,
            healing_history=request.healing_history,
            timestamp=datetime.now(timezone.utc),
        )

        self._processed_escalations[cache_key] = escalation_result

        # Log escalation details:
        log_level = (
            logging.ERROR
            if severity in (EscalationSeverity.HIGH, EscalationSeverity.CRITICAL)
            else logging.WARNING
        )
        logger.log(
            log_level,
            "Escalation Handled [ID: %s] Reason: %s | Severity: %s | "
            "User Intervention: %s | Workflow: %s | Task: %s | Details: %s",
            escalation_result.escalation_id,
            escalation_result.reason.value,
            escalation_result.severity.value,
            escalation_result.requires_user_intervention,
            request.workflow_id,
            request.task_id,
            request.details,
        )

        # Update Shared Workflow State if provided:
        if sws is not None:
            self._update_workflow_state(sws, escalation_result)

        # Emit escalation events:
        await self._emit_escalation_events(escalation_result, request.details)

        return escalation_result

    def _update_workflow_state(
        self, sws: SharedWorkflowState, escalation_result: EscalationResult
    ) -> None:
        """Updates Shared Workflow State with escalation details, status transitions,

        and halts execution queues.
        """
        # Preserve escalation record in SWS:
        if hasattr(sws, "escalations"):
            sws.escalations.append(escalation_result)

        task_id = escalation_result.task_id

        # Update specific task status:
        if task_id in sws.tasks:
            task = sws.tasks[task_id]
            task.status = (
                TaskStatus.BLOCKED
                if escalation_result.requires_user_intervention
                else TaskStatus.ESCALATED
            )
            task.finished_at = datetime.now(timezone.utc)
            task.execution_logs.append(
                f"ESCALATION: Reason={escalation_result.reason.value}, "
                f"Severity={escalation_result.severity.value}, "
                f"Action={escalation_result.user_action_required}"
            )

        # Update queues:
        if task_id in sws.execution_queue:
            sws.execution_queue.remove(task_id)
        if task_id in sws.running_tasks:
            sws.running_tasks.remove(task_id)
        if task_id not in sws.failed_tasks:
            sws.failed_tasks.append(task_id)

        # Update top-level workflow status:
        if escalation_result.requires_user_intervention:
            sws.metadata.status = WorkflowStatus.BLOCKED
        else:
            sws.metadata.status = WorkflowStatus.ESCALATED

        # Append structured log entry to SWS:
        sws.logs.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "component": "EscalationHandler",
                "level": escalation_result.severity.value,
                "message": (
                    f"Task {task_id} escalated due to "
                    f"{escalation_result.reason.value}. "
                    f"User intervention required: "
                    f"{escalation_result.requires_user_intervention}"
                ),
                "escalation_id": str(escalation_result.escalation_id),
            }
        )

    async def _emit_escalation_events(
        self, escalation_result: EscalationResult, details: str
    ) -> None:
        """Publishes escalation events to the EventBus if configured."""
        if self.event_bus is None:
            return

        payload = {
            "escalation_id": str(escalation_result.escalation_id),
            "workflow_id": str(escalation_result.workflow_id),
            "task_id": str(escalation_result.task_id),
            "reason": escalation_result.reason.value,
            "severity": escalation_result.severity.value,
            "requires_user_intervention": (
                escalation_result.requires_user_intervention
            ),
            "user_action_required": escalation_result.user_action_required,
            "details": details,
            "failure_context": escalation_result.failure_context,
            "healing_history_count": len(escalation_result.healing_history),
            "timestamp": escalation_result.timestamp.isoformat(),
        }

        # Model events for internal bus:
        model_event_requested = ModelEvent(
            workflow_id=str(escalation_result.workflow_id),
            task_id=str(escalation_result.task_id),
            event_type=ModelEventType.ESCALATION_REQUESTED,
            source_component="HEALING",
            payload=payload,
        )

        model_event_escalated = ModelEvent(
            workflow_id=str(escalation_result.workflow_id),
            task_id=str(escalation_result.task_id),
            event_type=ModelEventType.HEALING_ESCALATED,
            source_component="HEALING",
            payload=payload,
        )

        # Track runtime event in SWS/contract payload:
        _ = RuntimeEvent(
            workflow_id=escalation_result.workflow_id,
            task_id=escalation_result.task_id,
            event_type=EventType.ESCALATION_REQUESTED,
            source_component=EventSource.HEALING,
            payload=payload,
        )

        await self.event_bus.publish(model_event_requested)
        await self.event_bus.publish(model_event_escalated)
