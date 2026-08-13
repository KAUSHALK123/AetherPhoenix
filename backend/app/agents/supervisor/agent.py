import logging
from typing import Any, Optional

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionResult,
    SupervisorDecision,
    SupervisorValidation,
    TaskError,
)
from shared.contracts.permission import PermissionStatus, PermissionType
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowStatus

from app.agents.supervisor.failure_detector import FailureDetectorService
from app.core.events.bus import EventBus
from app.core.events.models import Event as ModelEvent
from app.core.events.models import EventType as ModelEventType
from app.engine.monitor import WorkflowProgressMonitor
from app.engine.validator import OutputValidationService
from app.engine.workflow import WorkflowEngine
from app.runtime.interfaces import AgentRegistration, BaseAgent

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


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent responsible for validating Worker execution results,
    updating workflow state, analyzing failures, and triggering controlled
    task retries through the Workflow Engine.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        failure_detector: Optional[FailureDetectorService] = None,
        max_retries: int = 3,
    ) -> None:
        self.event_bus = event_bus
        self.max_retries = max_retries
        self.monitor = WorkflowProgressMonitor()
        self.validator = OutputValidationService()
        self.failure_detector = failure_detector or FailureDetectorService()

    @property
    def registration(self) -> AgentRegistration:
        """Returns registration metadata for the Supervisor Agent."""
        return AgentRegistration(
            name="SupervisorAgent",
            version="1.0.0",
            description=(
                "Performs Quality Assurance, validating task execution, "
                "detecting failures, and triggering controlled retries."
            ),
        )

    async def initialize(self) -> None:
        """Lifecycle hook: Called when the agent is registered."""
        logger.info("SupervisorAgent initialized.")
        if self.event_bus:
            # Subscribe to task failure events
            self.event_bus.subscribe(
                ModelEventType.TASK_FAILED, self.handle_task_failure_event
            )

    async def shutdown(self) -> None:
        """Lifecycle hook: Called when the kernel shuts down."""
        logger.info("SupervisorAgent shut down.")
        if self.event_bus:
            self.event_bus.unsubscribe(
                ModelEventType.TASK_FAILED, self.handle_task_failure_event
            )

    async def _emit_event(
        self,
        event_type: EventType,
        payload: dict,
        workflow_id: str,
        task_id: str | None = None,
    ) -> None:
        if self.event_bus:
            event = RuntimeEvent(
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type,
                source_component=EventSource.SUPERVISOR,
                payload=payload,
            )
            await self.event_bus.publish(event)

    async def execute(
        self,
        task: Task,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Main execution loop for Supervisor Agent. Handles both validation
        and retry triggering based on arguments.
        """
        # Determine if we are performing validation or retry triggering
        is_validation = False
        result = None
        state = None

        if args:
            if isinstance(args[0], ExecutionResult):
                is_validation = True
                result = args[0]
                if len(args) > 1:
                    state = args[1]
            elif isinstance(kwargs.get("result"), ExecutionResult):
                is_validation = True
                result = kwargs.get("result")
                state = args[0] if len(args) > 0 else kwargs.get("state")
        elif "result" in kwargs:
            if isinstance(kwargs["result"], ExecutionResult):
                is_validation = True
                result = kwargs["result"]
                state = kwargs.get("state")

        if is_validation:
            return await self._execute_validation(task, result, state)
        else:
            state = args[0] if args else kwargs.get("state")
            error = args[1] if len(args) > 1 else kwargs.get("error")
            max_retries = args[2] if len(args) > 2 else kwargs.get("max_retries")
            return await self._execute_retry(task, state, error, max_retries)

    async def _execute_validation(
        self,
        task: Task,
        result: ExecutionResult,
        state: SharedWorkflowState,
    ) -> SupervisorValidation:
        """
        Validates the ExecutionResult from the WorkerAgent.
        """
        logger.info(
            f"SupervisorAgent evaluating task: {task.task_id} ({task.task_name})"
        )

        await self._emit_event(
            EventType.SUPERVISION_STARTED,
            {"task_id": str(task.task_id), "status": "STARTED"},
            str(task.workflow_id),
            str(task.task_id),
        )

        # 1. Output and Artifact Validation
        is_valid, checks, issues = self.validator.validate(task, result)

        # 2. Centralized Failure Detection Check
        failure_report = self.failure_detector.check_failure(task, result, state)

        # Merge FailureDetectorService checks
        detector_checks = {
            "worker_success": result.success,
            "no_tool_error": not self.failure_detector._is_tool_error(result),
            "expected_output_present": not self.failure_detector._is_output_missing(
                task, result
            ),
            "artifacts_valid_fs": self.failure_detector._check_artifact_failures(
                result.artifacts
            )
            is None,
            "no_timeout": not self.failure_detector._is_timeout(task, result),
            "dependencies_ok": self.failure_detector._check_dependency_failures(
                task, state
            )
            is None,
            "permissions_ok": not self.failure_detector._is_permission_denied(result),
            "tool_available": not self.failure_detector._is_tool_unavailable(result),
            "no_workflow_block": not self.failure_detector._is_workflow_blocked(state),
        }
        checks.update(detector_checks)

        if failure_report:
            is_valid = False
            issues.append(failure_report.message)

        # Determine decision
        if is_valid:
            decision = SupervisorDecision.PASSED
        else:
            decision = SupervisorDecision.FAILED

        # Create validation report
        validation = SupervisorValidation(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            is_valid=is_valid,
            decision=decision,
            checks=checks,
            issues=issues,
        )

        # Update Shared Workflow State
        try:
            state.validations[task.task_id] = validation

            # Remove from running if present
            if task.task_id in state.running_tasks:
                state.running_tasks.remove(task.task_id)

            if decision == SupervisorDecision.PASSED:
                task.status = TaskStatus.COMPLETED
                if task.task_id not in state.completed_tasks:
                    state.completed_tasks.append(task.task_id)
            else:
                task.status = TaskStatus.FAILED
                if task.task_id not in state.failed_tasks:
                    state.failed_tasks.append(task.task_id)

            self.monitor.update_progress_state(state)

            logger.info(
                f"SupervisorAgent decision for {task.task_id}: {decision.value}"
            )

            await self._emit_event(
                EventType.SUPERVISION_COMPLETED,
                {
                    "task_id": str(task.task_id),
                    "decision": decision.value,
                    "is_valid": is_valid,
                },
                str(task.workflow_id),
                str(task.task_id),
            )
        except Exception as e:
            logger.error(f"Failed to update SWS or emit completion event: {e}")
            await self._emit_event(
                EventType.SUPERVISION_FAILED,
                {"task_id": str(task.task_id), "error": str(e)},
                str(task.workflow_id),
                str(task.task_id),
            )
            raise

        return validation

    async def _execute_retry(
        self,
        task: Task,
        state: SharedWorkflowState,
        error: Optional[TaskError] = None,
        max_retries: Optional[int] = None,
    ) -> bool:
        """
        Analyzes a failed task, determines retry eligibility,
        and requests a retry if eligible.
        Updates the task and workflow state, and publishes the corresponding events.

        Returns:
            bool: True if retry was successfully triggered, False otherwise.
        """
        logger.info(
            f"SupervisorAgent executing failure analysis for task {task.task_id}"
        )

        eligible = self.is_eligible_for_retry(task, state, error, max_retries)
        if not eligible:
            logger.info(f"Task {task.task_id} is not eligible for retry.")
            return False

        # Request retry through the Workflow Engine
        engine = WorkflowEngine(state)

        # Increment retry count metadata
        task.retry_count += 1
        logger.info(
            f"Triggering retry attempt {task.retry_count} for task {task.task_id}."
        )

        # Remove the task from the failed list in state (since it's being retried)
        if task.task_id in state.failed_tasks:
            state.failed_tasks.remove(task.task_id)

        # Enqueue the task (this will set the task status to WAITING
        # and add it to the execution queue)
        engine.enqueue(task)

        # Publish a TaskRetried event
        if self.event_bus:
            retry_event = ModelEvent(
                workflow_id=str(task.workflow_id),
                task_id=str(task.task_id),
                event_type="TaskRetried",
                source_component="SupervisorAgent",
                payload={
                    "retry_count": task.retry_count,
                    "max_retries": (
                        max_retries if max_retries is not None else self.max_retries
                    ),
                    "error_code": error.error_code if error else None,
                },
            )
            await self.event_bus.publish(retry_event)

        return True

    def is_eligible_for_retry(
        self,
        task: Task,
        state: SharedWorkflowState,
        error: Optional[TaskError] = None,
        max_retries: Optional[int] = None,
    ) -> bool:
        """
        Determines whether a failed task is eligible for a retry based on:
        - Max retry count.
        - Retryable vs non-retryable failures.
        - Task state.
        - Workflow state.
        - Permission state.
        - Dependency state.
        - Existing retry_count metadata.
        """
        # Determine max retries to enforce
        limit = max_retries if max_retries is not None else self.max_retries

        # 1. Enforce max retry count
        if task.retry_count >= limit:
            logger.info(f"Task {task.task_id} reached max retry limit of {limit}.")
            return False

        # 2. Check task state (must be FAILED)
        if task.status != TaskStatus.FAILED:
            logger.info(
                f"Task {task.task_id} is not in FAILED state (current: {task.status})."
            )
            return False

        # 3. Check workflow state (must be RUNNING)
        if state.metadata.status != WorkflowStatus.RUNNING:
            logger.info(
                f"Workflow {state.metadata.workflow_id} is not RUNNING "
                f"(current: {state.metadata.status})."
            )
            return False

        # 4. Check dependencies (all parent dependencies must be COMPLETED)
        for dep_id in task.dependencies:
            dep_task = state.tasks.get(dep_id)
            if not dep_task:
                logger.info(f"Dependency task {dep_id} not found in state.")
                return False
            if dep_task.status != TaskStatus.COMPLETED:
                logger.info(
                    f"Dependency task {dep_id} is not COMPLETED "
                    f"(current: {dep_task.status})."
                )
                return False

        # 5. Check permission state
        # If any permission requests specifically for this task are pending
        # or rejected, do not retry
        task_perms = [req for req in state.permissions if req.task_id == task.task_id]
        for req in task_perms:
            if req.status in (PermissionStatus.REJECTED, PermissionStatus.PENDING):
                logger.info(
                    f"Task {task.task_id} has permission request in "
                    f"status: {req.status}."
                )
                return False

        # Also, check if all required permissions listed on the task are GRANTED
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
                    logger.info(
                        f"Required permission '{perm_str}' is not granted for workflow."
                    )
                    return False
            except ValueError:
                logger.warning(
                    f"Task {task.task_id} has invalid permission string: {perm_str}"
                )
                return False

        # 6. Check failure details (recoverable vs non-recoverable,
        # and destructive operations)
        if error:
            # If explicitly marked as not recoverable, do not retry
            if not error.is_recoverable:
                logger.info(
                    f"Task {task.task_id} failed with non-recoverable error flag."
                )
                return False

            # If error code is explicitly non-retryable, do not retry
            err_code = error.error_code.upper() if error.error_code else ""
            if err_code in NON_RETRYABLE_ERROR_CODES:
                logger.info(
                    f"Task {task.task_id} failed with non-retryable "
                    f"error code: {err_code}."
                )
                return False

            # If the task is a destructive operation (risk level high/critical
            # or rollback info exists), do not blindly retry unless it is a
            # known transient failure.
            is_destructive = False
            if getattr(task, "risk_level", "LOW") in ("HIGH", "CRITICAL"):
                is_destructive = True
            if task.rollback_info is not None:
                is_destructive = True

            if is_destructive:
                # Must be a transient error code to allow retry
                err_msg = error.error_message.upper() if error.error_message else ""
                is_transient = any(
                    code in err_code for code in TRANSIENT_ERROR_CODES
                ) or any(code in err_msg for code in TRANSIENT_ERROR_CODES)
                if not is_transient:
                    logger.info(
                        f"Destructive task {task.task_id} cannot be retried "
                        f"for non-transient error: {error.error_message}."
                    )
                    return False

        return True

    async def handle_task_failure_event(self, event: ModelEvent) -> None:
        """
        Asynchronous handler subscribed to EventType.TASK_FAILED.
        Resolves the task and state context, and triggers execute.
        """
        pass

    def get_workflow_progress(self, state: SharedWorkflowState) -> Any:
        """
        Retrieves the current workflow progress calculation.
        """
        return self.monitor.calculate_progress(state)

    def get_parallel_group_status(
        self, task_id: Any, state: SharedWorkflowState
    ) -> Optional[str]:
        """
        Returns the overall status of the parallel execution group containing task_id.
        """
        group = self.monitor.parallel_monitor.get_parallel_group(task_id, state)
        if group:
            return self.monitor.parallel_monitor.get_group_status(group, state)
        return None

    def is_task_ready(self, task_id: Any, state: SharedWorkflowState) -> bool:
        """
        Returns True if all prerequisite tasks are completed.
        """
        return (
            self.monitor.parallel_monitor.check_prerequisites(task_id, state) == "READY"
        )
