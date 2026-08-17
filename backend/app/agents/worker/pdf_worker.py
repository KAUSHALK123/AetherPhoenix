import time
from typing import Any, Dict, Optional
from uuid import UUID

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.pdf import PDFDocumentInput
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task
from shared.contracts.tool import ToolState

from app.core.exceptions import (
    PermissionDeniedException,
)
from app.core.logging import get_logger
from app.core.permissions import PermissionManager
from app.tools.pdf.generator import PDFGenerator
from app.tools.pdf.tool import PDFToolAdapter
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class PDFWorkerAgent:
    """
    Worker Agent responsible for executing PDF generation tasks without reasoning.
    Executes compiled tasks via PDFToolAdapter.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        permission_manager: Optional[PermissionManager] = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.permission_manager = permission_manager
        self.adapter = PDFToolAdapter(permission_manager=permission_manager)

    def execute_task(
        self,
        task: Task,
        payload: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[UUID] = None,
    ) -> ExecutionResult:
        """
        Executes a compiled PDF task and returns an ExecutionResult.

        Args:
            task: The compiled Task object to execute.
            payload: Optional dictionary payload with PDF creation parameters.
            workflow_id: The active workflow ID (overrides task.workflow_id).

        Returns:
            ExecutionResult containing execution status, artifacts, and metrics.
        """
        start_time = time.time()
        active_workflow_id = workflow_id or task.workflow_id
        logs = []
        logs.append(
            f"Received PDF task {task.task_id} ('{task.task_name}') for workflow "
            f"{active_workflow_id}"
        )
        logger.info(
            f"PDFWorkerAgent executing task {task.task_id} (tool: {task.required_tool})"
        )

        # Step 1: Tool Resolution via ToolRegistry
        tool_name = task.required_tool or "pdf_generator"
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
                logs.append("Performing FILE_SYSTEM permission check")
                self.permission_manager.enforce_permission(
                    PermissionType.FILE_SYSTEM, active_workflow_id
                )
            except PermissionDeniedException as pde:
                err_msg = f"Permission denied for PDF execution: {pde.message}"
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

        # Step 3: Parse Payload & Execute PDF Tool Adapter
        try:
            task_payload = payload.copy() if payload else {}
            if "workflow_id" not in task_payload:
                task_payload["workflow_id"] = str(active_workflow_id)
            if "task_id" not in task_payload:
                task_payload["task_id"] = str(task.task_id)

            input_data = PDFDocumentInput.model_validate(task_payload)
            pdf_result = self.adapter.execute(
                input_data, workflow_id=active_workflow_id
            )

            # Step 4: Construct System Artifact
            generator = PDFGenerator(permission_manager=self.permission_manager)
            artifact = generator.create_artifact(
                pdf_result, workflow_id=active_workflow_id, task_id=task.task_id
            )

            execution_duration_ms = (time.time() - start_time) * 1000.0
            logs.append(f"PDF generated successfully at {pdf_result.filepath}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_workflow_id,
                success=True,
                output=pdf_result.model_dump(mode="json"),
                artifacts=[artifact],
                metrics=ExecutionMetrics(
                    execution_time_ms=execution_duration_ms,
                    exit_code=0,
                ),
                logs=logs,
            )

        except Exception as exc:
            execution_duration_ms = (time.time() - start_time) * 1000.0
            err_msg = f"PDF task execution failed: {str(exc)}"
            logs.append(err_msg)
            logger.error(err_msg, exc_info=True)

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=active_workflow_id,
                success=False,
                logs=logs,
                error=TaskError(
                    error_code="PDF_EXECUTION_FAILED",
                    error_message=str(exc),
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(
                    execution_time_ms=execution_duration_ms,
                    exit_code=1,
                ),
            )
