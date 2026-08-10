import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.permissions.models import PermissionRequest, PermissionType

from app.core.config import get_config
from app.core.permissions.manager import PermissionManager
from app.tools.filesystem.models import (
    CopyFileRequest,
    CreateDirectoryRequest,
    DeleteFileRequest,
    ListFilesRequest,
    MoveFileRequest,
    ReadFileRequest,
    RenameFileRequest,
)

logger = logging.getLogger(__name__)


class FileSystemExecutor:
    """Executor for filesystem operations with path validation and permission checks."""

    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        self.config = get_config()
        self.workspace_dir = Path(self.config.WORKSPACE_DIR).resolve()
        self.permission_manager = permission_manager or PermissionManager()

    def _resolve_and_validate_path(self, path: str) -> Path:
        """
        Resolves a given path against the workspace directory and validates
        that it does not attempt path traversal outside the workspace.
        """
        # Resolve to absolute path, starting from workspace if relative
        resolved_path = (self.workspace_dir / Path(path)).resolve()

        # Check if the resolved path is a subpath of workspace_dir
        if not str(resolved_path).startswith(str(self.workspace_dir)):
            logger.error(
                f"Path validation failed: {path} is outside "
                f"workspace {self.workspace_dir}"
            )
            raise ValueError(
                f"Access denied: path '{path}' is outside the "
                f"permitted workspace directory."
            )

        return resolved_path

    async def list_files(self, request: ListFilesRequest) -> List[Dict[str, Any]]:
        """List files and directories in the specified path."""
        target_path = self._resolve_and_validate_path(request.path)

        logger.info(f"Listing files in: {target_path} (recursive={request.recursive})")
        if not target_path.exists():
            raise FileNotFoundError(f"Path not found: {request.path}")
        if not target_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {request.path}")

        results = []

        def _scan(directory: Path):
            for item in directory.iterdir():
                results.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(self.workspace_dir)),
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else None,
                    }
                )
                if request.recursive and item.is_dir():
                    _scan(item)

        _scan(target_path)
        logger.info(f"Successfully listed {len(results)} items in {target_path}")
        return results

    async def read_file(self, request: ReadFileRequest) -> str:
        """Read the contents of a file."""
        target_path = self._resolve_and_validate_path(request.path)
        logger.info(f"Reading file: {target_path}")

        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {request.path}")
        if not target_path.is_file():
            raise IsADirectoryError(f"Path is a directory, not a file: {request.path}")

        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Successfully read file {target_path}")
        return content

    async def create_directory(self, request: CreateDirectoryRequest) -> str:
        """Create a new directory."""
        target_path = self._resolve_and_validate_path(request.path)
        logger.info(
            f"Creating directory: {target_path} "
            f"(create_parents={request.create_parents})"
        )

        target_path.mkdir(parents=request.create_parents, exist_ok=True)
        logger.info(f"Successfully created directory {target_path}")
        return str(target_path.relative_to(self.workspace_dir))

    async def copy_file(self, request: CopyFileRequest) -> str:
        """Copy a file to a new destination."""
        src_path = self._resolve_and_validate_path(request.source_path)
        dst_path = self._resolve_and_validate_path(request.destination_path)
        logger.info(f"Copying file from {src_path} to {dst_path}")

        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {request.source_path}")
        if not src_path.is_file():
            raise IsADirectoryError(
                f"Source path is a directory: {request.source_path}"
            )

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        logger.info(f"Successfully copied file to {dst_path}")
        return str(dst_path.relative_to(self.workspace_dir))

    async def move_file(self, request: MoveFileRequest) -> str:
        """Move a file or directory to a new destination."""
        src_path = self._resolve_and_validate_path(request.source_path)
        dst_path = self._resolve_and_validate_path(request.destination_path)
        logger.info(f"Moving from {src_path} to {dst_path}")

        if not src_path.exists():
            raise FileNotFoundError(f"Source not found: {request.source_path}")

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src_path, dst_path)
        logger.info(f"Successfully moved to {dst_path}")
        return str(dst_path.relative_to(self.workspace_dir))

    async def rename_file(self, request: RenameFileRequest) -> str:
        """Rename a file or directory in place."""
        target_path = self._resolve_and_validate_path(request.path)
        # Ensure new name does not contain path separators to avoid traversal
        if "/" in request.new_name or "\\" in request.new_name:
            raise ValueError(
                f"New name cannot contain path separators: {request.new_name}"
            )

        new_path = target_path.parent / request.new_name
        logger.info(f"Renaming {target_path} to {new_path}")

        if not target_path.exists():
            raise FileNotFoundError(f"Path not found: {request.path}")

        target_path.rename(new_path)
        logger.info(f"Successfully renamed to {new_path}")
        return str(new_path.relative_to(self.workspace_dir))

    async def delete_file(self, request: DeleteFileRequest, workflow_id: UUID) -> bool:
        """Delete a file or directory. Requires explicit permission."""
        target_path = self._resolve_and_validate_path(request.path)
        logger.info(f"Attempting to delete: {target_path}")

        if not target_path.exists():
            raise FileNotFoundError(f"Path not found: {request.path}")

        # Check permissions for delete operation
        req = self.permission_manager.request_permission(
            workflow_id=str(workflow_id),
            task_id="delete_file",
            permission_type=PermissionType.FILE_DELETE,
            reason=f"Requires permission to delete path: {request.path}",
        )
        
        has_permission = self.permission_manager.validate_permission(req.request_id)
        
        if not has_permission:
            logger.warning(f"Delete permission denied for {target_path}")
            raise PermissionError(f"Permission denied to delete {request.path}")

        if target_path.is_dir():
            if not request.recursive:
                # Check if directory is empty
                if any(target_path.iterdir()):
                    raise OSError(f"Directory not empty: {request.path}")
                target_path.rmdir()
            else:
                shutil.rmtree(target_path)
        else:
            target_path.unlink()

        logger.info(f"Successfully deleted {target_path}")
        return True
