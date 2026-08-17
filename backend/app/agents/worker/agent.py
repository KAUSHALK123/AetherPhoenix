import logging
import time
from typing import Any, Dict

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task, TaskStatus
from shared.contracts.tool import ToolState

from app.core.exceptions import PermissionDeniedException
from app.core.logging.execution_logger import WorkerExecutionLogger
from app.core.permissions.manager import PermissionManager
from app.runtime.interfaces import AgentRegistration, BaseAgent
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class WorkerAgent(BaseAgent):
    """
    Worker Agent responsible for receiving executable tasks from the Execution Engine
    and executing them using registered tools.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        permission_manager: PermissionManager | None = None,
    ):
        self.tool_registry = tool_registry
        self.permission_manager = permission_manager
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

        Validates the task, resolves the required tool, enforces permissions,
        delegates execution to the registered Tool Adapter, and logs all phases.
        """
        logger.info(f"WorkerAgent executing task: {task.task_id} ({task.task_name})")

        exec_logger = WorkerExecutionLogger.from_task(
            task=task,
            workflow_id=task.workflow_id,
            correlation_id=str(task.task_id),
        )

        start_time = time.time()
        logs_captured = []

        # 1. Record Task Start
        exec_logger.log_task_start(inputs={})
        logs_captured.append(f"Task '{task.task_name}' execution started")

        try:
            # 2. Validation
            if not task.required_tool:
                raise ValueError("Task is missing 'required_tool'")

            # 3. Tool Resolution
            tool_name = task.required_tool
            exec_logger.log_tool_selected(tool_name=tool_name)

            tool = self.tool_registry.get(tool_name)
            if not tool:
                raise ValueError(f"Tool '{tool_name}' not found in registry")

            if tool.status != ToolState.READY:
                raise ValueError(
                    f"Tool '{tool_name}' is not ready (Status: {tool.status.value})"
                )

            adapter = self._adapters.get(tool.adapter)
            if not adapter:
                raise ValueError(
                    f"Tool adapter '{tool.adapter}' is not registered in WorkerAgent"
                )

            # 4. Permission Verification
            if self.permission_manager and tool.required_permissions:
                for perm_str in tool.required_permissions:
                    try:
                        perm_type = PermissionType(perm_str.upper())
                    except ValueError:
                        logger.warning(f"Unknown permission type: {perm_str}")
                        continue

                    is_approved = await self.permission_manager.check_permission(
                        action=f"Execute tool {tool_name}",
                        permission_type=perm_type,
                        context={"task_id": str(task.task_id)},
                    )
                    if not is_approved:
                        raise PermissionDeniedException(
                            f"Permission denied for {perm_type.value}"
                        )

            # 5. Execute Tool via Adapter
            task.status = TaskStatus.RUNNING
            tool_start_time = time.time()
            exec_logger.log_tool_start(tool_name=tool_name, inputs={})

            try:
                result = await adapter.execute(task)

                tool_duration_ms = (time.time() - tool_start_time) * 1000.0
                exec_logger.log_tool_complete(
                    tool_name=tool_name,
                    duration_ms=tool_duration_ms,
                    outputs=result.output or {},
                )

                # Append tool logs to captured logs if present
                if result.logs:
                    logs_captured.extend(result.logs)

            except Exception as tool_exc:
                tool_duration_ms = (time.time() - tool_start_time) * 1000.0
                err_code = getattr(tool_exc, "code", "TOOL_EXECUTION_ERROR")
                err_msg = str(tool_exc)

                exec_logger.log_tool_failure(
                    tool_name=tool_name,
                    duration_ms=tool_duration_ms,
                    error_code=str(err_code),
                    error_message=err_msg,
                )
                raise tool_exc

            # 6. Finalize Task
            total_duration_ms = (time.time() - start_time) * 1000.0
            if result.metrics.execution_time_ms == 0.0:
                result.metrics.execution_time_ms = total_duration_ms

            if result.success:
                exec_logger.log_task_complete(
                    duration_ms=total_duration_ms,
                    outputs=result.output or {},
                )
                logs_captured.append(f"Task '{task.task_name}' completed successfully")
            else:
                exec_logger.log_task_failure(
                    duration_ms=total_duration_ms,
                    error_code=result.error.error_code if result.error else "FAILED",
                    error_message=(
                        result.error.error_message if result.error else "Task failed"
                    ),
                )
                logs_captured.append(f"Task '{task.task_name}' failed")

            result.logs = logs_captured
            return result

        except PermissionDeniedException as pde:
            duration_ms = (time.time() - start_time) * 1000.0
            exec_logger.log_task_failure(
                duration_ms=duration_ms,
                error_code="PERMISSION_DENIED",
                error_message=pde.message,
            )
            logs_captured.append(f"Task failed: {pde.message}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="PERMISSION_DENIED",
                    error_message=pde.message,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms),
            )
        except Exception as e:
            # Handle all exceptions without crashing the runtime
            logger.error(
                f"Execution failed for task {task.task_id}: {str(e)}", exc_info=True
            )
            duration_ms = (time.time() - start_time) * 1000.0

            error_code = "EXECUTION_FAILED"
            exec_logger.log_task_failure(
                duration_ms=duration_ms,
                error_code=error_code,
                error_message=str(e),
            )
            logs_captured.append(f"Task failed with error: {str(e)}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code=error_code,
                    error_message=str(e),
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms),
            )

    async def reexecute(
        self,
        request: Any,
        state: Any,
        *args: Any,
        **kwargs: Any,
    ) -> ExecutionResult:
        """
        Executes a controlled re-execution request for a task.
        Revalidates permissions, applies recovery context, and delegates to execute().
        """
        task_id = getattr(request, "task_id", None)
        if not task_id:
            raise ValueError("Invalid re-execution request: missing task_id")

        task = state.tasks.get(task_id) if hasattr(state, "tasks") else None
        if not task:
            raise ValueError(f"Task {task_id} not found in workflow state")

        attempt_id = getattr(request, "attempt_id", None)
        if attempt_id:
            task.current_attempt_id = attempt_id

        mod_params = getattr(request, "modified_parameters", {})
        if mod_params and "updated_tool" in mod_params:
            task.required_tool = mod_params["updated_tool"]

        logger.info(
            f"WorkerAgent re-executing task {task.task_id} "
            f"(Attempt #{getattr(request, 'attempt_number', 1)})"
        )
        return await self.execute(task, *args, **kwargs)
