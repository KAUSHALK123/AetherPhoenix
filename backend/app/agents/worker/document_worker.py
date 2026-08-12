import time
from typing import Any, Dict, Optional
from uuid import UUID

from shared.contracts.document import StructuredDocumentInput
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task
from shared.contracts.tool import ToolState

from app.core.exceptions import (
    PermissionDeniedException,
)
from app.core.logging import get_logger
from app.core.permissions import PermissionManager
from app.tools.document.generator import DocumentGenerator
from app.tools.document.tool import DocumentToolAdapter
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class DocumentWorkerAgent:
    """
    Worker Agent responsible for executing Document Generation tasks without reasoning.
    Executes compiled tasks via DocumentToolAdapter.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        permission_manager: Optional[PermissionManager] = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.permission_manager = permission_manager
        self.adapter = DocumentToolAdapter(permission_manager=permission_manager)

    def execute_task(
        self,
        task: Task,
        payload: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[UUID] = None,
    ) -> ExecutionResult:
        """
        Executes a compiled document generation task and returns an ExecutionResult.

        Args:
            task: The compiled Task object to execute.
            payload: Optional dictionary payload with document creation parameters.
            workflow_id: The active workflow ID (overrides task.workflow_id).

        Returns:
            ExecutionResult containing execution status, artifacts, and metrics.
        """
        start_time = time.time()
        active_workflow_id = workflow_id or task.workflow_id
        logs = []
        logs.append(
            f"Received Document task {task.task_id} ('{task.task_name}') for workflow "
            f"{active_workflow_id}"
        )
        logger.info(
            f"DocumentWorkerAgent executing task {task.task_id} "
            f"(tool: {task.required_tool})"
        )

        # Step 1: Tool Resolution via ToolRegistry
        tool_name = task.required_tool or "document_generator"
        registered_tool = self.tool_registry.get(tool_name)
        if not registered_tool:
            err_msg = f"Tool '{tool_name}' is not registered in ToolRegistry."
            logger.error(err_msg)
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_workflow_id,
                success=False,
                logs=logs,
                error=TaskError(
                    error_code="TOOL_NOT_FOUND",
                    error_message=err_msg,
                    is_recoverable=False,
                ),
            )

        if registered_tool.status == ToolState.DISABLED:
            err_msg = f"Tool '{tool_name}' is disabled."
            logger.error(err_msg)
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_workflow_id,
                success=False,
                logs=logs,
                error=TaskError(
                    error_code="TOOL_DISABLED",
                    error_message=err_msg,
                    is_recoverable=False,
                ),
            )

        # Step 2: Permission Check
        if self.permission_manager:
            try:
                logs.append("Performing permission check")
                for p in ["FILE_WRITE", "FILE_SYSTEM_WRITE", "FILE_SYSTEM"]:
                    try:
                        self.permission_manager.enforce_permission(
                            p, active_workflow_id
                        )
                        break
                    except Exception:
                        continue
                else:
                    self.permission_manager.enforce_permission(
                        "FILE_SYSTEM", active_workflow_id
                    )
            except PermissionDeniedException as pde:
                err_msg = f"Permission denied for document execution: {pde.message}"
                logs.append(err_msg)
                logger.warning(err_msg)
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=active_workflow_id,
                    success=False,
                    logs=logs,
                    error=TaskError(
                        error_code="PERMISSION_DENIED",
                        error_message=pde.message,
                        is_recoverable=False,
                    ),
                )

        # Step 3: Parse Payload & Execute Document Tool Adapter
        try:
            task_payload = payload.copy() if payload else {}
            if "workflow_id" not in task_payload:
                task_payload["workflow_id"] = str(active_workflow_id)
            if "task_id" not in task_payload:
                task_payload["task_id"] = str(task.task_id)

            input_data = StructuredDocumentInput.model_validate(task_payload)
            doc_result = self.adapter.execute(
                input_data, workflow_id=active_workflow_id
            )

            # Step 4: Construct System Artifact
            generator = DocumentGenerator(permission_manager=self.permission_manager)
            artifact = generator.create_artifact(
                doc_result, workflow_id=active_workflow_id, task_id=task.task_id
            )

            execution_duration_ms = (time.time() - start_time) * 1000.0
            logs.append(f"Document generated successfully at {doc_result.filepath}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_workflow_id,
                success=True,
                output=doc_result.model_dump(mode="json"),
                artifacts=[artifact],
                metrics=ExecutionMetrics(
                    execution_time_ms=execution_duration_ms,
                    exit_code=0,
                ),
                logs=logs,
            )

        except Exception as exc:
            execution_duration_ms = (time.time() - start_time) * 1000.0
            err_msg = f"Document task execution failed: {str(exc)}"
            logs.append(err_msg)
            logger.error(err_msg, exc_info=True)

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_workflow_id,
                success=False,
                logs=logs,
                error=TaskError(
                    error_code="DOCUMENT_EXECUTION_FAILED",
                    error_message=str(exc),
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(
                    execution_time_ms=execution_duration_ms,
                    exit_code=1,
                ),
            )
