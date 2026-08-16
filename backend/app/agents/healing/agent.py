"""
AetherPhoenix — Healing Core Agent
===================================
Main Healing Agent implementation responsible for analyzing workflow & task
execution failures, determining root causes, formulating recovery strategies,
and emitting healing lifecycle events.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from shared.contracts.execution import (
    ExecutionResult,
    FailureType,
    HealingResult,
    SupervisorValidation,
    TaskFailureReport,
)
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.error_parser import ErrorParser
from app.core.events.bus import EventBus
from app.core.events.models import Event as ModelEvent
from app.core.events.models import EventType
from app.core.exceptions import ValidationException
from app.runtime.interfaces import AgentRegistration, BaseAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Local enums & models (not yet promoted to shared contracts)
# ---------------------------------------------------------------------------


class HealingState(str, Enum):
    IDLE = "IDLE"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    GENERATING_TASKS = "GENERATING_TASKS"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


class RootCauseCategory(str, Enum):
    PERMISSION_DENIED = "PERMISSION_DENIED"
    USER_REJECTED = "USER_REJECTED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    TOOL_FAILURE = "TOOL_FAILURE"
    EXTERNAL_API = "EXTERNAL_API"
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"


class RecoveryStrategyType(str, Enum):
    RETRY = "RETRY"
    RESTART_TOOL = "RESTART_TOOL"
    ALTERNATIVE_TOOL = "ALTERNATIVE_TOOL"
    WAIT = "WAIT"
    ESCALATE = "ESCALATE"


class HealingRequest(BaseModel):
    """Payload for requesting recovery analysis from Healing Agent."""

    task_id: UUID
    workflow_id: UUID
    error_message: Optional[str] = None
    attempt_number: int = Field(default=1, ge=1)
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    failure_report: Optional[TaskFailureReport] = None
    execution_result: Optional[ExecutionResult] = None
    validation: Optional[SupervisorValidation] = None


# ---------------------------------------------------------------------------
# Healing Agent
# ---------------------------------------------------------------------------


class HealingAgent(BaseAgent):
    """
    Healing Agent Core responsible for coordinating autonomous recovery
    when task execution failures occur.

    Integrates with ErrorParser to convert raw failures into normalized error
    models across Worker, Tool, Supervisor, Permission, Filesystem, Network,
    Browser, PowerShell, and System layers.

    Acts as the central coordinator for failure analysis, root cause
    classification, recovery strategy selection, task generation, and state updates.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        error_parser: Optional[ErrorParser] = None,
        max_healing_attempts: int = 3,
    ) -> None:
        self.event_bus = event_bus
        self.error_parser = error_parser or ErrorParser()
        self.max_healing_attempts = max_healing_attempts
        self.current_state: HealingState = HealingState.IDLE

    @property
    def registration(self) -> AgentRegistration:
        """Returns registration metadata for the Healing Agent."""
        return AgentRegistration(
            name="HealingAgent",
            version="1.0.0",
            description=(
                "Coordinates autonomous failure analysis, root cause classification, "
                "recovery strategy formulation, and state tracking."
            ),
        )

    async def initialize(self) -> None:
        """Lifecycle hook: Called when agent is registered with kernel."""
        logger.info("HealingAgent initialized.")
        if self.event_bus:
            self.event_bus.subscribe(EventType.TASK_FAILED, self.handle_failure_event)

    async def shutdown(self) -> None:
        """Lifecycle hook: Called when the runtime kernel shuts down."""
        logger.info("HealingAgent shut down.")
        if self.event_bus:
            self.event_bus.unsubscribe(EventType.TASK_FAILED, self.handle_failure_event)

    async def handle_failure_event(self, event: ModelEvent) -> None:
        """Async event listener for failure events on EventBus."""
        logger.info(f"HealingAgent received failure event: {event.event_type}")

    async def _emit_event(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        workflow_id: UUID,
        task_id: Optional[UUID] = None,
    ) -> None:
        """Publishes a healing lifecycle event on the EventBus."""
        if self.event_bus:
            event = ModelEvent(
                event_type=event_type,
                source_component="HealingAgent",
                workflow_id=str(workflow_id),
                task_id=str(task_id) if task_id else None,
                payload=payload,
            )
            await self.event_bus.publish(event)

    def _normalize_request(self, request: Any) -> HealingRequest:
        """Standardizes input payloads into a uniform HealingRequest."""
        if isinstance(request, HealingRequest):
            return request

        if isinstance(request, TaskFailureReport):
            return HealingRequest(
                workflow_id=request.workflow_id,
                task_id=request.task_id,
                failure_report=request,
                error_message=request.message,
                execution_context=request.execution_context,
            )

        if isinstance(request, ExecutionResult):
            error_msg = (
                request.error.error_message if request.error else "Execution failed"
            )
            return HealingRequest(
                workflow_id=request.workflow_id,
                task_id=request.task_id,
                execution_result=request,
                error_message=error_msg,
                execution_context={"output": request.output, "logs": request.logs},
            )

        if isinstance(request, SupervisorValidation):
            error_msg = (
                "; ".join(request.issues) if request.issues else "Validation failed"
            )
            return HealingRequest(
                workflow_id=request.workflow_id,
                task_id=request.task_id,
                validation=request,
                error_message=error_msg,
                execution_context={"checks": request.checks, "issues": request.issues},
            )

        if isinstance(request, dict):
            workflow_id_raw = request.get("workflow_id")
            task_id_raw = request.get("task_id")
            if not workflow_id_raw or not task_id_raw:
                raise ValidationException(
                    "Healing request payload missing required workflow_id or task_id",
                    code="INVALID_HEALING_REQUEST",
                )
            try:
                wf_id = UUID(str(workflow_id_raw))
                t_id = UUID(str(task_id_raw))
            except ValueError as ve:
                raise ValidationException(
                    f"Invalid UUID format in healing request: {ve}",
                    code="INVALID_HEALING_REQUEST",
                )

            return HealingRequest(
                workflow_id=wf_id,
                task_id=t_id,
                error_message=request.get("error_message") or request.get("message"),
                attempt_number=int(request.get("attempt_number", 1)),
                execution_context=request.get("execution_context", {}),
            )

        raise ValidationException(
            f"Unsupported healing request payload type: {type(request)}",
            code="INVALID_HEALING_REQUEST",
        )

    def _analyze_root_cause(
        self,
        request: HealingRequest,
        task: Optional[Task] = None,  # noqa: ARG002
    ) -> RootCauseCategory:
        """Determines the root cause category of an execution failure."""
        err_msg = (request.error_message or "").lower()
        err_code = ""
        if request.execution_result and request.execution_result.error:
            err_code = (request.execution_result.error.error_code or "").lower()

        if request.failure_report:
            ft = request.failure_report.failure_type
            if ft == FailureType.PERMISSION_DENIED:
                return RootCauseCategory.PERMISSION_DENIED
            if ft == FailureType.TIMEOUT:
                return RootCauseCategory.TIMEOUT
            if ft in (FailureType.TOOL_UNAVAILABLE, FailureType.TOOL_ERROR):
                return RootCauseCategory.TOOL_FAILURE
            if ft in (FailureType.WORKFLOW_BLOCKED, FailureType.DEPENDENCY_FAILED):
                return RootCauseCategory.WORKFLOW_ERROR

        if (
            "permission" in err_msg
            or "access denied" in err_msg
            or "permission" in err_code
        ):
            return RootCauseCategory.PERMISSION_DENIED
        if "user rejected" in err_msg or "user denied" in err_msg:
            return RootCauseCategory.USER_REJECTED
        if "timeout" in err_msg or "timed out" in err_msg or "timeout" in err_code:
            return RootCauseCategory.TIMEOUT
        if (
            "network" in err_msg
            or "connection" in err_msg
            or "dns" in err_msg
            or "network" in err_code
        ):
            return RootCauseCategory.NETWORK_ERROR
        if "tool" in err_msg or "command not found" in err_msg or "tool" in err_code:
            return RootCauseCategory.TOOL_FAILURE
        if (
            "api" in err_msg
            or "rate limit" in err_msg
            or "429" in err_msg
            or "api" in err_code
        ):
            return RootCauseCategory.EXTERNAL_API
        if "workflow" in err_msg or "dependency" in err_msg or "workflow" in err_code:
            return RootCauseCategory.WORKFLOW_ERROR

        return RootCauseCategory.RUNTIME_ERROR

    def _formulate_recovery_strategy(
        self,
        root_cause: RootCauseCategory,
        request: HealingRequest,
        attempt_number: int,
    ) -> tuple[RecoveryStrategyType, bool, Optional[str]]:
        """Formulates recovery strategy based on root cause and attempt count.

        Returns:
            tuple: (strategy_type, is_recoverable, escalation_reason)
        """
        if attempt_number > self.max_healing_attempts:
            reason = f"Exceeded maximum healing attempts ({self.max_healing_attempts})"
            return RecoveryStrategyType.ESCALATE, False, reason

        if request.failure_report and not request.failure_report.retryability:
            reason = (
                f"Failure is explicitly non-retryable: {request.failure_report.message}"
            )
            return RecoveryStrategyType.ESCALATE, False, reason

        if request.execution_result and request.execution_result.error:
            if not request.execution_result.error.is_recoverable:
                reason = (
                    "Error explicitly flagged non-recoverable: "
                    f"{request.execution_result.error.error_message}"
                )
                return RecoveryStrategyType.ESCALATE, False, reason

        if root_cause in (
            RootCauseCategory.PERMISSION_DENIED,
            RootCauseCategory.USER_REJECTED,
            RootCauseCategory.WORKFLOW_ERROR,
        ):
            reason = (
                f"Root cause '{root_cause.value}' requires escalation "
                "or user intervention"
            )
            return RecoveryStrategyType.ESCALATE, False, reason

        if root_cause in (
            RootCauseCategory.TIMEOUT,
            RootCauseCategory.NETWORK_ERROR,
            RootCauseCategory.RUNTIME_ERROR,
        ):
            return RecoveryStrategyType.RETRY, True, None

        if root_cause == RootCauseCategory.TOOL_FAILURE:
            return RecoveryStrategyType.RESTART_TOOL, True, None

        if root_cause == RootCauseCategory.EXTERNAL_API:
            return RecoveryStrategyType.WAIT, True, None

        return RecoveryStrategyType.RETRY, True, None

    def _generate_replacement_tasks(
        self,
        strategy: RecoveryStrategyType,
        task: Optional[Task],
        attempt_number: int,
    ) -> List[Task]:
        """Generates replacement tasks if applicable for the strategy."""
        if not task or strategy not in (
            RecoveryStrategyType.RETRY,
            RecoveryStrategyType.RESTART_TOOL,
            RecoveryStrategyType.ALTERNATIVE_TOOL,
        ):
            return []

        replacement = task.model_copy(
            update={
                "status": TaskStatus.WAITING,
                "retry_count": attempt_number,
                "execution_logs": list(task.execution_logs)
                + [f"Healing recovery attempt #{attempt_number}"],
            }
        )
        return [replacement]

    async def execute(
        self,
        request: Any,
        state: Optional[SharedWorkflowState] = None,
        **kwargs: Any,
    ) -> HealingResult:
        """
        Main execution entrypoint for Healing Agent.

        Performs request validation, failure analysis, root cause determination,
        strategy selection, event publishing, and state management.
        """
        self.current_state = HealingState.ANALYZING

        # 1. Standardize / Validate Request
        try:
            norm_req = self._normalize_request(request)
        except ValidationException as ve:
            self.current_state = HealingState.FAILED
            logger.error(f"Healing request validation failed: {ve.message}")
            raise

        logger.info(
            "HealingAgent beginning recovery analysis for workflow "
            f"{norm_req.workflow_id}, task {norm_req.task_id}"
        )

        await self._emit_event(
            EventType.HEALING_STARTED,
            {
                "task_id": str(norm_req.task_id),
                "attempt_number": norm_req.attempt_number,
                "status": "STARTED",
            },
            norm_req.workflow_id,
            norm_req.task_id,
        )

        # 2. Check SWS Context & Validate Workflow/Task
        target_task: Optional[Task] = None
        attempt_number = norm_req.attempt_number

        if state is not None:
            if state.metadata.workflow_id != norm_req.workflow_id:
                self.current_state = HealingState.ESCALATED
                escalation_reason = (
                    f"Unknown workflow ID: {norm_req.workflow_id} "
                    f"(expected {state.metadata.workflow_id})"
                )
                logger.warning(escalation_reason)
                result = HealingResult(
                    task_id=norm_req.task_id,
                    workflow_id=norm_req.workflow_id,
                    root_cause=RootCauseCategory.WORKFLOW_ERROR.value,
                    recovery_strategy=RecoveryStrategyType.ESCALATE.value,
                    attempt_number=attempt_number,
                    success=False,
                )
                state.healing_history.append(result)
                await self._emit_event(
                    EventType.HEALING_FAILED,
                    {"task_id": str(norm_req.task_id), "reason": escalation_reason},
                    norm_req.workflow_id,
                    norm_req.task_id,
                )
                return result

            target_task = state.tasks.get(norm_req.task_id)
            if not target_task:
                self.current_state = HealingState.ESCALATED
                escalation_reason = f"Unknown task ID: {norm_req.task_id}"
                logger.warning(escalation_reason)
                result = HealingResult(
                    task_id=norm_req.task_id,
                    workflow_id=norm_req.workflow_id,
                    root_cause=RootCauseCategory.WORKFLOW_ERROR.value,
                    recovery_strategy=RecoveryStrategyType.ESCALATE.value,
                    attempt_number=attempt_number,
                    success=False,
                )
                state.healing_history.append(result)
                await self._emit_event(
                    EventType.HEALING_FAILED,
                    {"task_id": str(norm_req.task_id), "reason": escalation_reason},
                    norm_req.workflow_id,
                    norm_req.task_id,
                )
                return result

            target_task.status = TaskStatus.HEALING
            attempt_number = target_task.retry_count + 1

        # 3. Analyze Root Cause & Formulate Strategy
        self.current_state = HealingState.PLANNING
        root_cause = self._analyze_root_cause(norm_req, target_task)
        strategy, is_success, escalation_reason = self._formulate_recovery_strategy(
            root_cause, norm_req, attempt_number
        )

        # 4. Generate Recovery Tasks
        self.current_state = HealingState.GENERATING_TASKS
        replacement_tasks = self._generate_replacement_tasks(
            strategy, target_task, attempt_number
        )

        self.current_state = (
            HealingState.COMPLETED if is_success else HealingState.ESCALATED
        )

        result = HealingResult(
            task_id=norm_req.task_id,
            workflow_id=norm_req.workflow_id,
            root_cause=root_cause.value,
            recovery_strategy=strategy.value,
            replacement_tasks=replacement_tasks,
            attempt_number=attempt_number,
            success=is_success,
        )

        # 5. Update State & Emit Completion/Failure Event
        if state is not None:
            state.healing_history.append(result)
            if target_task:
                if is_success:
                    target_task.status = TaskStatus.WAITING
                    target_task.retry_count = attempt_number
                else:
                    target_task.status = TaskStatus.FAILED

        if is_success:
            logger.info(
                "HealingAgent successfully created recovery plan for task "
                f"{norm_req.task_id}: strategy={strategy.value}, "
                f"root_cause={root_cause.value}"
            )
            await self._emit_event(
                EventType.HEALING_COMPLETED,
                {
                    "task_id": str(norm_req.task_id),
                    "success": True,
                    "root_cause": root_cause.value,
                    "strategy": strategy.value,
                    "replacement_tasks_count": len(replacement_tasks),
                },
                norm_req.workflow_id,
                norm_req.task_id,
            )
        else:
            logger.warning(
                f"HealingAgent recovery escalated for task {norm_req.task_id}: "
                f"reason={escalation_reason}"
            )
            await self._emit_event(
                EventType.HEALING_FAILED,
                {
                    "task_id": str(norm_req.task_id),
                    "success": False,
                    "reason": escalation_reason,
                    "root_cause": root_cause.value,
                },
                norm_req.workflow_id,
                norm_req.task_id,
            )

        return result


__all__ = [
    "HealingAgent",
    "HealingRequest",
    "HealingState",
    "RootCauseCategory",
    "RecoveryStrategyType",
]
