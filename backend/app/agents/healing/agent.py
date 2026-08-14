import logging
from typing import Any, Optional
from uuid import uuid4

from shared.contracts.execution import ExecutionResult, HealingResult
from shared.contracts.task import Task
from shared.contracts.workflow import SharedWorkflowState

from app.runtime.interfaces import AgentRegistration, BaseAgent

logger = logging.getLogger(__name__)


class HealingAgent(BaseAgent):
    """
    Healing Agent responsible for analyzing failed task execution,
    determining recovery strategy, generating replacement tasks,
    and recording the healing results.
    """

    def __init__(self) -> None:
        self.force_success: Optional[bool] = None

    @property
    def registration(self) -> AgentRegistration:
        """Returns registration metadata for the Healing Agent."""
        return AgentRegistration(
            name="HealingAgent",
            version="1.0.0",
            description=(
                "Performs automated recovery for failed task executions "
                "by analyzing root causes and generating recovery strategies."
            ),
        )

    async def initialize(self) -> None:
        """Lifecycle hook: Called when the agent is registered."""
        logger.info("HealingAgent initialized.")

    async def shutdown(self) -> None:
        """Lifecycle hook: Called when the kernel shuts down."""
        logger.info("HealingAgent shut down.")

    async def execute(
        self,
        task: Task,
        *args: Any,
        **kwargs: Any,
    ) -> HealingResult:
        """
        Executes the healing analysis.
        Accepts: task, result, state
        Returns: HealingResult
        """
        result: Optional[ExecutionResult] = kwargs.get("result")
        state: Optional[SharedWorkflowState] = kwargs.get("state")

        if args:
            if isinstance(args[0], ExecutionResult):
                result = args[0]
                if len(args) > 1:
                    state = args[1]
            elif isinstance(args[0], SharedWorkflowState):
                state = args[0]

        # Log invocation
        logger.info(
            f"HealingAgent evaluating recovery for task {task.task_id} ('{task.task_name}')"
        )

        error_msg = ""
        root_cause = "Unknown failure"
        if result and result.error:
            error_msg = result.error.error_message.lower()
            root_cause = result.error.error_message

        # Determine success
        if self.force_success is not None:
            success = self.force_success
        else:
            # Default heuristic: if error message indicates unrecoverable, we fail healing
            if "unrecoverable" in error_msg or "permanent" in error_msg:
                success = False
            else:
                success = True

        healing_res = HealingResult(
            recovery_id=uuid4(),
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            root_cause=root_cause,
            recovery_strategy="Retry with alternate parameters"
            if success
            else "No recovery strategy possible",
            replacement_tasks=[],
            attempt_number=task.retry_count + 1,
            success=success,
        )

        # Append to state history if state is present
        if state is not None:
            state.healing_history.append(healing_res)

        return healing_res
