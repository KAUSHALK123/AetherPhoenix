from datetime import datetime, timezone
import logging
from typing import Optional, Tuple
from uuid import UUID

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import HealingResult, TaskError
from shared.contracts.permission import PermissionStatus, PermissionType
from shared.contracts.retry import (
    RecoveryPlan,
    RetryRequest,
    RetryResult,
    RetryStatus,
)
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowStatus

from app.core.events.bus import EventBus
from app.engine.workflow import WorkflowEngine

logger = logging.getLogger(__name__)

# Non-retryable error codes:
NON_RETRYABLE_ERROR_CODES = {
    "PERMISSION_DENIED",
    "TOOL_NOT_FOUND",
    "TOOL_DISABLED",
    "INVALID_WORKFLOW",
    "UNSUPPORTED_CAPABILITY",
    "INVALID_PERMISSION",
}

# Transient/Retryable error codes (for destructive operations):
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
    Retry Engine component for Sprint 5 (Healing Agent).

    Validates, manages, and executes controlled retry requests by interfacing
    with the Workflow Engine. Enforces maximum retry limits, permission checks,
    exponential backoff, destructive operation policies, and complete history tracking.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        default_max_retries: int = 3,
        base_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 60.0,
    ) -> None:
        self.event_bus = event_bus
        self.default_max_retries = default_max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds

    def calculate_backoff_delay(
        self,
        attempt_number: int,
        backoff_override: Optional[float] = None,
    ) -> float:
        """
        Calculates exponential backoff delay based on attempt number.
        Formula: min(base_backoff * 2^(attempt - 1), max_backoff)
        """
        if backoff_override is not None and backoff_override > 0:
            return float(backoff_override)

        exponent = max(0, attempt_number - 1)
        delay = self.base_backoff_seconds * (2**exponent)
        return min(delay, self.max_backoff_seconds)

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
            Tuple[bool, RetryStatus, str]: (is_eligible, status, reason)
        """
        limit = max_retries if max_retries is not None else self.default_max_retries

        # 1. Enforce maximum retry limit
        if task.retry_count >= limit:
            msg = (
                f"Task {task.task_id} reached maximum retry limit "
                f"({task.retry_count}/{limit})."
            )
            logger.info(msg)
            return False, RetryStatus.REJECTED_MAX_RETRIES, msg

        # 2. Check task state (must be FAILED or HEALING)
        if task.status not in (TaskStatus.FAILED, TaskStatus.HEALING, TaskStatus.WAITING):
            msg = (
                f"Task {task.task_id} is in status {task.status.value} "
                f"and is not eligible for retry."
            )
            logger.info(msg)
            return False, RetryStatus.REJECTED_INVALID_STATE, msg

        # 3. Check workflow state (must be RUNNING)
        if state.metadata.status != WorkflowStatus.RUNNING:
            msg = (
                f"Workflow {state.metadata.workflow_id} is not RUNNING "
                f"(current: {state.metadata.status.value})."
            )
            logger.info(msg)
            return False, RetryStatus.REJECTED_INVALID_STATE, msg

        # 4. Check dependencies (all parent dependencies must be COMPLETED)
        for dep_id in task.dependencies:
            dep_task = state.tasks.get(dep_id)
            if not dep_task:
                msg = f"Dependency task {dep_id} not found in workflow state."
                logger.info(msg)
                return False, RetryStatus.REJECTED_INVALID_STATE, msg
            if dep_task.status != TaskStatus.COMPLETED:
                msg = (
                    f"Dependency task {dep_id} is not COMPLETED "
                    f"(current status: {dep_task.status.value})."
                )
                logger.info(msg)
                return False, RetryStatus.REJECTED_INVALID_STATE, msg

        # 5. Check permissions
        task_perms = [req for req in state.permissions if req.task_id == task.task_id]
        for req in task_perms:
            if req.status in (PermissionStatus.REJECTED, PermissionStatus.PENDING):
                msg = (
                    f"Task {task.task_id} has permission request in "
                    f"status: {req.status.value}."
                )
                logger.info(msg)
                return False, RetryStatus.REJECTED_PERMISSION_DENIED, msg

        for perm_str in task.permissions:
            try:
                perm_type = PermissionType(perm_str.upper())
                granted_reqs = [
                    req
                    for req in state.permissions
                    if req.workflow_id == state.metadata.workflow_id
                    and req.permission_type == perm_type
                    and req.status == PermissionStatus.GRANTED
                ]
                if not granted_reqs:
                    msg = f"Required permission '{perm_str}' is not granted for workflow."
                    logger.info(msg)
                    return False, RetryStatus.REJECTED_PERMISSION_DENIED, msg
            except ValueError:
                logger.warning(
                    f"Task {task.task_id} has invalid permission string: {perm_str}"
                )
                msg = f"Invalid permission specification: {perm_str}"
                return False, RetryStatus.REJECTED_PERMISSION_DENIED, msg

        # 6. Check recovery plan and error retryability
        if recovery_plan and not recovery_plan.is_retryable:
            msg = "Recovery plan explicitly marks failure as non-retryable."
            logger.info(msg)
            return False, RetryStatus.REJECTED_NON_RETRYABLE, msg

        if error:
            if not error.is_recoverable:
                msg = f"Error {error.error_code} is explicitly marked non-recoverable."
                logger.info(msg)
                return False, RetryStatus.REJECTED_NON_RETRYABLE, msg

            err_code = error.error_code.upper() if error.error_code else ""
            if err_code in NON_RETRYABLE_ERROR_CODES:
                msg = f"Error code '{err_code}' is classified as non-retryable."
                logger.info(msg)
                return False, RetryStatus.REJECTED_NON_RETRYABLE, msg

        # 7. Safety policy for destructive operations
        is_destructive = False
        if getattr(task, "risk_level", "LOW") in ("HIGH", "CRITICAL"):
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
                    f"Destructive task {task.task_id} requires recovery plan approval "
                    f"or transient failure status to retry."
                )
                logger.info(msg)
                return False, RetryStatus.REJECTED_DESTRUCTIVE_UNAPPROVED, msg

        return True, RetryStatus.TRIGGERED, "Task is eligible for retry."

    async def execute_retry(
        self,
        request: RetryRequest,
        state: SharedWorkflowState,
    ) -> RetryResult:
        """
        Executes an approved retry request by validating eligibility, updating state,
        logging history, and re-enqueueing the task through the Workflow Engine.
        """
        task = state.tasks.get(request.task_id)
        if not task:
            msg = f"Task {request.task_id} not found in workflow state."
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

        # Validate eligibility
        is_eligible, status, reason = self.validate_retry_eligibility(
            task=task,
            state=state,
            error=request.error,
            max_retries=request.max_retries,
            recovery_plan=request.recovery_plan,
        )

        if not is_eligible:
            logger.warning(
                f"Retry request for task {task.task_id} rejected: {reason} "
                f"(Status: {status.value})"
            )
            # Emit failure event if event bus present
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
                task_id=task.task_id,
                workflow_id=request.workflow_id,
                success=False,
                status=status,
                attempt_number=task.retry_count,
                message=reason,
            )

        # Calculate backoff delay
        backoff_override = (
            request.recovery_plan.backoff_seconds
            if request.recovery_plan and request.recovery_plan.backoff_seconds > 0
            else request.delay_seconds
        )
        delay_sec = self.calculate_backoff_delay(
            attempt_number=task.retry_count + 1,
            backoff_override=backoff_override,
        )

        # Update task retry count and parameters
        task.retry_count += 1

        if request.recovery_plan and request.recovery_plan.updated_task_params:
            for key, value in request.recovery_plan.updated_task_params.items():
                if hasattr(task, key):
                    setattr(task, key, value)

        # Append execution log entry
        log_entry = (
            f"[{datetime.now(timezone.utc).isoformat()}] Retry attempt {task.retry_count} "
            f"triggered via Workflow Engine (Delay: {delay_sec:.2f}s, "
            f"Reason: {request.reason or 'Recovery attempt'})."
        )
        task.execution_logs.append(log_entry)

        # Record HealingResult in Shared Workflow State history
        strategy = (
            request.recovery_plan.strategy
            if request.recovery_plan
            else "RETRY"
        )
        root_cause = (
            request.recovery_plan.reason
            if request.recovery_plan and request.recovery_plan.reason
            else (request.reason or "Task failure")
        )
        healing_entry = HealingResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            root_cause=root_cause,
            recovery_strategy=strategy,
            attempt_number=task.retry_count,
            success=True,
        )
        state.healing_history.append(healing_entry)

        # Record system log entry
        state.logs.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "component": "RetryEngine",
                "message": (
                    f"Retry attempt {task.retry_count} enqueued for task {task.task_id} "
                    f"with {delay_sec:.2f}s delay."
                ),
            }
        )

        # Manage state lists
        if task.task_id in state.failed_tasks:
            state.failed_tasks.remove(task.task_id)

        # Workflow Engine integration
        engine = WorkflowEngine(state)

        # Process replacement tasks if provided by RecoveryPlan
        if request.recovery_plan and request.recovery_plan.replacement_tasks:
            for repl_task in request.recovery_plan.replacement_tasks:
                engine.enqueue(repl_task)

        # Re-enqueue the target task for worker execution
        engine.enqueue(task)

        logger.info(
            f"Retry Engine successfully enqueued attempt {task.retry_count} "
            f"for task {task.task_id} through Workflow Engine."
        )

        # Emit Runtime Events
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
            task_id=task.task_id,
            workflow_id=request.workflow_id,
            success=True,
            status=RetryStatus.TRIGGERED,
            attempt_number=task.retry_count,
            delay_seconds=delay_sec,
            message=(
                f"Retry attempt {task.retry_count} successfully enqueued "
                f"through Workflow Engine."
            ),
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
        Helper method to construct and execute a RetryRequest.
        """
        task = state.tasks.get(task_id)
        current_attempt = (task.retry_count + 1) if task else 1
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

        return await self.execute_retry(request, state)
