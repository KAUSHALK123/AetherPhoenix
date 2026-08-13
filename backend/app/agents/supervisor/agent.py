import logging
from typing import Any, Optional

from shared.contracts.execution import (
    ExecutionResult,
    SupervisorValidation,
)
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

from app.agents.supervisor.failure_detector import FailureDetectorService
from app.runtime.interfaces import AgentRegistration, BaseAgent

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent responsible for validation, failure detection,
    and quality assurance of task execution.
    """

    def __init__(
        self,
        event_bus: Optional[Any] = None,
        failure_detector: Optional[FailureDetectorService] = None,
    ) -> None:
        self.event_bus = event_bus
        self.failure_detector = failure_detector or FailureDetectorService()

    @property
    def registration(self) -> AgentRegistration:
        """Returns registration metadata for the Supervisor Agent."""
        return AgentRegistration(
            name="SupervisorAgent",
            version="1.0.0",
            description=(
                "Performs Quality Assurance, validating task execution "
                "and detecting failures."
            ),
        )

    async def initialize(self) -> None:
        """Lifecycle hook: Called when the agent is registered."""
        logger.info("SupervisorAgent initialized.")

    async def shutdown(self) -> None:
        """Lifecycle hook: Called when the kernel shuts down."""
        logger.info("SupervisorAgent shut down.")

    async def execute(
        self,
        task: Task,
        result: ExecutionResult,
        state: SharedWorkflowState,
        *args: Any,
        **kwargs: Any,
    ) -> SupervisorValidation:
        """
        Main execution loop for Supervisor Agent.
        Validates task results and returns SupervisorValidation.
        """
        return self.validate_task(task, result, state)

    def validate_task(
        self,
        task: Task,
        result: ExecutionResult,
        state: SharedWorkflowState,
    ) -> SupervisorValidation:
        """
        Validates task execution result and returns a SupervisorValidation report.
        Also updates the SharedWorkflowState accordingly.
        """
        logger.info(
            f"SupervisorAgent validating task: {task.task_id} ({task.task_name})"
        )

        # Use failure detector service to check for execution failures
        failure_report = self.failure_detector.check_failure(task, result, state)

        # Generate checks dictionary
        checks = {
            "worker_success": result.success,
            "no_tool_error": not self.failure_detector._is_tool_error(result),
            "expected_output_present": not self.failure_detector._is_output_missing(
                task, result
            ),
            "artifacts_valid": self.failure_detector._check_artifact_failures(
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

        if failure_report:
            logger.error(
                f"SupervisorAgent validation failed for task {task.task_id}: "
                f"{failure_report.message}"
            )
            issues = [failure_report.message]
            validation = SupervisorValidation(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                is_valid=False,
                checks=checks,
                issues=issues,
            )

            # Update task status and workflow state
            task.status = TaskStatus.FAILED
            if task.task_id in state.running_tasks:
                state.running_tasks.remove(task.task_id)
            if task.task_id not in state.failed_tasks:
                state.failed_tasks.append(task.task_id)
        else:
            logger.info(
                f"SupervisorAgent validation succeeded for task: {task.task_id}"
            )
            validation = SupervisorValidation(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                is_valid=True,
                checks=checks,
                issues=[],
            )

            # Update task status and workflow state
            task.status = TaskStatus.COMPLETED
            if task.task_id in state.running_tasks:
                state.running_tasks.remove(task.task_id)
            if task.task_id not in state.completed_tasks:
                state.completed_tasks.append(task.task_id)

        # Emit events to Event Bus if available
        if self.event_bus:
            # We will use the publish method asynchronously in fire-and-forget style
            # or log if it fails.
            import asyncio

            from app.core.events.models import Event, EventType

            event_type = (
                EventType.TASK_COMPLETED
                if validation.is_valid
                else EventType.TASK_FAILED
            )
            event = Event(
                event_type=event_type,
                workflow_id=str(task.workflow_id),
                task_id=str(task.task_id),
                source_component="SupervisorAgent",
                payload={
                    "validation_id": str(validation.validation_id),
                    "is_valid": validation.is_valid,
                    "issues": validation.issues,
                },
            )
            try:
                # Use running loop or create a task
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.event_bus.publish(event))
                else:
                    loop.run_until_complete(self.event_bus.publish(event))
            except Exception as exc:
                logger.warning(f"Could not publish supervisor validation event: {exc}")

        return validation
