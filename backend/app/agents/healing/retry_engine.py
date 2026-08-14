import logging
from typing import Any, Dict, Optional, Tuple

from shared.contracts.execution import HealingResult, WorkerReexecutionRequest
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

from app.agents.worker.reexecution import WorkerReexecutionManager
from app.engine.workflow import WorkflowEngine

logger = logging.getLogger(__name__)


class RetryEngine:
    """
    Retry Engine component responsible for evaluating recovery viability,
    enforcing limits, creating WorkerReexecutionRequest contracts, and
    enqueueing re-execution tasks via WorkflowEngine.
    """

    def __init__(
        self,
        default_max_retries: int = 3,
        default_max_healing_attempts: int = 5,
        reexecution_manager: Optional[WorkerReexecutionManager] = None,
    ) -> None:
        self.default_max_retries = default_max_retries
        self.default_max_healing_attempts = default_max_healing_attempts
        self.reexecution_manager = reexecution_manager or WorkerReexecutionManager()
        self._failure_signature_counts: Dict[Tuple[str, str, str], int] = {}

    def can_retry(
        self,
        task: Task,
        state: SharedWorkflowState,
        root_cause_category: str = "UNKNOWN",
        root_cause_summary: str = "Unknown failure",
        is_recoverable: bool = True,
        max_retries: Optional[int] = None,
        max_healing_attempts: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Determines whether a retry or re-execution attempt is allowed."""
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
            root_cause_category,
            root_cause_summary,
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
        if not is_recoverable:
            msg = f"Root cause '{root_cause_category}' is non-recoverable."
            logger.info(msg)
            return False, msg

        return True, "Retry permitted."

    def create_reexecution_request(
        self,
        task: Task,
        recovery_plan: Optional[Any] = None,
        state: Optional[SharedWorkflowState] = None,
    ) -> WorkerReexecutionRequest:
        """
        Delegates to WorkerReexecutionManager to construct an authorized
        WorkerReexecutionRequest contract for an approved recovery plan.
        """
        return self.reexecution_manager.create_reexecution_request(
            task=task,
            recovery_plan=recovery_plan,
            state=state,
        )

    def execute_recovery(
        self,
        plan: Any,
        task: Task,
        state: SharedWorkflowState,
        root_cause_category: str = "RUNTIME",
        attempt_number: int = 1,
    ) -> HealingResult:
        """Executes recovery plan by re-enqueuing task in WorkflowEngine."""
        logger.info(
            f"RetryEngine executing recovery for task {task.task_id} "
            f"(Attempt #{attempt_number})"
        )

        sig = (
            str(task.task_id),
            root_cause_category,
            getattr(plan, "description", "Recovery plan"),
        )
        self._failure_signature_counts[sig] = (
            self._failure_signature_counts.get(sig, 0) + 1
        )

        engine = WorkflowEngine(state)

        is_executable = getattr(plan, "is_executable", True)
        strategy_val = (
            plan.strategy.value
            if hasattr(getattr(plan, "strategy", None), "value")
            else str(getattr(plan, "strategy", "RETRY"))
        )

        if not is_executable or strategy_val in (
            "ESCALATE_USER",
            "CANCEL_WORKFLOW",
            "REQUEST_PERMISSION_AGAIN",
        ):
            logger.info(f"Recovery plan for task {task.task_id} is non-executable.")
            return HealingResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                root_cause=root_cause_category,
                recovery_strategy=strategy_val,
                replacement_tasks=getattr(plan, "replacement_tasks", []),
                attempt_number=attempt_number,
                success=False,
            )

        try:
            replacement_tasks = getattr(plan, "replacement_tasks", [])
            if replacement_tasks:
                logger.info(
                    f"Submitting {len(replacement_tasks)} replacement "
                    "tasks to WorkflowEngine."
                )
                engine.update_task_status(task.task_id, TaskStatus.FAILED)
                for rep_task in replacement_tasks:
                    engine.enqueue(rep_task)
            else:
                # Formulate WorkerReexecutionRequest to preserve attempt history
                self.create_reexecution_request(
                    task=task, recovery_plan=plan, state=state
                )
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
                root_cause=root_cause_category,
                recovery_strategy=strategy_val,
                replacement_tasks=replacement_tasks,
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
                root_cause=root_cause_category,
                recovery_strategy=strategy_val,
                replacement_tasks=[],
                attempt_number=attempt_number,
                success=False,
            )
