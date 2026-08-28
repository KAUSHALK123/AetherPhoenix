import logging
import time
from typing import Any, Dict, Optional

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.ocr import OCRRequest
from shared.contracts.task import Task

from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.services.artifact_storage import ArtifactStorageService
from app.tools.adapter import BaseToolAdapter
from app.tools.ocr.engine import OCREngine, OCRError

logger = logging.getLogger(__name__)


class OCRToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging the WorkerAgent and OCREngine.
    Executes visual OCR text extraction tasks and returns structured ExecutionResults.
    """

    def __init__(
        self,
        engine: Optional[OCREngine] = None,
        permission_manager: Optional[PermissionManager] = None,
        artifact_storage_service: Optional[ArtifactStorageService] = None,
    ) -> None:
        self.permission_manager = permission_manager
        self.artifact_storage_service = artifact_storage_service
        self.engine = engine or OCREngine(
            permission_manager=permission_manager,
            artifact_storage_service=artifact_storage_service,
        )

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes an OCR task.

        Args:
            task: Task contract to execute.

        Returns:
            ExecutionResult with success status, extracted outputs, logs, and metrics.
        """
        start_time = time.time()
        logs_captured = [f"OCRToolAdapter executing task '{task.task_name}'"]

        inputs: Dict[str, Any] = (
            task.inputs.copy() if hasattr(task, "inputs") and task.inputs else {}
        )

        # Resolve filepath from inputs
        filepath = (
            inputs.get("filepath")
            or inputs.get("image_path")
            or inputs.get("artifact_path")
            or inputs.get("path")
            or inputs.get("source_path")
            or inputs.get("file")
        )

        if not filepath:
            # Fallback check on task description or artifact_location
            if task.artifact_location:
                filepath = task.artifact_location
            else:
                duration_ms = (time.time() - start_time) * 1000.0
                err_msg = "OCR task missing required 'filepath' or 'image_path' input."
                logs_captured.append(f"Task failed: {err_msg}")
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=False,
                    logs=logs_captured,
                    error=TaskError(
                        error_code="INVALID_INPUT",
                        error_message=err_msg,
                        is_recoverable=False,
                    ),
                    metrics=ExecutionMetrics(
                        execution_time_ms=duration_ms, exit_code=1
                    ),
                )

        language = inputs.get("language", "eng")
        extract_boxes = bool(inputs.get("extract_boxes", False))

        request = OCRRequest(
            filepath=str(filepath),
            language=language,
            extract_boxes=extract_boxes,
            workflow_id=task.workflow_id,
            task_id=task.task_id,
            metadata=inputs,
        )

        try:
            ocr_result = await self.engine.extract_text(request)
            duration_ms = (time.time() - start_time) * 1000.0

            logs_captured.append(
                f"OCR text extraction completed successfully for '{filepath}'"
            )

            output = ocr_result.model_dump()
            artifacts = []

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output,
                artifacts=artifacts,
                logs=logs_captured,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=0),
            )

        except PermissionDeniedException as pde:
            duration_ms = (time.time() - start_time) * 1000.0
            err_msg = str(pde)
            logs_captured.append(f"Permission denied: {err_msg}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="PERMISSION_DENIED",
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )

        except FileNotFoundError as fnfe:
            duration_ms = (time.time() - start_time) * 1000.0
            err_msg = str(fnfe)
            logs_captured.append(f"File not found: {err_msg}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="FILE_NOT_FOUND",
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )

        except OCRError as ocr_err:
            duration_ms = (time.time() - start_time) * 1000.0
            err_msg = str(ocr_err)
            logs_captured.append(f"OCR execution error: {err_msg}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="OCR_EXTRACTION_FAILED",
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            err_code = getattr(e, "code", type(e).__name__)
            err_msg = str(e)
            logs_captured.append(f"OCR execution failed: {err_msg}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code=str(err_code),
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )
