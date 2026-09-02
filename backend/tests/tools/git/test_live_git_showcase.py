from uuid import uuid4

import pytest
from shared.contracts.task import Task, TaskCategory, TaskType

from app.tools.git.adapter import GitToolAdapter


@pytest.fixture
def git_adapter():
    return GitToolAdapter()


def create_live_git_task(operation: str, **kwargs) -> Task:
    return Task(
        workflow_id=uuid4(),
        task_name=f"live_git_{operation}",
        description=f"Live test for git {operation}",
        task_type=TaskType.LEAF,
        category=TaskCategory.GIT,
        required_tool="git_tool",
        expected_output="Live Git execution result",
        inputs={"operation": operation, **kwargs},
    )


@pytest.mark.asyncio
async def test_live_git_detect_repo(git_adapter):
    """Test live detection of the AetherPhoenix git repository."""
    task = create_live_git_task("detect_repo")
    result = await git_adapter.execute(task)

    assert result.success is True
    assert result.output.get("output") == "true"


@pytest.mark.asyncio
async def test_live_git_status(git_adapter):
    """Test live status check of the repository."""
    task = create_live_git_task("status")
    result = await git_adapter.execute(task)

    assert result.success is True
    assert "output" in result.output


@pytest.mark.asyncio
async def test_live_git_history(git_adapter):
    """Test live git history retrieval."""
    task = create_live_git_task("history", limit=5)
    result = await git_adapter.execute(task)

    assert result.success is True
    assert len(result.output.get("output", "")) > 0
