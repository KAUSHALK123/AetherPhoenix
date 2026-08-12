import time
from typing import Any, Callable
from uuid import UUID, uuid4

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task
from shared.contracts.tool import ToolState

from app.core.exceptions import PermissionDeniedException
from app.core.logging.execution_logger import WorkerExecutionLogger
from app.tools.registry import ToolRegistry


class WorkerTaskExecutor:
    """
    Standard Execution Engine for Worker Agent operations.
    Executes tasks deterministically and emits structured execution logs
    via WorkerExecutionLogger.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        permission_manager: Any | None = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.permission_manager = permission_manager

    def execute_task(
        self,
        task: Task,
        payload: dict[str, Any] | None = None,
        tool_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        workflow_id: UUID | None = None,
        correlation_id: str | None = None,
    ) -> ExecutionResult:
        """
        Executes a worker task, tracking granular execution phases, tools, duration,
        status, and correlation IDs.

        Args:
            task: Task contract to execute.
            payload: Optional input parameters for execution.
            tool_fn: Optional callable adapter to run the resolved tool logic.
            workflow_id: Optional active workflow ID.
            correlation_id: Optional correlation trace ID.

        Returns:
            ExecutionResult containing execution status, output, metrics, and logs.
        """
        active_wf_id = workflow_id or task.workflow_id
        corr_id = correlation_id or str(uuid4())
        task_inputs = payload.copy() if payload else {}

        exec_logger = WorkerExecutionLogger.from_task(
            task=task,
            workflow_id=active_wf_id,
            correlation_id=corr_id,
        )

        start_time = time.time()
        logs_captured = []

        # Step 1: Record Task Start
        exec_logger.log_task_start(inputs=task_inputs)
        logs_captured.append(f"Task '{task.task_name}' execution started")

        # Step 2: Tool Resolution
        tool_name = task.required_tool or "default_tool"
        exec_logger.log_tool_selected(tool_name=tool_name)

        registered_tool = self.tool_registry.get(tool_name)
        if not registered_tool:
            duration_ms = (time.time() - start_time) * 1000.0
            err_msg = f"Tool '{tool_name}' is not registered in ToolRegistry."
            exec_logger.log_task_failure(
                duration_ms=duration_ms,
                error_code="TOOL_NOT_FOUND",
                error_message=err_msg,
            )
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_wf_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="TOOL_NOT_FOUND",
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(
                    execution_time_ms=duration_ms,
                    exit_code=1,
                ),
            )

        if registered_tool.status == ToolState.DISABLED:
            duration_ms = (time.time() - start_time) * 1000.0
            err_msg = f"Tool '{tool_name}' is currently disabled."
            exec_logger.log_task_failure(
                duration_ms=duration_ms,
                error_code="TOOL_DISABLED",
                error_message=err_msg,
            )
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_wf_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="TOOL_DISABLED",
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(
                    execution_time_ms=duration_ms,
                    exit_code=1,
                ),
            )

        # Step 3: Permission Verification
        if self.permission_manager:
            try:
                if hasattr(self.permission_manager, "enforce_permission"):
                    self.permission_manager.enforce_permission(
                        PermissionType.FILE_SYSTEM, active_wf_id
                    )
            except PermissionDeniedException as pde:
                duration_ms = (time.time() - start_time) * 1000.0
                exec_logger.log_task_failure(
                    duration_ms=duration_ms,
                    error_code="PERMISSION_DENIED",
                    error_message=pde.message,
                )
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=active_wf_id,
                    success=False,
                    logs=logs_captured,
                    error=TaskError(
                        error_code="PERMISSION_DENIED",
                        error_message=pde.message,
                        is_recoverable=False,
                    ),
                    metrics=ExecutionMetrics(
                        execution_time_ms=duration_ms,
                        exit_code=1,
                    ),
                )

        # Step 4: Execute Tool
        tool_start_time = time.time()
        exec_logger.log_tool_start(tool_name=tool_name, inputs=task_inputs)

        try:
            if tool_fn:
                output_result = tool_fn(task_inputs)
            else:
                output_result = {"status": "EXECUTED", "tool": tool_name}

            tool_duration_ms = (time.time() - tool_start_time) * 1000.0
            exec_logger.log_tool_complete(
                tool_name=tool_name,
                duration_ms=tool_duration_ms,
                outputs=output_result,
            )

            total_duration_ms = (time.time() - start_time) * 1000.0
            exec_logger.log_task_complete(
                duration_ms=total_duration_ms,
                outputs=output_result,
            )
            logs_captured.append(f"Task '{task.task_name}' completed successfully")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_wf_id,
                success=True,
                output=output_result,
                metrics=ExecutionMetrics(
                    execution_time_ms=total_duration_ms,
                    exit_code=0,
                ),
                logs=logs_captured,
            )

        except Exception as exc:
            tool_duration_ms = (time.time() - tool_start_time) * 1000.0
            err_code = getattr(exc, "code", "TOOL_EXECUTION_ERROR")
            err_msg = str(exc)

            exec_logger.log_tool_failure(
                tool_name=tool_name,
                duration_ms=tool_duration_ms,
                error_code=str(err_code),
                error_message=err_msg,
            )

            total_duration_ms = (time.time() - start_time) * 1000.0
            exec_logger.log_task_failure(
                duration_ms=total_duration_ms,
                error_code=str(err_code),
                error_message=err_msg,
            )
            logs_captured.append(f"Task '{task.task_name}' failed: {err_msg}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_wf_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code=str(err_code),
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(
                    execution_time_ms=total_duration_ms,
                    exit_code=1,
                ),
            )
