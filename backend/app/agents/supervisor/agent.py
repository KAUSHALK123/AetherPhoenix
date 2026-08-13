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

from app.core.events.bus import EventBus
from app.engine.monitor import WorkflowProgressMonitor
from app.runtime.interfaces import AgentRegistration, BaseAgent

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent responsible for validating Worker execution results,
    updating workflow state, and determining final task outcomes.
    """

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self.monitor = WorkflowProgressMonitor()

    @property
    def registration(self) -> AgentRegistration:
        """Returns the registration metadata for this agent."""
        return AgentRegistration(
            name="SupervisorAgent",
            version="1.0.0",
            description="Observes and validates Worker execution results.",
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

        checks = {}
        issues = []
        is_valid = True

        # 1. Check basic execution success
        checks["execution_success"] = result.success
        if not result.success:
            is_valid = False
            error_msg = result.error.error_message if result.error else "Unknown"
            issues.append(f"Worker reported failure: {error_msg}")

        # 2. Check outputs against success criteria (heuristic for now)
        checks["output_matches_criteria"] = True
        if result.success and task.success_criteria:
            # Placeholder for actual LLM-based or strict validation
            if not result.output and not result.artifacts:
                checks["output_matches_criteria"] = False
                is_valid = False
                issues.append("Task succeeded but produced no output or artifacts.")

        # Determine decision
        if is_valid:
            decision = SupervisorDecision.PASSED
        else:
            decision = SupervisorDecision.FAILED
            # Here we could also determine NEEDS_REVIEW or BLOCKED for complex cases

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
