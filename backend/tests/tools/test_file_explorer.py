from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.task import Task, TaskCategory, TaskStatus

from app.core.config import get_config
from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.core.permissions.models import (
    ExecutionMode,
    PermissionRequest,
    PermissionStatus,
    PermissionType,
)
from app.services.artifact_storage import ArtifactStorageService
from app.tools.file_explorer.adapter import FileExplorerToolAdapter
from app.tools.file_explorer.executor import FileExplorerExecutor
from app.tools.file_explorer.models import (
    CreateFolderRequest,
    DetectExistenceRequest,
    FileMetadataRequest,
    OpenFileRequest,
    OpenFolderRequest,
    RevealArtifactRequest,
)
from app.tools.file_explorer.tool import register_file_explorer_tool
from app.tools.registry import ToolRegistry


class MockPermissionManagerDenied(PermissionManager):
    def check_permission(self, *args, **kwargs):
        return False

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
    original_artifacts = config.ARTIFACTS_DIR
    config.WORKSPACE_DIR = str(tmp_path)
    config.ARTIFACTS_DIR = str(tmp_path / "artifacts")
    yield tmp_path
    config.WORKSPACE_DIR = original_workspace
    config.ARTIFACTS_DIR = original_artifacts


@pytest.fixture
def executor(workspace):
    manager = PermissionManager(mode=ExecutionMode.AUTONOMOUS)
    storage = ArtifactStorageService()
    return FileExplorerExecutor(
        permission_manager=manager, artifact_storage_service=storage
    )


@pytest.mark.asyncio
async def test_path_validation(executor, workspace):
    target = executor._resolve_and_validate_path("sub/file.txt")
    assert str(target) == str((workspace / "sub/file.txt").resolve())

    with pytest.raises(ValueError, match="Access denied"):
        executor._resolve_and_validate_path("../outside.txt")


@pytest.mark.asyncio
async def test_open_folder_success(executor, workspace):
    folder = workspace / "my_folder"
    folder.mkdir()

    req = OpenFolderRequest(path="my_folder")
    with patch.object(executor, "_launch_os_open") as mock_open:
        res = await executor.open_folder(req)
        assert res.success is True
        assert res.action == "open_folder"
        mock_open.assert_called_once()


@pytest.mark.asyncio
async def test_open_folder_not_found(executor):
    req = OpenFolderRequest(path="non_existent_folder")
    with pytest.raises(FileNotFoundError):
        await executor.open_folder(req)


@pytest.mark.asyncio
async def test_open_folder_not_a_directory(executor, workspace):
    file_path = workspace / "file.txt"
    file_path.touch()

    req = OpenFolderRequest(path="file.txt")
    with pytest.raises(NotADirectoryError):
        await executor.open_folder(req)


@pytest.mark.asyncio
async def test_open_file_success(executor, workspace):
    file_path = workspace / "document.pdf"
    file_path.write_text("dummy PDF content")

    req = OpenFileRequest(path="document.pdf")
    with patch.object(executor, "_launch_os_open") as mock_open:
        res = await executor.open_file(req)
        assert res.success is True
        assert res.action == "open_file"
        mock_open.assert_called_once()


@pytest.mark.asyncio
async def test_open_file_is_directory(executor, workspace):
    folder = workspace / "my_dir"
    folder.mkdir()

    req = OpenFileRequest(path="my_dir")
    with pytest.raises(IsADirectoryError):
        await executor.open_file(req)


@pytest.mark.asyncio
async def test_reveal_artifact_by_filepath(executor, workspace):
    art_file = workspace / "presentation.pptx"
    art_file.write_text("presentation content")

    req = RevealArtifactRequest(filepath="presentation.pptx")
    with patch.object(executor, "_launch_os_reveal") as mock_reveal:
        res = await executor.reveal_artifact(req)
        assert res.success is True
        assert res.action == "reveal_artifact"
        mock_reveal.assert_called_once()


@pytest.mark.asyncio
async def test_reveal_artifact_by_id(executor, workspace):
    art_file = workspace / "test_artifact.pptx"
    art_file.write_text("data")

    wf_id = uuid4()
    art = Artifact(
        workflow_id=wf_id,
        name="test_artifact.pptx",
        filepath=str(art_file),
        artifact_type=ArtifactType.PPT,
    )
    saved_art = await executor.artifact_storage_service.register_artifact(
        art, content=b"data"
    )

    req = RevealArtifactRequest(artifact_id=str(saved_art.artifact_id))
    with patch.object(executor, "_launch_os_reveal") as mock_reveal:
        res = await executor.reveal_artifact(req, workflow_id=wf_id)
        assert res.success is True
        assert res.metadata["artifact_name"] == "test_artifact.pptx"
        mock_reveal.assert_called_once()


@pytest.mark.asyncio
async def test_reveal_artifact_by_name(executor, workspace):
    art_file = workspace / "report.pdf"
    art_file.write_text("report content")

    wf_id = uuid4()
    art = Artifact(
        workflow_id=wf_id,
        name="report.pdf",
        filepath=str(art_file),
        artifact_type=ArtifactType.PDF,
    )
    await executor.artifact_storage_service.register_artifact(
        art, source_path=art_file
    )

    req = RevealArtifactRequest(artifact_name="report.pdf")
    with patch.object(executor, "_launch_os_reveal") as mock_reveal:
        res = await executor.reveal_artifact(req, workflow_id=wf_id)
        assert res.success is True
        mock_reveal.assert_called_once()


@pytest.mark.asyncio
async def test_reveal_artifact_missing_fails(executor):
    req = RevealArtifactRequest(filepath="missing_file.docx")
    with pytest.raises(FileNotFoundError):
        await executor.reveal_artifact(req)


@pytest.mark.asyncio
async def test_create_folder_success(executor, workspace):
    req = CreateFolderRequest(path="new_dir/sub_dir")
    res = await executor.create_folder(req)

    assert res.success is True
    assert (workspace / "new_dir/sub_dir").is_dir()


@pytest.mark.asyncio
async def test_create_folder_permission_denied(workspace):
    denied_manager = MockPermissionManagerDenied()
    storage = ArtifactStorageService()
    executor = FileExplorerExecutor(
        permission_manager=denied_manager, artifact_storage_service=storage
    )

    req = CreateFolderRequest(path="forbidden_dir")
    with pytest.raises(PermissionDeniedException):
        await executor.create_folder(req)


@pytest.mark.asyncio
async def test_detect_existence(executor, workspace):
    (workspace / "exists.txt").touch()

    req1 = DetectExistenceRequest(path="exists.txt")
    res1 = await executor.detect_existence(req1)
    assert res1.metadata["exists"] is True
    assert res1.metadata["is_dir"] is False

    req2 = DetectExistenceRequest(path="does_not_exist.txt")
    res2 = await executor.detect_existence(req2)
    assert res2.metadata["exists"] is False


@pytest.mark.asyncio
async def test_get_file_metadata(executor, workspace):
    file_path = workspace / "sample.txt"
    file_path.write_text("1234567890")

    req = FileMetadataRequest(path="sample.txt")
    res = await executor.get_file_metadata(req)

    assert res.exists is True
    assert res.is_dir is False
    assert res.size_bytes == 10
    assert res.extension == ".txt"
    assert res.created_at is not None
    assert res.modified_at is not None


@pytest.mark.asyncio
async def test_file_explorer_adapter_execute(executor, workspace):
    adapter = FileExplorerToolAdapter(executor=executor)

    # Test reveal_artifact action via adapter
    (workspace / "demo.pptx").touch()
    task = Task(
        workflow_id=uuid4(),
        task_name="Reveal generated PowerPoint presentation",
        description="Reveal PowerPoint in file explorer",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="File Explorer opened with presentation revealed",
        required_tool="file_explorer",
        inputs={
            "action": "reveal_artifact",
            "filepath": "demo.pptx",
        },
    )

    with patch.object(executor, "_launch_os_reveal") as mock_reveal:
        result = await adapter.execute(task)
        assert result.success is True
        assert result.output["action"] == "reveal_artifact"
        mock_reveal.assert_called_once()


@pytest.mark.asyncio
async def test_tool_registration():
    registry = ToolRegistry()
    tool = register_file_explorer_tool(registry)
    assert tool.name == "file_explorer"
    assert registry.get("file_explorer") is not None
