import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from shared.contracts.task import Task, TaskCategory, TaskType
from app.tools.git.adapter import GitToolAdapter


@pytest.fixture
def git_adapter():
    return GitToolAdapter()


def create_git_task(operation: str, **kwargs) -> Task:
    return Task(
        workflow_id=uuid4(),
        task_name=f"test_git_{operation}",
        description=f"Test git {operation}",
        task_type=TaskType.LEAF,
        category=TaskCategory.GIT,
        required_tool="git_tool",
        expected_output="Git command result",
        inputs={"operation": operation, **kwargs}
    )


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_git_status_success(mock_exec, git_adapter):
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b" M file1.txt\n?? file2.txt\n", b"")
    mock_process.returncode = 0
    mock_exec.return_value = mock_process

    task = create_git_task("status")
    result = await git_adapter.execute(task)

    assert result.success is True
    assert "M file1.txt" in result.output["output"]
    mock_exec.assert_called_once_with(
        "git", "status", "-s",
        cwd=None,
        stdout=-1,
        stderr=-1
    )


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_git_commit_failure(mock_exec, git_adapter):
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"error: pathspec 'nonexistent.txt' did not match any file(s) known to git")
    mock_process.returncode = 1
    mock_exec.return_value = mock_process

    task = create_git_task("commit", message="Test commit")
    result = await git_adapter.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "GIT_COMMAND_FAILED"
    mock_exec.assert_called_once_with(
        "git", "commit", "-m", "Test commit",
        cwd=None,
        stdout=-1,
        stderr=-1
    )


@pytest.mark.asyncio
async def test_git_missing_branch_for_checkout(git_adapter):
    task = create_git_task("checkout")
    result = await git_adapter.execute(task)

    assert result.success is False
    assert result.error.error_code == "GIT_EXECUTION_ERROR"
    assert "Branch name is required for checkout operation" in result.error.error_message
