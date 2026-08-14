"""
AetherPhoenix — Healing Core Agent
===================================
Main Healing Agent implementation responsible for analyzing workflow & task
execution failures, consuming normalized error representations from ErrorParser,
determining root causes, formulating recovery strategies, and emitting healing
lifecycle events.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from shared.contracts.execution import HealingResult
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.error_parser import ErrorParser
from app.agents.healing.models import (
    NormalizedError,
)
from app.core.events.bus import EventBus
from app.core.events.models import EventType
from app.core.logging import get_logger

logger = get_logger(__name__)


class HealingRequest(BaseModel):
    """Payload for requesting recovery analysis from Healing Agent."""

    task_id: UUID
    workflow_id: UUID
    raw_error: Any
    attempt_number: int = Field(default=1, ge=1)
    context: Dict[str, Any] = Field(default_factory=dict)


class HealingAgent:
    """
    Healing Agent Core component.

    Integrates with ErrorParser to convert raw failures into normalized error
    models across Worker, Tool, Supervisor, Permission, Filesystem, Network,
    Browser, PowerShell, and System layers without executing recovery tools directly.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        error_parser: Optional[ErrorParser] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus()
        self.error_parser = error_parser or ErrorParser()

    def parse_error(
        self,
        raw_error: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> NormalizedError:
        """
        Parses and normalizes a raw error into a structured NormalizedError.

        Delegates parsing to ErrorParser.
        """
        return self.error_parser.parse(raw_error, context)

    async def execute(
        self,
        request: HealingRequest,
        state: Optional[SharedWorkflowState] = None,
        **kwargs: Any,
    ) -> HealingResult:
        """
        Main entrypoint for Healing Agent execution.

        Parses raw error, analyzes failure details, determines root cause,
        publishes healing events, updates workflow state, and returns HealingResult.
        """
        logger.info(
            f"HealingAgent evaluating failure for workflow {request.workflow_id}, "
            f"task {request.task_id}"
        )

        await self._emit_event(
            EventType.HEALING_STARTED,
            {
                "task_id": str(request.task_id),
                "attempt_number": request.attempt_number,
                "status": "STARTED",
            },
            str(request.workflow_id),
            str(request.task_id),
        )

        # 1. Parse and normalize error using ErrorParser
        normalized_error = self.parse_error(request.raw_error, request.context)

        logger.info(
            f"Normalized Error -> Category: {normalized_error.category.value}, "
            f"Source: {normalized_error.source.value}, "
            f"Severity: {normalized_error.severity.value}, "
            f"Retryable: {normalized_error.is_retryable}"
        )

        # 2. Formulate strategy based on normalized classification
        is_success = normalized_error.is_retryable
        root_cause_str = normalized_error.category.value
        strategy_str = "RETRY" if is_success else "ESCALATE"

        replacement_tasks: List[Task] = []
        target_task: Optional[Task] = None

        if state is not None:
            target_task = state.tasks.get(request.task_id)
            if target_task:
                target_task.status = TaskStatus.HEALING
                if is_success:
                    target_task.retry_count = request.attempt_number
                    replacement = target_task.model_copy(
                        update={
                            "status": TaskStatus.WAITING,
                            "retry_count": request.attempt_number,
                            "execution_logs": list(target_task.execution_logs)
                            + [f"Healing recovery attempt #{request.attempt_number}"],
                        }
                    )
                    replacement_tasks.append(replacement)
                    target_task.status = TaskStatus.WAITING
                else:
                    target_task.status = TaskStatus.FAILED

        result = HealingResult(
            task_id=request.task_id,
            workflow_id=request.workflow_id,
            root_cause=root_cause_str,
            recovery_strategy=strategy_str,
            replacement_tasks=replacement_tasks,
            attempt_number=request.attempt_number,
            success=is_success,
        )

        if state is not None:
            state.healing_history.append(result)

        # 3. Emit outcome events
        if is_success:
            await self._emit_event(
                EventType.HEALING_COMPLETED,
                {
                    "task_id": str(request.task_id),
                    "success": True,
                    "root_cause": root_cause_str,
                    "strategy": strategy_str,
                    "normalized_category": normalized_error.category.value,
                    "normalized_source": normalized_error.source.value,
                },
                str(request.workflow_id),
                str(request.task_id),
            )
        else:
            await self._emit_event(
                EventType.HEALING_FAILED,
                {
                    "task_id": str(request.task_id),
                    "success": False,
                    "root_cause": root_cause_str,
                    "strategy": strategy_str,
                    "normalized_category": normalized_error.category.value,
                    "normalized_source": normalized_error.source.value,
                },
                str(request.workflow_id),
                str(request.task_id),
            )

        return result

    async def _emit_event(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        workflow_id: str,
        task_id: str,
    ) -> None:
        """Helper to publish events on EventBus safely."""
        try:
            await self.event_bus.publish_async(
                event_type=event_type,
                source_component="HealingAgent",
                workflow_id=workflow_id,
                task_id=task_id,
                payload=payload,
            )
        except Exception as exc:
            logger.warning(f"Failed to publish event {event_type}: {exc}")


__all__ = [
    "HealingRequest",
    "HealingAgent",
]
