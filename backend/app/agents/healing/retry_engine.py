import logging
from typing import Dict, Optional, Tuple

from shared.contracts.execution import HealingResult
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.recovery_planner import RecoveryPlan, RecoveryStrategy
from app.agents.healing.root_cause_analyzer import RootCauseAnalysis
from app.engine.workflow import WorkflowEngine

logger = logging.getLogger(__name__)


class RetryEngine:
    """Retry Engine component responsible for evaluating recovery permission."""

    def __init__(
        self,
        default_max_retries: int = 3,
        default_max_healing_attempts: int = 5,
    ) -> None:
        self.default_max_retries = default_max_retries
        self.default_max_healing_attempts = default_max_healing_attempts
        # Tracking failure signatures: (task_id, root_cause_category, code) -> count
        self._failure_signature_counts: Dict[Tuple[str, str, str], int] = {}

    def can_retry(
        self,
        task: Task,
        state: SharedWorkflowState,
        root_cause: RootCauseAnalysis,
        max_retries: Optional[int] = None,
        max_healing_attempts: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Determines whether a retry or healing attempt is allowed."""
        limit_retries = (
            max_retries if max_retries is not None else self.default_max_retries
        )
        limit_healing = (
            max_healing_attempts
            if max_healing_attempts is not None
            else self.default_max_healing_attempts
        )

        # 1. Enforce per-task retry limit
        if task.retry_count >= limit_retries:
            msg = f"Task {task.task_id} reached max retry limit of {limit_retries}."
            logger.info(msg)
            return False, msg

        # 2. Enforce total healing attempts limit across workflow state
        healing_attempts_for_task = sum(
            1 for h in state.healing_history if h.task_id == task.task_id
        )
        if healing_attempts_for_task >= limit_healing:
            msg = (
                f"Task {task.task_id} reached max healing attempts limit "
                f"of {limit_healing}."
            )
            logger.info(msg)
            return False, msg

        # 3. Infinite Loop Protection: Check repeat failure signature count
        signature = (
            str(task.task_id),
            root_cause.category.value,
            root_cause.summary,
        )
        current_count = self._failure_signature_counts.get(signature, 0)
        if current_count >= 3:
            msg = (
                f"Infinite loop detected: Task {task.task_id} repeatedly "
                "failed with identical signature."
            )
            logger.warning(msg)
            return False, msg

        # 4. Check root cause recoverability
        if not root_cause.is_recoverable:
            msg = f"Root cause '{root_cause.category.value}' is non-recoverable."
            logger.info(msg)
            return False, msg

        return True, "Retry permitted."

    def execute_recovery(
        self,
        plan: RecoveryPlan,
        task: Task,
        state: SharedWorkflowState,
        root_cause: RootCauseAnalysis,
        attempt_number: int = 1,
    ) -> HealingResult:
        """Executes recovery plan by re-enqueuing task in WorkflowEngine."""
        logger.info(
            f"RetryEngine executing recovery for task {task.task_id} "
            f"using strategy {plan.strategy.value} (Attempt #{attempt_number})"
        )

        sig = (
            str(task.task_id),
            root_cause.category.value,
            root_cause.summary,
        )
        self._failure_signature_counts[sig] = (
            self._failure_signature_counts.get(sig, 0) + 1
        )

        engine = WorkflowEngine(state)

        if not plan.is_executable or plan.strategy in (
            RecoveryStrategy.ESCALATE_USER,
            RecoveryStrategy.CANCEL_WORKFLOW,
            RecoveryStrategy.REQUEST_PERMISSION_AGAIN,
        ):
            logger.info(f"Recovery plan for task {task.task_id} is non-executable.")
            return HealingResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                root_cause=root_cause.category.value,
                recovery_strategy=plan.strategy.value,
                replacement_tasks=plan.replacement_tasks,
                attempt_number=attempt_number,
                success=False,
            )

        try:
            if plan.replacement_tasks:
                logger.info(
                    f"Submitting {len(plan.replacement_tasks)} replacement "
                    "tasks to WorkflowEngine."
                )
                engine.update_task_status(task.task_id, TaskStatus.FAILED)
                for rep_task in plan.replacement_tasks:
                    engine.enqueue(rep_task)
            else:
                task.retry_count += 1
                logger.info(
                    f"Re-enqueueing task {task.task_id} "
                    f"(New retry count: {task.retry_count})"
                )
                if task.task_id in state.failed_tasks:
                    state.failed_tasks.remove(task.task_id)
                engine.enqueue(task)

            return HealingResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                root_cause=root_cause.category.value,
                recovery_strategy=plan.strategy.value,
                replacement_tasks=plan.replacement_tasks,
                attempt_number=attempt_number,
                success=True,
            )

        except Exception as e:
            logger.exception(
                f"RetryEngine failed recovery for task {task.task_id}: {e}"
            )
            return HealingResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                root_cause=root_cause.category.value,
                recovery_strategy=plan.strategy.value,
                replacement_tasks=[],
                attempt_number=attempt_number,
                success=False,
            )
