from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import UUID

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionResult,
    HealingResult,
    TaskFailureReport,
)
from shared.contracts.task import Task
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.error_parser import ErrorParser, ParsedError
from app.agents.healing.recovery_planner import RecoveryPlan, RecoveryPlanner
from app.agents.healing.retry_engine import RetryEngine
from app.agents.healing.root_cause_analyzer import (
    RootCauseAnalysis,
    RootCauseAnalyzer,
)
from app.core.events.bus import EventBus
from app.core.logging import get_logger
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
        max_retries: int = 3,
        max_healing_attempts: int = 5,
    ) -> None:
        self.event_bus = event_bus
        self.error_parser = error_parser or ErrorParser()
        self.root_cause_analyzer = root_cause_analyzer or RootCauseAnalyzer()
        self.recovery_planner = recovery_planner or RecoveryPlanner()
        self.retry_engine = retry_engine or RetryEngine(
            default_max_retries=max_retries,
            default_max_healing_attempts=max_healing_attempts,
        )
        self.max_retries = max_retries
        self.max_healing_attempts = max_healing_attempts
        self.current_state: HealingState = HealingState.IDLE

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

        self.current_state = HealingState.ANALYZING
        await self._emit_healing_event(
            EventType.HEALING_STARTED,
            workflow_id=workflow_id,
            task_id=task_id,
            payload={
                "task_name": task.task_name,
                "attempt_number": attempt_number,
                "state": self.current_state.value,
            },
        )

        parsed_error: ParsedError = self.error_parser.parse(failure_input, task=task)
        logger.info(
            f"Step 1/4 - Error Parser normalized failure: "
            f"code={parsed_error.normalized_code}, "
            f"category={parsed_error.category.value}"
        )

        self.current_state = HealingState.PLANNING

        root_cause: RootCauseAnalysis = self.root_cause_analyzer.analyze(
            parsed_error=parsed_error,
            task=task,
            state=state,
        )
        logger.info(
            f"Step 2/4 - Root Cause Analyzer result: "
            f"category={root_cause.category.value}, "
            f"recoverable={root_cause.is_recoverable}"
        )

        plan: RecoveryPlan = self.recovery_planner.plan(
            root_cause=root_cause,
            task=task,
            state=state,
            max_healing_attempts=self.max_healing_attempts,
        )
        logger.info(
            f"Step 3/4 - Recovery Planner strategy: "
            f"{plan.strategy.value}, executable={plan.is_executable}"
        )

        if plan.replacement_tasks:
            self.current_state = HealingState.GENERATING_TASKS
        else:
            self.current_state = HealingState.RETRYING

        can_retry, reason = self.retry_engine.can_retry(
            task=task,
            state=state,
            root_cause=root_cause,
            max_retries=self.max_retries,
            max_healing_attempts=self.max_healing_attempts,
        )

        if not can_retry:
            logger.warning(
                f"RetryEngine blocked recovery attempt for task {task_id}: {reason}"
            )
            self.current_state = (
                HealingState.EXHAUSTED
                if "limit" in reason.lower()
                else HealingState.FAILED
            )
            result = HealingResult(
                task_id=task_id,
                workflow_id=workflow_id,
                root_cause=root_cause.category.value,
                recovery_strategy=plan.strategy.value,
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
                    "root_cause": root_cause.category.value,
                },
            )
            return result

        result = await self.retry_engine.execute_recovery(
            plan=plan,
            task=task,
            state=state,
            root_cause=root_cause,
            attempt_number=attempt_number,
        )

        state.healing_history.append(result)

        if result.success:
            self.current_state = HealingState.COMPLETED
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
            self.current_state = HealingState.FAILED
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

        return result
