from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union
from uuid import UUID

from shared.contracts.escalation import (
    EscalationReason,
    EscalationRequest,
)
from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionResult,
    HealingResult,
    TaskFailureReport,
)
from shared.contracts.task import Task
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.error_parser import ErrorParser, ParsedError
from app.agents.healing.escalation import EscalationHandler
from app.agents.healing.recovery_planner import RecoveryPlan, RecoveryPlanner
from app.agents.healing.retry_engine import RetryEngine
from app.agents.healing.root_cause_analyzer import (
    RootCauseAnalysis,
    RootCauseAnalyzer,
)
from app.agents.healing.validator import validate_recovery_plan
from app.core.events.bus import EventBus
from app.core.logging import get_logger
from app.core.permissions.models import ExecutionMode
from app.core.permissions.policies import evaluate_task_risk_and_permissions
from app.core.tracing import record_trace
from app.runtime.interfaces import AgentRegistration, BaseAgent

logger = get_logger(__name__)


class HealingState(str, Enum):
    """Lifecycle states of the Self-Healing Loop state machine."""

    IDLE = "IDLE"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    GENERATING_TASKS = "GENERATING_TASKS"
    RETRYING = "RETRYING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    EXHAUSTED = "EXHAUSTED"


class SelfHealingLoop(BaseAgent):
    """Central Self-Healing Loop coordinator for failure recovery."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        error_parser: Optional[ErrorParser] = None,
        root_cause_analyzer: Optional[RootCauseAnalyzer] = None,
        recovery_planner: Optional[RecoveryPlanner] = None,
        retry_engine: Optional[RetryEngine] = None,
        escalation_handler: Optional[EscalationHandler] = None,
        max_retries: int = 3,
        max_healing_attempts: int = 5,
        permission_manager: Optional[Any] = None,
        tool_registry: Optional[Any] = None,
    ) -> None:
        self.event_bus = event_bus
        self.permission_manager = permission_manager
        self.tool_registry = tool_registry
        self.error_parser = error_parser or ErrorParser()
        self.root_cause_analyzer = root_cause_analyzer or RootCauseAnalyzer()
        self.recovery_planner = recovery_planner or RecoveryPlanner(tool_registry=tool_registry)
        if self.recovery_planner and getattr(self.recovery_planner, "tool_registry", None) is None:
            self.recovery_planner.tool_registry = tool_registry
        self.retry_engine = retry_engine or RetryEngine(
            default_max_retries=max_retries,
            default_max_healing_attempts=max_healing_attempts,
            permission_manager=permission_manager,
        )
        self.escalation_handler = escalation_handler or EscalationHandler(
            event_bus=event_bus
        )
        self.max_retries = max_retries
        self.max_healing_attempts = max_healing_attempts
        self._default_state: HealingState = HealingState.IDLE
        self._task_states: Dict[Tuple[UUID, UUID], HealingState] = {}

    @property
    def current_state(self) -> HealingState:
        """Backward-compatible property returning the global/most recent healing state."""
        return self._default_state

    @current_state.setter
    def current_state(self, state: HealingState) -> None:
        self._default_state = state

    def get_task_state(
        self, workflow_id: Optional[UUID] = None, task_id: Optional[UUID] = None
    ) -> HealingState:
        """Returns the isolated lifecycle state for a specific task failure."""
        if workflow_id is not None and task_id is not None:
            return self._task_states.get((workflow_id, task_id), self._default_state)
        return self._default_state

    def _set_task_state(
        self, workflow_id: UUID, task_id: UUID, state: HealingState
    ) -> None:
        """Sets the isolated lifecycle state for a specific task failure."""
        self._task_states[(workflow_id, task_id)] = state
        self._default_state = state

    @property
    def registration(self) -> AgentRegistration:
        """Returns registration metadata for the Healing Agent."""
        return AgentRegistration(
            name="HealingAgent",
            version="1.0.0",
            description=(
                "Orchestrates autonomous workflow failure diagnosis, "
                "root cause classification, recovery planning, and retries."
            ),
        )

    async def initialize(self) -> None:
        """Lifecycle hook: Called when the agent is registered."""
        logger.info("HealingAgent / SelfHealingLoop initialized.")
        self.current_state = HealingState.IDLE

    async def shutdown(self) -> None:
        """Lifecycle hook: Called when the kernel shuts down."""
        logger.info("HealingAgent / SelfHealingLoop shut down.")
        self.current_state = HealingState.IDLE

    async def _emit_healing_event(
        self,
        event_type: EventType,
        workflow_id: UUID,
        task_id: Optional[UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Helper to publish event bus lifecycle notifications."""
        if self.event_bus:
            event = RuntimeEvent(
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type,
                source_component=EventSource.HEALING,
                payload=payload or {},
            )
            await self.event_bus.publish(event)

    async def execute(
        self,
        task: Task,
        *args: Any,
        **kwargs: Any,
    ) -> HealingResult:
        """BaseAgent interface entry point. Resolves args and delegates."""
        failure_input = None
        state = None

        if args:
            failure_input = args[0]
            if len(args) > 1:
                state = args[1]
        if not failure_input and "failure_input" in kwargs:
            failure_input = kwargs["failure_input"]
        if not failure_input and "result" in kwargs:
            failure_input = kwargs["result"]
        if not state and "state" in kwargs:
            state = kwargs["state"]

        if not state:
            raise ValueError("SharedWorkflowState is required for SelfHealingLoop.")

        return await self.process_failure(
            task, failure_input or "Unknown Failure", state
        )

    async def process_failure(
        self,
        task: Task,
        failure_input: Union[
            TaskFailureReport, ExecutionResult, Exception, str, Dict[str, Any]
        ],
        state: SharedWorkflowState,
    ) -> HealingResult:
        """Coordinates autonomous recovery pipeline after a task failure."""
        workflow_id = task.workflow_id
        task_id = task.task_id

        attempt_number = (
            sum(1 for h in state.healing_history if h.task_id == task_id) + 1
        )

        logger.info(
            f"SelfHealingLoop starting recovery lifecycle for task {task_id} "
            f"(Workflow: {workflow_id}, Attempt #{attempt_number})"
        )

        record_trace(
            "failure_detected",
            workflow_id=workflow_id,
            task_id=task_id,
            attempt=attempt_number,
            extra={"error_text": str(failure_input), "retry_count_k": task.retry_count},
        )

        self._set_task_state(workflow_id, task_id, HealingState.ANALYZING)
        await self._emit_healing_event(
            EventType.HEALING_STARTED,
            workflow_id=workflow_id,
            task_id=task_id,
            payload={
                "task_name": task.task_name,
                "attempt_number": attempt_number,
                "state": self.get_task_state(workflow_id, task_id).value,
            },
        )

        # Stage 1: Error Parsing
        record_trace("stage1_error_parsing_start", workflow_id=workflow_id, task_id=task_id, attempt=attempt_number)
        parsed_error: ParsedError = self.error_parser.parse(failure_input, task=task)
        record_trace(
            "stage1_error_parsing_end",
            workflow_id=workflow_id,
            task_id=task_id,
            attempt=attempt_number,
            fault_class=parsed_error.category.value if hasattr(parsed_error.category, "value") else str(parsed_error.category),
            extra={
                "error_text": parsed_error.raw_message or str(failure_input),
                "parsed_category": parsed_error.category.value if hasattr(parsed_error.category, "value") else str(parsed_error.category),
                "normalized_code": parsed_error.normalized_code,
            },
        )
        logger.info(
            f"Step 1/4 - Error Parser normalized failure: "
            f"code={parsed_error.normalized_code}, "
            f"category={parsed_error.category.value}"
        )

        self._set_task_state(workflow_id, task_id, HealingState.PLANNING)

        # Stage 2: Root Cause Analysis
        record_trace("stage2_root_cause_analysis_start", workflow_id=workflow_id, task_id=task_id, attempt=attempt_number)
        root_cause: RootCauseAnalysis = self.root_cause_analyzer.analyze(
            parsed_error=parsed_error,
            task=task,
            state=state,
        )
        record_trace(
            "stage2_root_cause_analysis_end",
            workflow_id=workflow_id,
            task_id=task_id,
            attempt=attempt_number,
            fault_class=root_cause.category.value if hasattr(root_cause.category, "value") else str(root_cause.category),
            extra={
                "confidence": root_cause.confidence_score,
                "root_cause_category": root_cause.category.value if hasattr(root_cause.category, "value") else str(root_cause.category),
                "root_cause_summary": root_cause.root_cause_summary,
            },
        )
        logger.info(
            f"Step 2/4 - Root Cause Analyzer result: "
            f"category={root_cause.category.value}, "
            f"recoverable={root_cause.is_recoverable}"
        )

        exec_mode = (
            getattr(getattr(state, "metadata", None), "execution_mode", None)
            or getattr(self.permission_manager, "mode", None)
            or ExecutionMode.SAFE
        )
        orig_risk, orig_perms, _, _ = evaluate_task_risk_and_permissions(
            task, mode=exec_mode
        )
        baseline = (orig_risk, orig_perms)

        # Stage 3: Strategy Selection / Planning
        record_trace("stage3_strategy_selection_start", workflow_id=workflow_id, task_id=task_id, attempt=attempt_number)
        plan: RecoveryPlan = self.recovery_planner.plan(
            root_cause=root_cause,
            task=task,
            state=state,
            max_healing_attempts=self.max_healing_attempts,
            mode=exec_mode,
            tool_registry=self.tool_registry,
        )
        plan_strat_str = plan.strategy.value if hasattr(plan.strategy, "value") else str(plan.strategy)
        record_trace(
            "stage3_strategy_selection_end",
            workflow_id=workflow_id,
            task_id=task_id,
            attempt=attempt_number,
            extra={
                "plan_chosen": plan_strat_str,
                "patch_applied": getattr(plan, "updated_task_params", {}) or {},
                "is_viable": plan.is_viable,
            },
        )
        logger.info(
            f"Step 3/4 - Recovery Planner strategy: "
            f"{plan.strategy.value}, executable={plan.is_executable}"
        )

        can_retry, reason = self.retry_engine.can_retry(
            task=task,
            state=state,
            root_cause=root_cause,
            max_retries=self.max_retries,
            max_healing_attempts=self.max_healing_attempts,
            recovery_plan=plan,
        )

        if not can_retry:
            logger.warning(
                f"RetryEngine blocked recovery attempt for task {task_id}: {reason}"
            )
            if hasattr(plan, "replacement_tasks"):
                plan.replacement_tasks = []
            st = (
                HealingState.EXHAUSTED
                if "limit" in reason.lower()
                else HealingState.FAILED
            )
            self._set_task_state(workflow_id, task_id, st)
            rc_cat = (
                root_cause.category.value
                if hasattr(root_cause.category, "value")
                else str(root_cause.category)
            )
            strat_val = (
                plan.strategy.value
                if hasattr(plan.strategy, "value")
                else str(plan.strategy)
            )
            record_trace(
                "stage3_retry_check_blocked",
                workflow_id=workflow_id,
                task_id=task_id,
                attempt=attempt_number,
                fault_class=rc_cat,
                extra={
                    "supervisor_result": f"BLOCKED: {reason}",
                    "final_status": st.value if hasattr(st, "value") else str(st),
                    "retry_count_k": task.retry_count,
                    "plan_chosen": strat_val,
                    "patch_applied": getattr(plan, "updated_task_params", {}) or {},
                },
            )
            result = HealingResult(
                task_id=task_id,
                workflow_id=workflow_id,
                root_cause=rc_cat,
                recovery_strategy=strat_val,
                replacement_tasks=[],
                attempt_number=attempt_number,
                success=False,
            )
            state.healing_history.append(result)

            await self._emit_healing_event(
                EventType.HEALING_FAILED,
                workflow_id=workflow_id,
                task_id=task_id,
                payload={
                    "reason": reason,
                    "attempt_number": attempt_number,
                    "root_cause": rc_cat,
                },
            )

            # Invoke EscalationHandler for unrecoverable/exhausted failure
            try:
                esc_reason = (
                    EscalationReason.MAX_RETRIES_EXCEEDED
                    if ("limit" in reason.lower() or "exceeded" in reason.lower())
                    else EscalationReason.UNSUPPORTED_ERROR
                )
                if (
                    "permission" in parsed_error.normalized_code.lower()
                    or "permission" in rc_cat.lower()
                ):
                    esc_reason = EscalationReason.PERMISSION_DENIED

                esc_req = EscalationRequest(
                    workflow_id=workflow_id,
                    task_id=task_id,
                    reason=esc_reason,
                    details=f"SelfHealing blocked/exhausted: {reason}",
                    failure_context={
                        "error_code": parsed_error.normalized_code,
                        "error_message": parsed_error.raw_message,
                        "root_cause": rc_cat,
                        "reason": reason,
                    },
                    healing_history=list(state.healing_history),
                    attempt_number=attempt_number,
                    risk_level=getattr(task, "risk_level", None),
                )
                await self.escalation_handler.handle_escalation(esc_req, sws=state)
            except Exception as esc_err:
                logger.warning(f"Error invoking EscalationHandler: {esc_err}")

            return result

        # Stage 4: Plan Validation
        record_trace("stage4_plan_validation_start", workflow_id=workflow_id, task_id=task_id, attempt=attempt_number)
        is_plan_valid, val_errors = validate_recovery_plan(
            plan,
            original_task=task,
            mode=exec_mode,
            original_baseline=baseline,
        )
        record_trace("stage4_plan_validation_end", workflow_id=workflow_id, task_id=task_id, attempt=attempt_number)
        if not is_plan_valid or not plan.is_viable:
            sec_reason = (
                "; ".join(val_errors)
                if val_errors
                else (
                    "; ".join(getattr(plan, "validation_errors", []) or [])
                    or "Recovery plan marked non-viable"
                )
            )
            logger.warning(
                f"SelfHealingLoop blocked unsafe or non-viable recovery plan for task {task_id}: {sec_reason}"
            )
            plan.is_viable = False
            plan.replacement_tasks = []
            self._set_task_state(workflow_id, task_id, HealingState.ESCALATED)
            rc_cat = (
                root_cause.category.value
                if hasattr(root_cause.category, "value")
                else str(root_cause.category)
            )
            strat_val = (
                plan.strategy.value
                if hasattr(plan.strategy, "value")
                else str(plan.strategy)
            )
            record_trace(
                "stage4_plan_validation_rejected",
                workflow_id=workflow_id,
                task_id=task_id,
                attempt=attempt_number,
                fault_class=rc_cat,
                extra={
                    "supervisor_result": f"REJECTED: {sec_reason}",
                    "final_status": HealingState.ESCALATED.value,
                    "retry_count_k": task.retry_count,
                    "plan_chosen": strat_val,
                    "patch_applied": getattr(plan, "updated_task_params", {}) or {},
                },
            )
            result = HealingResult(
                task_id=task_id,
                workflow_id=workflow_id,
                root_cause=rc_cat,
                recovery_strategy=strat_val,
                replacement_tasks=[],
                attempt_number=attempt_number,
                success=False,
            )
            state.healing_history.append(result)
            await self._emit_healing_event(
                EventType.HEALING_FAILED,
                workflow_id=workflow_id,
                task_id=task_id,
                payload={
                    "reason": sec_reason,
                    "attempt_number": attempt_number,
                    "root_cause": rc_cat,
                    "security_violation": True,
                },
            )
            try:
                esc_req = EscalationRequest(
                    workflow_id=workflow_id,
                    task_id=task_id,
                    reason=EscalationReason.PERMISSION_DENIED,
                    details=f"SelfHealing blocked unsafe recovery plan: {sec_reason}",
                    failure_context={
                        "error_code": parsed_error.normalized_code,
                        "error_message": parsed_error.raw_message,
                        "root_cause": rc_cat,
                        "reason": sec_reason,
                    },
                    healing_history=list(state.healing_history),
                    attempt_number=attempt_number,
                    risk_level=getattr(task, "risk_level", None),
                )
                await self.escalation_handler.handle_escalation(esc_req, sws=state)
            except Exception as esc_err:
                logger.warning(f"Error invoking EscalationHandler: {esc_err}")
            return result

        if plan.replacement_tasks:
            self._set_task_state(workflow_id, task_id, HealingState.GENERATING_TASKS)
        else:
            self._set_task_state(workflow_id, task_id, HealingState.RETRYING)

        # Stage 5: Recovery Execution
        record_trace("stage5_recovery_execution_start", workflow_id=workflow_id, task_id=task_id, attempt=attempt_number)
        result = await self.retry_engine.execute_recovery(
            plan=plan,
            task=task,
            state=state,
            root_cause=root_cause,
            attempt_number=attempt_number,
        )
        record_trace(
            "stage5_recovery_execution_end",
            workflow_id=workflow_id,
            task_id=task_id,
            attempt=attempt_number,
            fault_class=root_cause.category.value if hasattr(root_cause.category, "value") else str(root_cause.category),
            extra={
                "supervisor_result": "PASSED: recovery executed successfully" if result.success else "FAILED: retry engine execution failed",
                "final_status": HealingState.COMPLETED.value if result.success else HealingState.FAILED.value,
                "retry_count_k": task.retry_count,
                "plan_chosen": plan.strategy.value if hasattr(plan.strategy, "value") else str(plan.strategy),
                "patch_applied": getattr(plan, "updated_task_params", {}) or {},
            },
        )

        state.healing_history.append(result)

        if result.success:
            self._set_task_state(workflow_id, task_id, HealingState.COMPLETED)
            logger.info(f"SelfHealingLoop successfully recovered task {task_id}.")
            await self._emit_healing_event(
                EventType.HEALING_COMPLETED,
                workflow_id=workflow_id,
                task_id=task_id,
                payload={
                    "recovery_strategy": plan.strategy.value,
                    "attempt_number": attempt_number,
                    "replacement_tasks_count": len(plan.replacement_tasks),
                },
            )
        else:
            self._set_task_state(workflow_id, task_id, HealingState.FAILED)
            logger.error(f"SelfHealingLoop recovery failed for task {task_id}.")
            await self._emit_healing_event(
                EventType.HEALING_FAILED,
                workflow_id=workflow_id,
                task_id=task_id,
                payload={
                    "recovery_strategy": plan.strategy.value,
                    "attempt_number": attempt_number,
                    "reason": "Retry Engine execution failed",
                },
            )

            # Invoke EscalationHandler when recovery execution fails
            try:
                esc_req = EscalationRequest(
                    workflow_id=workflow_id,
                    task_id=task_id,
                    reason=EscalationReason.MAX_HEALING_ATTEMPTS_EXCEEDED,
                    details=(
                        f"SelfHealingLoop recovery execution failed for task {task_id}"
                    ),
                    failure_context={
                        "task_id": str(task_id),
                        "attempt_number": attempt_number,
                    },
                    healing_history=list(state.healing_history),
                    attempt_number=attempt_number,
                )
                await self.escalation_handler.handle_escalation(esc_req, sws=state)
            except Exception as esc_err:
                logger.warning(
                    f"Error invoking EscalationHandler on failed recovery: {esc_err}"
                )

        return result
