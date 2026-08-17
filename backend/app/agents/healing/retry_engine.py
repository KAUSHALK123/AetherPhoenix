import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    HealingResult,
    TaskError,
    WorkerReexecutionRequest,
)
from shared.contracts.permission import PermissionStatus, PermissionType
from shared.contracts.retry import (
    RecoveryPlan,
    RetryRequest,
    RetryResult,
    RetryStatus,
)
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowStatus

from app.agents.worker.reexecution import WorkerReexecutionManager
from app.core.events.bus import EventBus
from app.engine.workflow import WorkflowEngine

logger = logging.getLogger(__name__)


NON_RETRYABLE_ERROR_CODES = {
    "PERMISSION_DENIED",
    "TOOL_NOT_FOUND",
    "TOOL_DISABLED",
    "INVALID_WORKFLOW",
    "UNSUPPORTED_CAPABILITY",
    "INVALID_PERMISSION",
}


TRANSIENT_ERROR_CODES = {
    "TIMEOUT",
    "BROWSER_TIMEOUT",
    "NETWORK_ERROR",
    "TEMPORARY_NETWORK_ERROR",
    "FILE_LOCKED",
    "RETRYABLE_API_FAILURE",
}


class RetryEngine:
    """
    Retry Engine component for Healing Agent.

    Handles:
    - Retry eligibility validation
    - Maximum retry limits
    - Healing-attempt limits
    - Infinite-loop protection
    - Permission validation
    - Recovery-plan validation
    - Exponential backoff
    - Destructive-operation safety
    - Worker re-execution requests
    - Workflow Engine re-enqueueing
    - Healing/retry history
    - Runtime event publishing
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        default_max_retries: int = 3,
        default_max_healing_attempts: int = 5,
        base_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 60.0,
        reexecution_manager: Optional[WorkerReexecutionManager] = None,
    ) -> None:
        self.event_bus = event_bus
        self.default_max_retries = default_max_retries
        self.default_max_healing_attempts = default_max_healing_attempts
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds

        self.reexecution_manager = reexecution_manager or WorkerReexecutionManager()

        # Used to prevent repeatedly attempting the exact same recovery.
        self._failure_signature_counts: Dict[Tuple[str, str, str], int] = {}

    def calculate_backoff_delay(
        self,
        attempt_number: int,
        backoff_override: Optional[float] = None,
    ) -> float:
        """
        Calculates exponential backoff delay.

        Formula:
            min(base_backoff * 2^(attempt - 1), max_backoff)
        """

        if backoff_override is not None and backoff_override > 0:
            return float(backoff_override)

        exponent = max(0, attempt_number - 1)
        delay = self.base_backoff_seconds * (2**exponent)

        return min(delay, self.max_backoff_seconds)

    def can_retry(
        self,
        task: Task,
        state: SharedWorkflowState,
        root_cause_category: str = "UNKNOWN",
        root_cause_summary: str = "Unknown failure",
        is_recoverable: bool = True,
        max_retries: Optional[int] = None,
        max_healing_attempts: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[bool, str]:
        """
        Backward-compatible retry eligibility check.

        This keeps the worker-re-execution feature's healing limits and
        failure-signature loop protection.
        """
        # Backward compatibility for passing root_cause object
        root_cause = kwargs.get("root_cause")
        if root_cause is not None:
            if hasattr(root_cause, "category"):
                root_cause_category = str(root_cause.category)
            else:
                root_cause_category = str(root_cause)

            if hasattr(root_cause, "root_cause_summary"):
                root_cause_summary = str(root_cause.root_cause_summary)
            elif hasattr(root_cause, "summary"):
                root_cause_summary = str(root_cause.summary)

            if hasattr(root_cause, "is_recoverable"):
                is_recoverable = bool(root_cause.is_recoverable)

        limit_retries = (
            max_retries if max_retries is not None else self.default_max_retries
        )

        limit_healing = (
            max_healing_attempts
            if max_healing_attempts is not None
            else self.default_max_healing_attempts
        )

        # 1. Per-task retry limit.
        if task.retry_count >= limit_retries:
            msg = f"Task {task.task_id} reached max retry limit " f"of {limit_retries}."
            logger.info(msg)
            return False, msg

        # 2. Total healing attempts for this task.
        healing_attempts_for_task = sum(
            1 for healing in state.healing_history if healing.task_id == task.task_id
        )

        if healing_attempts_for_task >= limit_healing:
            msg = (
                f"Task {task.task_id} reached max healing attempts "
                f"limit of {limit_healing}."
            )
            logger.info(msg)
            return False, msg

        # 3. Infinite-loop protection.
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

        # 4. Root-cause recoverability.
        if not is_recoverable:
            msg = f"Root cause '{root_cause_category}' " "is non-recoverable."
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
        Creates an authorized WorkerReexecutionRequest through the
        WorkerReexecutionManager.
        """

        return self.reexecution_manager.create_reexecution_request(
            task=task,
            recovery_plan=recovery_plan,
            state=state,
        )

    def validate_retry_eligibility(
        self,
        task: Task,
        state: SharedWorkflowState,
        error: Optional[TaskError] = None,
        max_retries: Optional[int] = None,
        recovery_plan: Optional[RecoveryPlan] = None,
    ) -> Tuple[bool, RetryStatus, str]:
        """
        Validates whether a task is eligible for retry.

        Returns:
            Tuple[bool, RetryStatus, str]:
                (is_eligible, status, reason)
        """

        limit = max_retries if max_retries is not None else self.default_max_retries

        # 1. Maximum retry limit.
        if task.retry_count >= limit:
            msg = (
                f"Task {task.task_id} reached maximum retry limit "
                f"({task.retry_count}/{limit})."
            )
            logger.info(msg)

            return (
                False,
                RetryStatus.REJECTED_MAX_RETRIES,
                msg,
            )

        # 2. Task state.
        if task.status not in (
            TaskStatus.FAILED,
            TaskStatus.HEALING,
            TaskStatus.WAITING,
        ):
            msg = (
                f"Task {task.task_id} is in status "
                f"{task.status.value} and is not eligible for retry."
            )
            logger.info(msg)

            return (
                False,
                RetryStatus.REJECTED_INVALID_STATE,
                msg,
            )

        # 3. Workflow state.
        if state.metadata.status != WorkflowStatus.RUNNING:
            msg = (
                f"Workflow {state.metadata.workflow_id} is not RUNNING "
                f"(current: {state.metadata.status.value})."
            )
            logger.info(msg)

            return (
                False,
                RetryStatus.REJECTED_INVALID_STATE,
                msg,
            )

        # 4. Dependencies.
        for dep_id in task.dependencies:
            dep_task = state.tasks.get(dep_id)

            if not dep_task:
                msg = f"Dependency task {dep_id} not found " "in workflow state."
                logger.info(msg)

                return (
                    False,
                    RetryStatus.REJECTED_INVALID_STATE,
                    msg,
                )

            if dep_task.status != TaskStatus.COMPLETED:
                msg = (
                    f"Dependency task {dep_id} is not COMPLETED "
                    f"(current status: {dep_task.status.value})."
                )
                logger.info(msg)

                return (
                    False,
                    RetryStatus.REJECTED_INVALID_STATE,
                    msg,
                )

        # 5. Permission checks.
        task_perms = [req for req in state.permissions if req.task_id == task.task_id]

        for req in task_perms:
            if req.status in (
                PermissionStatus.REJECTED,
                PermissionStatus.PENDING,
            ):
                msg = (
                    f"Task {task.task_id} has permission request "
                    f"in status: {req.status.value}."
                )
                logger.info(msg)

                return (
                    False,
                    RetryStatus.REJECTED_PERMISSION_DENIED,
                    msg,
                )

        for perm_str in task.permissions:
            try:
                perm_type = PermissionType(perm_str.upper())

                granted_reqs = [
                    req
                    for req in state.permissions
                    if (
                        req.workflow_id == state.metadata.workflow_id
                        and req.permission_type == perm_type
                        and req.status == PermissionStatus.GRANTED
                    )
                ]

                if not granted_reqs:
                    msg = (
                        f"Required permission '{perm_str}' "
                        "is not granted for workflow."
                    )
                    logger.info(msg)

                    return (
                        False,
                        RetryStatus.REJECTED_PERMISSION_DENIED,
                        msg,
                    )

            except ValueError:
                logger.warning(
                    f"Task {task.task_id} has invalid permission " f"string: {perm_str}"
                )

                msg = f"Invalid permission specification: {perm_str}"

                return (
                    False,
                    RetryStatus.REJECTED_PERMISSION_DENIED,
                    msg,
                )

        # 6. Recovery-plan retryability.
        if recovery_plan and not recovery_plan.is_retryable:
            msg = "Recovery plan explicitly marks failure " "as non-retryable."
            logger.info(msg)

            return (
                False,
                RetryStatus.REJECTED_NON_RETRYABLE,
                msg,
            )

        # 7. Error retryability.
        if error:
            if not error.is_recoverable:
                msg = (
                    f"Error {error.error_code} is explicitly " "marked non-recoverable."
                )
                logger.info(msg)

                return (
                    False,
                    RetryStatus.REJECTED_NON_RETRYABLE,
                    msg,
                )

            err_code = error.error_code.upper() if error.error_code else ""

            if err_code in NON_RETRYABLE_ERROR_CODES:
                msg = f"Error code '{err_code}' is classified " "as non-retryable."
                logger.info(msg)

                return (
                    False,
                    RetryStatus.REJECTED_NON_RETRYABLE,
                    msg,
                )

        # 8. Destructive-operation safety.
        is_destructive = False

        if getattr(task, "risk_level", "LOW") in (
            "HIGH",
            "CRITICAL",
        ):
            is_destructive = True

        if task.rollback_info is not None:
            is_destructive = True

        if is_destructive:
            has_approval = False

            if recovery_plan and recovery_plan.strategy in (
                "RETRY",
                "RETRY_WITH_BACKOFF",
                "APPROVED_RETRY",
            ):
                has_approval = True

            elif error:
                err_msg = error.error_message.upper() if error.error_message else ""

                err_code = error.error_code.upper() if error.error_code else ""

                is_transient = any(
                    code in err_code for code in TRANSIENT_ERROR_CODES
                ) or any(code in err_msg for code in TRANSIENT_ERROR_CODES)

                if is_transient:
                    has_approval = True

            if not has_approval:
                msg = (
                    f"Destructive task {task.task_id} requires "
                    "recovery plan approval or transient failure "
                    "status to retry."
                )
                logger.info(msg)

                return (
                    False,
                    RetryStatus.REJECTED_DESTRUCTIVE_UNAPPROVED,
                    msg,
                )

        return (
            True,
            RetryStatus.TRIGGERED,
            "Task is eligible for retry.",
        )

    async def execute_retry(
        self,
        request: RetryRequest,
        state: SharedWorkflowState,
    ) -> RetryResult:
        """
        Executes an approved retry request.

        The method:
        - Validates the task
        - Checks retry/healing limits
        - Checks permissions and safety policies
        - Records the failure signature
        - Creates worker re-execution request
        - Calculates backoff
        - Updates task state
        - Records healing history
        - Enqueues replacement tasks
        - Re-enqueues the original task
        - Publishes runtime events
        """

        task = state.tasks.get(request.task_id)

        if not task:
            msg = f"Task {request.task_id} not found " "in workflow state."
            logger.error(msg)

            return RetryResult(
                retry_id=request.retry_id,
                task_id=request.task_id,
                workflow_id=request.workflow_id,
                success=False,
                status=RetryStatus.ERROR,
                attempt_number=request.attempt_number,
                message=msg,
            )

        # Determine root cause / recovery description for loop protection.
        root_cause_category = "RUNTIME"

        if request.error and request.error.error_code:
            root_cause_category = request.error.error_code

        root_cause_summary = (
            request.recovery_plan.reason
            if request.recovery_plan and request.recovery_plan.reason
            else (
                request.reason
                or (
                    request.error.error_message
                    if request.error and request.error.error_message
                    else "Task failure"
                )
            )
        )

        # Check worker-reexecution healing limits and loop protection.
        can_reexecute, reexecution_reason = self.can_retry(
            task=task,
            state=state,
            root_cause_category=root_cause_category,
            root_cause_summary=root_cause_summary,
            is_recoverable=(request.error.is_recoverable if request.error else True),
            max_retries=request.max_retries,
        )

        if not can_reexecute:
            logger.warning(
                f"Retry request for task {task.task_id} rejected "
                f"by healing protection: {reexecution_reason}"
            )

            return RetryResult(
                retry_id=request.retry_id,
                task_id=request.task_id,
                workflow_id=request.workflow_id,
                success=False,
                status=RetryStatus.REJECTED_NON_RETRYABLE,
                attempt_number=task.retry_count,
                message=reexecution_reason,
            )

        # Full retry eligibility validation.
        (
            is_eligible,
            status,
            reason,
        ) = self.validate_retry_eligibility(
            task=task,
            state=state,
            error=request.error,
            max_retries=request.max_retries,
            recovery_plan=request.recovery_plan,
        )

        if not is_eligible:
            logger.warning(
                f"Retry request for task {task.task_id} rejected: "
                f"{reason} (Status: {status.value})"
            )

            if self.event_bus:
                await self.event_bus.publish(
                    RuntimeEvent(
                        workflow_id=state.metadata.workflow_id,
                        task_id=task.task_id,
                        event_type=EventType.HEALING_FAILED,
                        source_component=EventSource.HEALING,
                        payload={
                            "reason": reason,
                            "status": status.value,
                            "retry_count": task.retry_count,
                        },
                    )
                )

            return RetryResult(
                retry_id=request.retry_id,
                task_id=request.task_id,
                workflow_id=request.workflow_id,
                success=False,
                status=status,
                attempt_number=task.retry_count,
                message=reason,
            )

        # Record the failure signature.
        signature = (
            str(task.task_id),
            root_cause_category,
            root_cause_summary,
        )

        self._failure_signature_counts[signature] = (
            self._failure_signature_counts.get(signature, 0) + 1
        )

        # Calculate backoff.
        backoff_override = None

        if request.recovery_plan and request.recovery_plan.backoff_seconds > 0:
            backoff_override = request.recovery_plan.backoff_seconds
        elif request.delay_seconds:
            backoff_override = request.delay_seconds

        delay_sec = self.calculate_backoff_delay(
            attempt_number=task.retry_count + 1,
            backoff_override=backoff_override,
        )

        # Create worker re-execution request.
        #
        # This preserves the feature branch's worker-reexecution
        # contract/history without replacing the main RetryRequest flow.
        try:
            self.create_reexecution_request(
                task=task,
                recovery_plan=request.recovery_plan,
                state=state,
            )
        except Exception:
            logger.exception(
                "Failed to create WorkerReexecutionRequest for task %s",
                task.task_id,
            )

        # Update retry count.
        task.retry_count += 1

        # Apply recovery-plan task parameter changes.
        if request.recovery_plan and request.recovery_plan.updated_task_params:
            for key, value in request.recovery_plan.updated_task_params.items():
                if hasattr(task, key):
                    setattr(task, key, value)

        # Append execution log.
        log_entry = (
            f"[{datetime.now(timezone.utc).isoformat()}] "
            f"Retry attempt {task.retry_count} "
            "triggered via Workflow Engine "
            f"(Delay: {delay_sec:.2f}s, "
            f"Reason: {request.reason or 'Recovery attempt'})."
        )

        task.execution_logs.append(log_entry)

        # Determine healing strategy.
        strategy = request.recovery_plan.strategy if request.recovery_plan else "RETRY"

        root_cause = (
            request.recovery_plan.reason
            if (request.recovery_plan and request.recovery_plan.reason)
            else (
                request.reason
                or (
                    request.error.error_message
                    if request.error and request.error.error_message
                    else "Task failure"
                )
            )
        )

        # Record healing result.
        healing_entry = HealingResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            root_cause=root_cause,
            recovery_strategy=strategy,
            replacement_tasks=(
                request.recovery_plan.replacement_tasks if request.recovery_plan else []
            ),
            attempt_number=task.retry_count,
            success=True,
        )

        state.healing_history.append(healing_entry)

        # Record system log.
        state.logs.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "component": "RetryEngine",
                "message": (
                    f"Retry attempt {task.retry_count} enqueued "
                    f"for task {task.task_id} with "
                    f"{delay_sec:.2f}s delay."
                ),
            }
        )

        # Remove task from failed list.
        if task.task_id in state.failed_tasks:
            state.failed_tasks.remove(task.task_id)

        # Workflow Engine integration.
        engine = WorkflowEngine(state)

        # Enqueue replacement tasks first.
        if request.recovery_plan and request.recovery_plan.replacement_tasks:
            for replacement_task in request.recovery_plan.replacement_tasks:
                engine.enqueue(replacement_task)

        # Re-enqueue the original task.
        engine.enqueue(task)

        logger.info(
            "Retry Engine successfully enqueued attempt %s "
            "for task %s through Workflow Engine.",
            task.retry_count,
            task.task_id,
        )

        # Publish runtime events.
        if self.event_bus:
            if request.recovery_plan:
                await self.event_bus.publish(
                    RuntimeEvent(
                        workflow_id=state.metadata.workflow_id,
                        task_id=task.task_id,
                        event_type=EventType.HEALING_STARTED,
                        source_component=EventSource.HEALING,
                        payload={
                            "attempt_number": task.retry_count,
                            "strategy": strategy,
                        },
                    )
                )

            await self.event_bus.publish(
                RuntimeEvent(
                    workflow_id=state.metadata.workflow_id,
                    task_id=task.task_id,
                    event_type=EventType.TASK_RETRIED,
                    source_component=EventSource.HEALING,
                    payload={
                        "retry_count": task.retry_count,
                        "max_retries": request.max_retries,
                        "delay_seconds": delay_sec,
                        "reason": request.reason,
                    },
                )
            )

            if request.recovery_plan:
                await self.event_bus.publish(
                    RuntimeEvent(
                        workflow_id=state.metadata.workflow_id,
                        task_id=task.task_id,
                        event_type=EventType.HEALING_COMPLETED,
                        source_component=EventSource.HEALING,
                        payload={
                            "attempt_number": task.retry_count,
                            "status": RetryStatus.TRIGGERED.value,
                        },
                    )
                )

        return RetryResult(
            retry_id=request.retry_id,
            task_id=request.task_id,
            workflow_id=request.workflow_id,
            success=True,
            status=RetryStatus.TRIGGERED,
            attempt_number=task.retry_count,
            delay_seconds=delay_sec,
            message=(
                f"Retry attempt {task.retry_count} successfully "
                "enqueued through Workflow Engine."
            ),
        )

    async def execute_recovery(
        self,
        plan: Any,
        task: Task,
        state: SharedWorkflowState,
        root_cause_category: str = "RUNTIME",
        attempt_number: int = 1,
        **kwargs: Any,
    ) -> HealingResult:
        """
        Backward-compatible recovery API.

        Converts the older recovery-plan interface into the current
        retry execution flow.
        """
        # Backward compatibility for passing root_cause object
        root_cause = kwargs.get("root_cause")
        if root_cause is not None:
            if hasattr(root_cause, "category"):
                root_cause_category = str(root_cause.category)
            else:
                root_cause_category = str(root_cause)

        logger.info(
            "RetryEngine executing recovery for task %s " "(Attempt #%s)",
            task.task_id,
            attempt_number,
        )

        strategy_val = (
            plan.strategy.value
            if hasattr(
                getattr(plan, "strategy", None),
                "value",
            )
            else str(getattr(plan, "strategy", "RETRY"))
        )

        is_executable = getattr(
            plan,
            "is_executable",
            True,
        )

        if not is_executable or strategy_val in (
            "ESCALATE_USER",
            "CANCEL_WORKFLOW",
            "REQUEST_PERMISSION_AGAIN",
        ):
            logger.info(
                "Recovery plan for task %s is non-executable.",
                task.task_id,
            )

            return HealingResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                root_cause=root_cause_category,
                recovery_strategy=strategy_val,
                replacement_tasks=getattr(
                    plan,
                    "replacement_tasks",
                    [],
                ),
                attempt_number=attempt_number,
                success=False,
            )

        try:
            # Record failure signature.
            signature = (
                str(task.task_id),
                root_cause_category,
                getattr(
                    plan,
                    "description",
                    "Recovery plan",
                ),
            )

            self._failure_signature_counts[signature] = (
                self._failure_signature_counts.get(
                    signature,
                    0,
                )
                + 1
            )

            # Protect against repeated identical recovery.
            if self._failure_signature_counts[signature] > 3:
                logger.warning(
                    "Infinite recovery loop detected for task %s.",
                    task.task_id,
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

            engine = WorkflowEngine(state)

            replacement_tasks = getattr(
                plan,
                "replacement_tasks",
                [],
            )

            if replacement_tasks:
                logger.info(
                    "Submitting %s replacement tasks " "to WorkflowEngine.",
                    len(replacement_tasks),
                )

                engine.update_task_status(
                    task.task_id,
                    TaskStatus.FAILED,
                )

                for replacement_task in replacement_tasks:
                    engine.enqueue(replacement_task)

            else:
                self.create_reexecution_request(
                    task=task,
                    recovery_plan=plan,
                    state=state,
                )

                task.retry_count += 1

                logger.info(
                    "Re-enqueueing task %s " "(New retry count: %s)",
                    task.task_id,
                    task.retry_count,
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

        except Exception as exc:
            logger.exception(
                "RetryEngine failed recovery for task %s: %s",
                task.task_id,
                exc,
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

    async def request_retry(
        self,
        task_id: UUID,
        workflow_id: UUID,
        state: SharedWorkflowState,
        error: Optional[TaskError] = None,
        recovery_plan: Optional[RecoveryPlan] = None,
        max_retries: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> RetryResult:
        """
        Helper method that constructs and executes a RetryRequest.
        """

        task = state.tasks.get(task_id)

        current_attempt = task.retry_count + 1 if task else 1

        limit = max_retries if max_retries is not None else self.default_max_retries

        req_reason = reason

        if not req_reason and error:
            req_reason = error.error_message

        elif not req_reason and recovery_plan:
            req_reason = recovery_plan.reason

        request = RetryRequest(
            task_id=task_id,
            workflow_id=workflow_id,
            attempt_number=current_attempt,
            max_retries=limit,
            error=error,
            recovery_plan=recovery_plan,
            reason=req_reason,
        )

        return await self.execute_retry(
            request,
            state,
        )
