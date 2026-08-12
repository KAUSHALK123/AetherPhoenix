import logging
import time
from typing import Any, Dict

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task, TaskStatus
from shared.contracts.tool import ToolState

from app.runtime.interfaces import AgentRegistration, BaseAgent
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class WorkerAgent(BaseAgent):
    """
    Worker Agent responsible for receiving executable tasks from the Execution Engine
    and executing them using registered tools.
    """

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self._adapters: Dict[str, BaseToolAdapter] = {}

    def register_adapter(self, adapter_name: str, adapter: BaseToolAdapter) -> None:
        """Registers a tool adapter implementation."""
        self._adapters[adapter_name] = adapter

    @property
    def registration(self) -> AgentRegistration:
        """Returns the registration metadata for this agent."""
        return AgentRegistration(
            name="WorkerAgent",
            version="1.0.0",
            description="Executes workflow tasks using registered tools.",
        )

    async def initialize(self) -> None:
        """Lifecycle hook: Called when the agent is registered."""
        logger.info("WorkerAgent initialized.")

    async def shutdown(self) -> None:
        """Lifecycle hook: Called when the kernel shuts down."""
        logger.info("WorkerAgent shut down.")

    async def execute(self, task: Task, *args: Any, **kwargs: Any) -> ExecutionResult:
        """
        Main execution loop for the Worker Agent.

        Validates the task, resolves the required tool, and delegates execution
        to the registered Tool Adapter.
        """
        logger.info(f"WorkerAgent executing task: {task.task_id} ({task.task_name})")
        start_time = time.time()

        try:
            # 1. Validation
            if not task.required_tool:
                raise ValueError("Task is missing 'required_tool'")

            # 2. Tool Resolution
            tool = self.tool_registry.get(task.required_tool)
            if not tool:
                raise ValueError(f"Tool '{task.required_tool}' not found in registry")

            if tool.status != ToolState.READY:
                raise ValueError(
                    f"Tool '{task.required_tool}' is not ready (Status: {tool.status.value})"  # noqa: E501
                )

            # 3. Get Adapter
            adapter = self._adapters.get(tool.adapter)
            if not adapter:
                raise ValueError(
                    f"Tool adapter '{tool.adapter}' is not registered in WorkerAgent"  # noqa: E501
                )

            # 4. State Update (Task tracking)
            task.status = TaskStatus.RUNNING

            # 5. Delegate Execution
            result = await adapter.execute(task)

            # Ensure metrics exist and execution time is populated if not set by adapter
            if result.metrics.execution_time_ms == 0.0:
                duration_ms = (time.time() - start_time) * 1000
                result.metrics.execution_time_ms = duration_ms

            return result

        except Exception as e:
            # Handle all exceptions without crashing the runtime
            logger.error(
                f"Execution failed for task {task.task_id}: {str(e)}", exc_info=True
            )
            duration_ms = (time.time() - start_time) * 1000
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="EXECUTION_FAILED",
                    error_message=str(e),
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms),
            )
