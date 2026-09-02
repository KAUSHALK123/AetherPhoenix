from pathlib import Path
from uuid import uuid4

import pytest
from shared.contracts.task import Task, TaskCategory, TaskType

from app.core.config import get_config
from app.core.permissions.manager import PermissionManager
from app.tools.file_explorer.adapter import FileExplorerToolAdapter
from app.tools.file_explorer.executor import FileExplorerExecutor


class MockPermissionManagerAllowed(PermissionManager):
    def check_permission(self, *args, **kwargs):
        return True


@pytest.fixture
def file_explorer_adapter():
    config = get_config()
    workspace = Path(config.WORKSPACE_DIR).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    pm = MockPermissionManagerAllowed()
    executor = FileExplorerExecutor(permission_manager=pm)
    return FileExplorerToolAdapter(executor=executor)


def create_file_explorer_task(action: str, **inputs) -> Task:
    return Task(
        workflow_id=uuid4(),
        task_name=f"live_file_explorer_{action}",
        description=f"Live test for file explorer {action}",
        task_type=TaskType.LEAF,
        category=TaskCategory.FILE_SYSTEM,
        required_tool="file_explorer",
        expected_output="File explorer action execution result",
        inputs={"action": action, **inputs},
    )


@pytest.mark.asyncio
async def test_live_detect_existence(file_explorer_adapter):
    """Test live detection of permitted workspace directory existence."""
    config = get_config()
    workspace = Path(config.WORKSPACE_DIR).resolve()

    task = create_file_explorer_task("detect_existence", path=str(workspace))
    result = await file_explorer_adapter.execute(task)

    assert result.success is True
    metadata = result.output.get("metadata", {})
    assert metadata.get("exists") is True
    assert metadata.get("is_dir") is True


@pytest.mark.asyncio
async def test_live_create_and_detect_folder(file_explorer_adapter):
    """Test creating a folder inside workspace sandbox and verifying existence."""
    config = get_config()
    workspace = Path(config.WORKSPACE_DIR).resolve()
    target_folder = workspace / "test_live_showcase_folder"

    task_create = create_file_explorer_task(
        "create_folder", path=str(target_folder), create_parents=True
    )
    res_create = await file_explorer_adapter.execute(task_create)

    assert res_create.success is True

    task_detect = create_file_explorer_task("detect_existence", path=str(target_folder))
    res_detect = await file_explorer_adapter.execute(task_detect)

    assert res_detect.success is True
    metadata = res_detect.output.get("metadata", {})
    assert metadata.get("exists") is True
    assert metadata.get("is_dir") is True


@pytest.mark.asyncio
async def test_live_file_metadata_in_workspace(file_explorer_adapter):
    """Test creating a test file in workspace sandbox and retrieving metadata."""
    config = get_config()
    workspace = Path(config.WORKSPACE_DIR).resolve()
    test_file = workspace / "test_showcase_meta.txt"
    test_file.write_text("Hello AetherPhoenix File Explorer Showcase", encoding="utf-8")

    task = create_file_explorer_task("get_file_metadata", path=str(test_file))
    result = await file_explorer_adapter.execute(task)

    assert result.success is True
    assert result.output.get("size_bytes", 0) > 0
    assert result.output.get("name") == "test_showcase_meta.txt"
