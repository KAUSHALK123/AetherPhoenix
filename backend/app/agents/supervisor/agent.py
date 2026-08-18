import logging
from typing import Any, Optional

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionResult,
    SupervisorDecision,
    SupervisorValidation,
    TaskError,
)
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.retry_engine import RetryEngine
from app.agents.supervisor.failure_detector import FailureDetectorService
from app.core.events.bus import EventBus
from app.core.events.models import Event as ModelEvent
from app.core.events.models import EventType as ModelEventType
from app.engine.monitor import WorkflowProgressMonitor
from app.engine.validator import OutputValidationService
from app.memory.task_history import TaskHistoryService, get_task_history_service
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
        healing_loop: Optional[Any] = None,
        retry_engine: Optional[RetryEngine] = None,
        task_history_service: Optional[TaskHistoryService] = None,
    ) -> None:
        self.event_bus = event_bus
        self.max_retries = max_retries
        self.monitor = WorkflowProgressMonitor()
        self.validator = OutputValidationService()
        self.failure_detector = failure_detector or FailureDetectorService()
        self.retry_engine = retry_engine or RetryEngine(
            event_bus=self.event_bus, default_max_retries=self.max_retries
        )
        self.task_history_service = task_history_service or get_task_history_service()
        from app.agents.healing.self_healing_loop import SelfHealingLoop

        self.healing_loop = healing_loop or SelfHealingLoop(
            event_bus=self.event_bus,
            max_retries=self.max_retries,
            retry_engine=self.retry_engine,
        )

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
                self.task_history_service.record_task_failed(
                    task_id=task.task_id,
                    error=TaskError(
                        error_code="SUPERVISOR_VALIDATION_FAILED",
                        error_message=(
                            "; ".join(issues) if issues else "Validation failed"
                        ),
                    ),
                    metadata={"supervisor_decision": decision.value, "checks": checks},
                )

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
        and delegates recovery to the Self-Healing Loop.
        Updates the task and workflow state, and publishes the corresponding events.
        and requests a retry if eligible through the RetryEngine.

        Returns:
            bool: True if recovery/retry was successfully triggered, False otherwise.
        """
        logger.info(
            f"SupervisorAgent executing failure analysis for task {task.task_id}"
        )

        eligible = self.is_eligible_for_retry(task, state, error, max_retries)
        if not eligible:
            logger.info(f"Task {task.task_id} is not eligible for retry.")
            return False

        # Delegate recovery execution to Self-Healing Loop
        healing_result = await self.healing_loop.process_failure(
            task=task,
            failure_input=error
            or TaskError(
                error_code="VALIDATION_FAILED",
                error_message="Supervisor output validation failed.",
            ),
            state=state,
        )

        if healing_result.success:
            self.task_history_service.record_retry_attempt(
                task_id=task.task_id,
                attempt_number=task.retry_count + 1,
                reason=error.error_message if error else None,
                metadata={"supervisor_trigger": True},
            )
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

        return False
        retry_result = await self.retry_engine.request_retry(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            state=state,
            error=error,
            max_retries=max_retries,
            reason=error.error_message if error else None,
        )

        return retry_result.success

    def is_eligible_for_retry(
        self,
        task: Task,
        state: SharedWorkflowState,
        error: Optional[TaskError] = None,
        max_retries: Optional[int] = None,
    ) -> bool:
        """
        Determines whether a failed task is eligible for a retry through RetryEngine.
        """
        is_eligible, _, _ = self.retry_engine.validate_retry_eligibility(
            task=task,
            state=state,
            error=error,
            max_retries=max_retries,
        )
        return is_eligible

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
