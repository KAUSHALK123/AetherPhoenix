from uuid import uuid4

import pytest
from app.core.config import get_config
from app.core.permissions.models import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
)
from app.core.permissions.manager import PermissionManager
from app.tools.filesystem.executor import FileSystemExecutor
from app.tools.filesystem.models import (
    CopyFileRequest,
    CreateDirectoryRequest,
    DeleteFileRequest,
    ListFilesRequest,
    MoveFileRequest,
    ReadFileRequest,
    RenameFileRequest,
)


class MockPermissionManagerDenied(PermissionManager):
    def validate_permission(self, request_id: str) -> bool:
        return False

    def request_permission(
        self,
        workflow_id: str,
        task_id: str,
        permission_type: PermissionType,
        reason: str,
        context=None,
    ) -> PermissionRequest:
        return PermissionRequest(
            request_id="dummy",
            workflow_id=workflow_id,
            task_id=task_id,
            permission_type=permission_type,
            reason=reason,
            status=PermissionStatus.REJECTED,
        )


@pytest.fixture
def workspace(tmp_path):
    config = get_config()
    original_workspace = config.WORKSPACE_DIR
    config.WORKSPACE_DIR = str(tmp_path)
    yield tmp_path
    config.WORKSPACE_DIR = original_workspace


from app.core.permissions.models import ExecutionMode


@pytest.fixture
def executor(workspace):
    manager = PermissionManager(mode=ExecutionMode.AUTONOMOUS)
    return FileSystemExecutor(permission_manager=manager)


@pytest.mark.asyncio
async def test_path_validation_success(executor, workspace):
    target_path = executor._resolve_and_validate_path("test.txt")
    assert str(target_path) == str(workspace / "test.txt")


@pytest.mark.asyncio
async def test_path_validation_traversal_fails(executor):
    with pytest.raises(ValueError, match=r"Access denied: path '.*' is outside"):
        executor._resolve_and_validate_path("../outside.txt")


@pytest.mark.asyncio
async def test_create_directory(executor, workspace):
    req = CreateDirectoryRequest(path="new_dir")
    res = await executor.create_directory(req)
    assert res == "new_dir"
    assert (workspace / "new_dir").is_dir()


@pytest.mark.asyncio
async def test_list_files(executor, workspace):
    (workspace / "file1.txt").touch()
    (workspace / "file2.txt").touch()

    req = ListFilesRequest(path=".")
    res = await executor.list_files(req)
    assert len(res) == 2
    names = [r["name"] for r in res]
    assert "file1.txt" in names
    assert "file2.txt" in names


@pytest.mark.asyncio
async def test_read_file(executor, workspace):
    (workspace / "read_me.txt").write_text("hello world")

    req = ReadFileRequest(path="read_me.txt")
    res = await executor.read_file(req)
    assert res == "hello world"


@pytest.mark.asyncio
async def test_copy_file(executor, workspace):
    (workspace / "src.txt").write_text("content")

    req = CopyFileRequest(source_path="src.txt", destination_path="dest.txt")
    await executor.copy_file(req)
    assert (workspace / "dest.txt").exists()
    assert (workspace / "dest.txt").read_text() == "content"


@pytest.mark.asyncio
async def test_move_file(executor, workspace):
    (workspace / "src.txt").write_text("content")

    req = MoveFileRequest(source_path="src.txt", destination_path="dest.txt")
    await executor.move_file(req)
    assert not (workspace / "src.txt").exists()
    assert (workspace / "dest.txt").exists()
    assert (workspace / "dest.txt").read_text() == "content"


@pytest.mark.asyncio
async def test_rename_file(executor, workspace):
    (workspace / "old.txt").write_text("content")

    req = RenameFileRequest(path="old.txt", new_name="new.txt")
    await executor.rename_file(req)
    assert not (workspace / "old.txt").exists()
    assert (workspace / "new.txt").exists()


@pytest.mark.asyncio
async def test_rename_file_with_separator_fails(executor, workspace):
    (workspace / "old.txt").write_text("content")

    req = RenameFileRequest(path="old.txt", new_name="../new.txt")
    with pytest.raises(ValueError, match="New name cannot contain path separators"):
        await executor.rename_file(req)


@pytest.mark.asyncio
async def test_delete_file_success(executor, workspace):
    (workspace / "delete_me.txt").touch()

    req = DeleteFileRequest(path="delete_me.txt")
    wf_id = uuid4()
    await executor.delete_file(req, workflow_id=wf_id)
    assert not (workspace / "delete_me.txt").exists()


@pytest.mark.asyncio
async def test_delete_file_permission_denied(workspace):
    denied_executor = FileSystemExecutor(
        permission_manager=MockPermissionManagerDenied()
    )
    (workspace / "delete_me.txt").touch()

    req = DeleteFileRequest(path="delete_me.txt")
    wf_id = uuid4()
    with pytest.raises(PermissionError, match="Permission denied to delete"):
        await denied_executor.delete_file(req, workflow_id=wf_id)

    assert (workspace / "delete_me.txt").exists()
