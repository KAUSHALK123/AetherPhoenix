import logging
import time
from typing import Any, Dict, Optional

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.services.artifact_storage import ArtifactStorageService
from app.tools.adapter import BaseToolAdapter
from app.tools.file_explorer.executor import FileExplorerExecutor
from app.tools.file_explorer.models import (
    CreateFolderRequest,
    DetectExistenceRequest,
    FileMetadataRequest,
    OpenFileRequest,
    OpenFolderRequest,
    RevealArtifactRequest,
)

logger = logging.getLogger(__name__)


class FileExplorerToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging the WorkerAgent and FileExplorerExecutor.
    Executes File Explorer automation tasks and produces structured ExecutionResults.
    """

    def __init__(
        self,
        executor: Optional[FileExplorerExecutor] = None,
        permission_manager: Optional[PermissionManager] = None,
        artifact_storage_service: Optional[ArtifactStorageService] = None,
    ) -> None:
        self.permission_manager = permission_manager
        self.executor = executor or FileExplorerExecutor(
            permission_manager=permission_manager,
            artifact_storage_service=artifact_storage_service,
        )

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a File Explorer task.

        Args:
            task: Task contract to execute.

        Returns:
            ExecutionResult with status, outputs, logs, and execution metrics.
        """
        start_time = time.time()
        logs_captured = [f"FileExplorerToolAdapter executing task '{task.task_name}'"]

        inputs: Dict[str, Any] = (
            task.inputs.copy() if hasattr(task, "inputs") and task.inputs else {}
        )
        action = inputs.get("action")

        # Action resolution heuristics
        if not action:
            task_name_lower = task.task_name.lower()
            if "reveal" in task_name_lower or "navigate" in task_name_lower:
                action = "reveal_artifact"
            elif "folder" in task_name_lower and "create" in task_name_lower:
                action = "create_folder"
            elif "folder" in task_name_lower and "open" in task_name_lower:
                action = "open_folder"
            elif "open" in task_name_lower:
                action = "open_file"
            elif "exist" in task_name_lower or "detect" in task_name_lower:
                action = "detect_existence"
            elif "metadata" in task_name_lower:
                action = "get_file_metadata"
            else:
                action = "reveal_artifact"

        logs_captured.append(f"Resolved file explorer action: {action}")

        try:
            if action in ("open_folder", "folder"):
                req = OpenFolderRequest(path=inputs.get("path", "."))
                res = await self.executor.open_folder(req)
                output = res.model_dump()

            elif action in ("open_file", "file", "open"):
                req = OpenFileRequest(path=inputs.get("path", "."))
                res = await self.executor.open_file(req)
                output = res.model_dump()

            elif action in (
                "reveal_artifact",
                "reveal",
                "navigate_to_artifact",
                "navigate",
            ):
                req = RevealArtifactRequest(
                    artifact_id=inputs.get("artifact_id"),
                    artifact_name=inputs.get("artifact_name") or inputs.get("name"),
                    filepath=inputs.get("filepath") or inputs.get("path"),
                )
                res = await self.executor.reveal_artifact(
                    request=req, workflow_id=task.workflow_id
                )
                output = res.model_dump()

            elif action in (
                "create_folder",
                "create_directory",
                "mkdir",
                "make_folder",
            ):
                req = CreateFolderRequest(
                    path=inputs.get("path", "new_folder"),
                    create_parents=inputs.get("create_parents", True),
                )
                res = await self.executor.create_folder(
                    request=req,
                    workflow_id=task.workflow_id,
                    task_id=task.task_id,
                )
                output = res.model_dump()

            elif action in ("detect_existence", "exists", "check_existence"):
                req = DetectExistenceRequest(path=inputs.get("path", "."))
                res = await self.executor.detect_existence(req)
                output = res.model_dump()

            elif action in ("get_file_metadata", "metadata", "file_metadata"):
                req = FileMetadataRequest(path=inputs.get("path", "."))
                res = await self.executor.get_file_metadata(req)
                output = res.model_dump()

            else:
                raise ValueError(f"Unsupported file explorer action: {action}")

            duration_ms = (time.time() - start_time) * 1000.0
            logs_captured.append(
                f"File explorer action '{action}' completed successfully"
            )

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output,
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

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            err_code = getattr(e, "code", type(e).__name__)
            err_msg = str(e)
            logs_captured.append(f"File explorer execution failed: {err_msg}")

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
