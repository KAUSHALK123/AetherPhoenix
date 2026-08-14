import logging
import re
from typing import Optional

from shared.contracts.execution import FailureType, HealingResult, TaskFailureReport
from shared.contracts.feedback import (
    CapabilityFailureInfo,
    FailureSummary,
    HealingSummary,
    PlannerFeedback,
    ReplanningContext,
)
from shared.contracts.workflow import SharedWorkflowState

from app.core.events.bus import EventBus, get_event_bus
from app.core.events.models import Event
from app.core.events.models import EventType as ModelEventType

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = [
    # API Keys / Tokens
    r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|bearer|secret|password|passwd|pwd|private[_-]?key|credentials|token|passphrase)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.\~]{8,}['\"]",
    r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|bearer|secret|password|passwd|pwd|private[_-]?key|credentials|token|passphrase)\s*[:=]\s*[a-zA-Z0-9_\-\.\~]{8,}",
    # Database URLs / Connection Strings
    r"(?i)(mongodb(?:\+srv)?|postgres|mysql|sqlite|redis|amqp|s?ftp)://[^:\s]+:[^@\s]+@[^\s]+",
    # Basic Authorization Headers / Base64 patterns
    r"(?i)(Authorization)\s*[:=]\s*(?:Basic|Bearer)\s+[a-zA-Z0-9\+/=\-_]{10,}",
    # Private Key blocks
    r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----",
]


def sanitize_sensitive_data(text: str) -> str:
    """Masks secret keys, passwords, database credentials, and auth tokens."""
    if not text:
        return text
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:

        def repl(match):
            if match.lastindex and match.lastindex >= 1:
                return f"{match.group(1)}: [REDACTED]"
            return "[REDACTED]"

        sanitized = re.sub(pattern, repl, sanitized)
    return sanitized


class PlannerFeedbackLoop:
    """
    Coordinates gathering execution and healing summaries, validating and sanitizing
    information, publishing events, and preparing structured feedback for the
    Planner Agent.
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus or get_event_bus()

    def generate_feedback(
        self,
        state: SharedWorkflowState,
        failure_report: Optional[TaskFailureReport] = None,
        healing_result: Optional[HealingResult] = None,
    ) -> PlannerFeedback:
        """
        Creates and returns a validated, sanitized PlannerFeedback package.
        """
        failure_summary = None
        if failure_report:
            task = state.tasks.get(failure_report.task_id)
            task_name = task.task_name if task else "Unknown Task"
            tool_used = task.required_tool if task else "Unknown Tool"

            sanitized_msg = sanitize_sensitive_data(failure_report.message)

            failure_summary = FailureSummary(
                task_id=failure_report.task_id,
                task_name=task_name,
                tool_used=tool_used,
                failure_type=failure_report.failure_type,
                error_message=sanitized_msg,
                timestamp=failure_report.detected_at,
            )

        healing_summary = None
        if healing_result:
            outcome = "SUCCESS" if healing_result.success else "FAILED"
            if not healing_result.success:
                outcome = "UNRECOVERABLE"

            healing_summary = HealingSummary(
                recovery_id=healing_result.recovery_id,
                attempts=healing_result.attempt_number,
                strategies_attempted=(
                    [healing_result.recovery_strategy]
                    if healing_result.recovery_strategy
                    else []
                ),
                successful_strategy=(
                    healing_result.recovery_strategy if healing_result.success else None
                ),
                outcome=outcome,
                timestamp=healing_result.timestamp,
            )

        capability_failure = None
        if failure_report and failure_report.failure_type in (
            FailureType.TOOL_UNAVAILABLE,
            FailureType.PERMISSION_DENIED,
        ):
            task = state.tasks.get(failure_report.task_id)
            tool_name = task.required_tool if task else "Unknown Tool"
            category = task.category.value if task else "OTHER"
            is_permanent = not failure_report.retryability

            capability_failure = CapabilityFailureInfo(
                tool_name=tool_name,
                category=category,
                is_permanent=is_permanent,
                details=sanitize_sensitive_data(failure_report.message),
            )

        # Replanning Context
        replanning_context = None
        replanning_recommended = False
        trigger_reason = ""

        if healing_summary and healing_summary.outcome == "UNRECOVERABLE":
            replanning_recommended = True
            trigger_reason = (
                f"Healing failed to recover task: "
                f"{failure_summary.task_name if failure_summary else 'Unknown'}"
            )
        elif capability_failure and capability_failure.is_permanent:
            replanning_recommended = True
            trigger_reason = (
                f"Permanent capability failure detected on tool: "
                f"{capability_failure.tool_name}"
            )
        elif failure_report and not failure_report.retryability:
            replanning_recommended = True
            trigger_reason = f"Non-retryable task failure: {failure_report.message}"

        if replanning_recommended:
            blocked_tasks = []
            if failure_report:
                blocked_tasks = [
                    t_id
                    for t_id, t in state.tasks.items()
                    if t.status == "BLOCKED" or failure_report.task_id in t.dependencies
                ]

            replanning_context = ReplanningContext(
                trigger_reason=sanitize_sensitive_data(trigger_reason),
                original_goal=state.metadata.goal,
                suggested_alternative_tools=[],
                suggested_alternative_capabilities=[],
                blocked_tasks=blocked_tasks,
            )

        feedback = PlannerFeedback(
            workflow_id=state.metadata.workflow_id,
            failure_summary=failure_summary,
            healing_summary=healing_summary,
            capability_failure=capability_failure,
            replanning_context=replanning_context,
        )

        return feedback

    async def process_and_publish_feedback(
        self,
        state: SharedWorkflowState,
        failure_report: Optional[TaskFailureReport] = None,
        healing_result: Optional[HealingResult] = None,
    ) -> PlannerFeedback:
        """
        Generates feedback, publishes events via the Event Bus, and
        returns the feedback.
        """
        feedback = self.generate_feedback(state, failure_report, healing_result)

        # 1. Publish Event via Core Event Bus
        core_event = Event(
            workflow_id=str(state.metadata.workflow_id),
            event_type=ModelEventType.FEEDBACK_GENERATED,
            source_component="PlannerFeedbackLoop",
            payload=feedback.model_dump(mode="json"),
        )
        await self.event_bus.publish(core_event)

        # 2. Publish Replanning Event if recommended
        if feedback.replanning_context:
            replanning_event = Event(
                workflow_id=str(state.metadata.workflow_id),
                event_type=ModelEventType.REPLANNING_TRIGGERED,
                source_component="PlannerFeedbackLoop",
                payload={"trigger_reason": feedback.replanning_context.trigger_reason},
            )
            await self.event_bus.publish(replanning_event)

        return feedback
