import logging
import time
from typing import Any

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.export import ExportFormat, ExportRequest
from shared.contracts.task import Task

from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.services.artifact_storage import ArtifactStorageService
from app.tools.adapter import BaseToolAdapter
from app.tools.export.engine import ExportEngine, ExportError

logger = logging.getLogger(__name__)


class ExportToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging the WorkerAgent and ExportEngine.
    Executes artifact export/conversion tasks and returns structured ExecutionResults.
    """

    def __init__(
        self,
        engine: ExportEngine | None = None,
        permission_manager: PermissionManager | None = None,
        artifact_storage_service: ArtifactStorageService | None = None,
    ) -> None:
        self.permission_manager = permission_manager
        self.artifact_storage_service = artifact_storage_service
        self.engine = engine or ExportEngine(
            permission_manager=permission_manager,
            artifact_storage_service=artifact_storage_service,
        )

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes an artifact export task.

        Args:
            task: Task contract to execute.

        Returns:
            ExecutionResult containing export outputs, artifact references, and logs.
        """
        start_time = time.time()
        logs_captured = [f"ExportToolAdapter executing task '{task.task_name}'"]

        inputs: dict[str, Any] = (
            task.inputs.copy() if hasattr(task, "inputs") and task.inputs else {}
        )

        # Resolve target format
        fmt_str = (
            inputs.get("target_format")
            or inputs.get("export_format")
            or inputs.get("format")
            or "pdf"
        )
        try:
            target_format = ExportFormat(str(fmt_str).lower())
        except ValueError:
            target_format = ExportFormat.PDF

        # Resolve source artifact / filepath
        source_artifact_id = inputs.get("source_artifact_id") or inputs.get(
            "artifact_id"
        )
        source_filepath = (
            inputs.get("source_filepath")
            or inputs.get("filepath")
            or inputs.get("image_path")
            or inputs.get("path")
            or task.artifact_location
        )
        output_path = inputs.get("output_path")
        title = inputs.get("title") or task.task_name

        request = ExportRequest(
            workflow_id=task.workflow_id,
            task_id=task.task_id,
            target_format=target_format,
            source_artifact_id=source_artifact_id,
            source_filepath=source_filepath,
            output_path=output_path,
            title=title,
            metadata=inputs,
        )

        try:
            export_result = await self.engine.export(request)
            duration_ms = (time.time() - start_time) * 1000.0

            logs_captured.append(
                f"Successfully exported artifact '{export_result.name}' "
                f"to format {target_format.value}"
            )

            # Reconstruct Artifact object for result payload
            exported_art = Artifact(
                artifact_id=export_result.artifact_id,
                workflow_id=export_result.workflow_id,
                task_id=export_result.task_id,
                name=export_result.name,
                filepath=export_result.filepath,
                artifact_type=ExportEngine.FORMAT_MAP.get(
                    target_format, ArtifactType.REPORTS
                ),
                size_bytes=export_result.size_bytes,
                checksum=export_result.checksum,
                created_at=export_result.created_at,
                metadata=export_result.metadata,
            )

            output = export_result.model_dump()

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output,
                artifacts=[exported_art],
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

        except ExportError as exp_err:
            duration_ms = (time.time() - start_time) * 1000.0
            err_msg = str(exp_err)
            logs_captured.append(f"Export error: {err_msg}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="EXPORT_FAILED",
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            err_code = getattr(e, "code", type(e).__name__)
            err_msg = str(e)
            logs_captured.append(f"Export execution failed: {err_msg}")

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
