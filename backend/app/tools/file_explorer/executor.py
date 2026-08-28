import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from shared.contracts.artifact import Artifact
from shared.contracts.permission import PermissionType

from app.core.config import get_config
from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.services.artifact_storage import (
    ArtifactStorageService,
    get_artifact_storage_service,
)
from app.tools.file_explorer.models import (
    CreateFolderRequest,
    DetectExistenceRequest,
    FileExplorerActionResult,
    FileMetadataRequest,
    FileMetadataResponse,
    OpenFileRequest,
    OpenFolderRequest,
    RevealArtifactRequest,
)

logger = logging.getLogger(__name__)


class FileExplorerExecutor:
    """
    Executor for File Explorer capabilities. Provides actual OS desktop actions
    for opening files/folders, revealing artifacts, creating directories with permission
    checks, detecting existence, and gathering file metadata.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        artifact_storage_service: Optional[ArtifactStorageService] = None,
    ):
        self.config = get_config()
        self.workspace_dir = Path(self.config.WORKSPACE_DIR).resolve()
        self.artifacts_dir = Path(self.config.ARTIFACTS_DIR).resolve()
        self.permission_manager = permission_manager or PermissionManager()
        self.artifact_storage_service = (
            artifact_storage_service or get_artifact_storage_service()
        )

    def _resolve_and_validate_path(self, path: str) -> Path:
        """
        Resolves a given path against workspace or artifacts directories
        and enforces path traversal security validation.
        """
        p = Path(path)
        if p.is_absolute():
            resolved_path = p.resolve()
        else:
            resolved_path = (self.workspace_dir / p).resolve()

        # Validate that path is within workspace_dir or artifacts_dir
        str_resolved = str(resolved_path)
        in_workspace = str_resolved.startswith(str(self.workspace_dir))
        in_artifacts = str_resolved.startswith(str(self.artifacts_dir))

        if not (in_workspace or in_artifacts):
            logger.error(
                f"Path validation failed: '{path}' resolves to '{resolved_path}' "
                f"outside permitted directories "
                f"({self.workspace_dir}, {self.artifacts_dir})"
            )
            raise ValueError(
                f"Access denied: path '{path}' is outside the permitted directories."
            )

        return resolved_path

        def _launch_os_open(self, target_path: Path) -> None:
        """Launches the target file or folder using OS default handler."""
        path_str = str(target_path)
        if sys.platform == "win32":
            if hasattr(os, "startfile"):
                os.startfile(path_str)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["explorer.exe", path_str])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path_str])
        else:
            subprocess.Popen(["xdg-open", path_str])

    def _launch_os_reveal(self, target_path: Path) -> None:
        """Reveals and highlights target file in native OS file explorer."""
        path_str = str(target_path)
        if sys.platform == "win32":
            subprocess.Popen(["explorer.exe", f"/select,{path_str}"])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path_str])
        else:
            folder_path = str(
                target_path.parent if target_path.is_file() else target_path
            )
            subprocess.Popen(["xdg-open", folder_path])


    async def open_folder(self, request: OpenFolderRequest) -> FileExplorerActionResult:
        """Visibly opens a directory in the OS file explorer."""
        target_path = self._resolve_and_validate_path(request.path)
        logger.info(f"Opening folder in OS file explorer: {target_path}")

        if not target_path.exists():
            raise FileNotFoundError(f"Folder not found: {request.path}")
        if not target_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {request.path}")

        self._launch_os_open(target_path)
        return FileExplorerActionResult(
            success=True,
            action="open_folder",
            target_path=str(target_path),
            message=f"Folder visibly opened in OS File Explorer: {target_path.name}",
        )

    async def open_file(self, request: OpenFileRequest) -> FileExplorerActionResult:
        """Visibly opens a file using the OS default associated application."""
        target_path = self._resolve_and_validate_path(request.path)
        logger.info(f"Opening file in OS desktop app: {target_path}")

        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {request.path}")
        if not target_path.is_file():
            raise IsADirectoryError(f"Path is a directory, not a file: {request.path}")

        self._launch_os_open(target_path)
        return FileExplorerActionResult(
            success=True,
            action="open_file",
            target_path=str(target_path),
            message=f"File visibly opened: {target_path.name}",
        )

    async def reveal_artifact(
        self,
        request: RevealArtifactRequest,
        workflow_id: Optional[UUID | str] = None,
    ) -> FileExplorerActionResult:
        """
        Locates an artifact by filepath, ID, or name via ArtifactStorageService
        and visibly reveals/highlights it in the OS File Explorer.
        """
        logger.info(
            f"Revealing artifact (id={request.artifact_id}, "
            f"name={request.artifact_name}, path={request.filepath})"
        )
        resolved_artifact: Optional[Artifact] = None
        target_path: Optional[Path] = None

        # 1. Direct filepath lookup
        if request.filepath:
            target_path = self._resolve_and_validate_path(request.filepath)

        # 2. Artifact ID lookup
        elif request.artifact_id:
            resolved_artifact = await self.artifact_storage_service.get_artifact(
                request.artifact_id
            )
            if resolved_artifact and resolved_artifact.filepath:
                target_path = Path(resolved_artifact.filepath).resolve()

        # 3. Artifact name lookup
        elif request.artifact_name:
            artifacts = await self.artifact_storage_service.list_artifacts(
                workflow_id=workflow_id
            )
            for art in artifacts:
                if art.name.lower() == request.artifact_name.lower():
                    resolved_artifact = art
                    target_path = Path(art.filepath).resolve()
                    break

        if not target_path or not target_path.exists():
            target_desc = (
                request.filepath
                or request.artifact_id
                or request.artifact_name
                or "Unknown"
            )
            logger.error(f"Artifact target missing on disk: {target_desc}")
            raise FileNotFoundError(f"Artifact file not found on disk: {target_desc}")

        self._launch_os_reveal(target_path)
        return FileExplorerActionResult(
            success=True,
            action="reveal_artifact",
            target_path=str(target_path),
            message=(
                f"Artifact '{target_path.name}' visibly revealed in OS File Explorer."
            ),
            metadata={
                "artifact_id": (
                    str(resolved_artifact.artifact_id) if resolved_artifact else None
                ),
                "artifact_name": (
                    resolved_artifact.name if resolved_artifact else target_path.name
                ),
                "filepath": str(target_path),
            },
        )

    async def create_folder(
        self,
        request: CreateFolderRequest,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> FileExplorerActionResult:
        """Creates a directory after verifying permission through PermissionManager."""
        target_path = self._resolve_and_validate_path(request.path)
        logger.info(f"Attempting to create folder: {target_path}")

        # Permission check
        if self.permission_manager:
            wf_str = str(workflow_id) if workflow_id else "file_explorer_workflow"
            t_str = str(task_id) if task_id else "create_folder_task"

            chk = self.permission_manager.check_permission(
                action=f"Create folder '{request.path}'",
                permission_type=PermissionType.FILE_SYSTEM_WRITE,
                workflow_id=wf_str,
                task_id=t_str,
                context={"path": str(target_path)},
            )
            if hasattr(chk, "__await__"):
                is_approved = await chk
            else:
                is_approved = bool(chk)

            if not is_approved:
                logger.warning(f"Create folder permission denied for {target_path}")
                raise PermissionDeniedException(
                    f"Permission denied to create folder: {request.path}"
                )

        target_path.mkdir(parents=request.create_parents, exist_ok=True)
        logger.info(f"Successfully created folder: {target_path}")

        return FileExplorerActionResult(
            success=True,
            action="create_folder",
            target_path=str(target_path),
            message=f"Folder created successfully: {target_path.name}",
        )

    async def detect_existence(
        self, request: DetectExistenceRequest
    ) -> FileExplorerActionResult:
        """Checks if a file or directory exists."""
        target_path = self._resolve_and_validate_path(request.path)
        exists = target_path.exists()
        is_dir = target_path.is_dir() if exists else False

        return FileExplorerActionResult(
            success=True,
            action="detect_existence",
            target_path=str(target_path),
            message=f"Path '{target_path.name}' exists={exists}",
            metadata={"exists": exists, "is_dir": is_dir},
        )

    async def get_file_metadata(
        self, request: FileMetadataRequest
    ) -> FileMetadataResponse:
        """Gathers and returns basic metadata for a file or folder."""
        target_path = self._resolve_and_validate_path(request.path)
        if not target_path.exists():
            return FileMetadataResponse(
                name=target_path.name,
                filepath=str(target_path),
                exists=False,
                is_dir=False,
                size_bytes=0,
                extension=target_path.suffix,
            )

        st = target_path.stat()
        created_dt = datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat()
        modified_dt = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()

        return FileMetadataResponse(
            name=target_path.name,
            filepath=str(target_path),
            exists=True,
            is_dir=target_path.is_dir(),
            size_bytes=st.st_size if target_path.is_file() else 0,
            extension=target_path.suffix,
            created_at=created_dt,
            modified_at=modified_dt,
        )
