import logging
from typing import Any, Optional

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionResult,
    SupervisorDecision,
    SupervisorValidation,
)
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

from app.agents.supervisor.failure_detector import FailureDetectorService
from app.core.events.bus import EventBus
from app.engine.monitor import WorkflowProgressMonitor
from app.engine.validator import OutputValidationService
from app.runtime.interfaces import AgentRegistration, BaseAgent

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent responsible for validating Worker execution results,
    updating workflow state, and determining final task outcomes.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        failure_detector: Optional[FailureDetectorService] = None,
    ) -> None:
        self.event_bus = event_bus
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
        result: ExecutionResult,
        state: SharedWorkflowState,
        *args: Any,
        **kwargs: Any,
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
