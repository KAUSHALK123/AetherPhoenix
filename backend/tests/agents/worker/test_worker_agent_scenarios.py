import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import ExecutionResult
from shared.contracts.task import Task, TaskCategory, TaskType
from shared.contracts.tool import Tool, ToolState

from app.agents.worker.agent import WorkerAgent
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry


class MockToolAdapter(BaseToolAdapter):
    def __init__(self, should_fail: bool = False, fail_artifact: bool = False):
        self.should_fail = should_fail
        self.fail_artifact = fail_artifact

    async def execute(self, task: Task, *args, **kwargs) -> ExecutionResult:
        if self.should_fail:
            raise RuntimeError("Tool execution failed internally in adapter")

        artifacts = []
        if self.fail_artifact:
            artifacts.append(
                Artifact(
                    workflow_id=task.workflow_id,
                    task_id=task.task_id,
                    name="artifact_1.pdf",
                    filepath="/tmp/artifact_1.pdf",
                    artifact_type=ArtifactType.PDF,
                )
            )

        return ExecutionResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            success=True,
            output={"result": "Success"},
            artifacts=artifacts,
            error=None,
        )


@pytest.fixture
def tool_registry():
    registry = ToolRegistry()
    tool = Tool(
        name="test_tool",
        version="1.0.0",
        status=ToolState.READY,
        adapter="test_adapter",
        required_permissions=[],
    )
    registry.register(tool)
    return registry


@pytest.fixture
def worker_agent(tool_registry):
    mock_history = MagicMock()
    mock_storage = MagicMock()
    mock_storage.register_artifact = AsyncMock()

    agent = WorkerAgent(
        tool_registry=tool_registry,
        task_history_service=mock_history,
        artifact_storage_service=mock_storage,
    )
    adapter = MockToolAdapter()
    agent.register_adapter("test_adapter", adapter)
    return agent


@pytest.mark.asyncio
async def test_worker_correct_task_and_tool_selection(worker_agent):
    """Test successful task execution with valid task, tool, and adapter selection."""
    task = Task(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        task_name="Valid Execution Task",
        description="Execute valid task",
        expected_output="Success result",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="test_tool",
    )

    result = await worker_agent.execute(task)

    assert result.success is True
    assert result.error is None
    assert result.output.get("result") == "Success"


@pytest.mark.asyncio
async def test_worker_invalid_tool_missing_tool_name(worker_agent):
    """Test task execution failure when task is missing required_tool."""
    task = Task(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        task_name="Missing Tool Task",
        description="Task missing required tool",
        expected_output="Error output",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="",  # Empty tool name
    )

    result = await worker_agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert "missing 'required_tool'" in result.error.error_message


@pytest.mark.asyncio
async def test_worker_invalid_tool_unregistered_tool(worker_agent):
    """Test task execution failure when tool is not registered in ToolRegistry."""
    task = Task(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        task_name="Unregistered Tool Task",
        description="Task with unregistered tool",
        expected_output="Error output",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="non_existent_tool",
    )

    result = await worker_agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert "not found in registry" in result.error.error_message


@pytest.mark.asyncio
async def test_worker_invalid_tool_unregistered_adapter(worker_agent, tool_registry):
    """Test task failure when adapter is not registered in WorkerAgent."""
    tool = Tool(
        name="no_adapter_tool",
        version="1.0.0",
        status=ToolState.READY,
        adapter="unregistered_adapter",
    )
    tool_registry.register(tool)

    task = Task(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        task_name="No Adapter Task",
        description="Task with unregistered adapter",
        expected_output="Error output",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="no_adapter_tool",
    )

    result = await worker_agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert "not registered in WorkerAgent" in result.error.error_message


@pytest.mark.asyncio
async def test_worker_tool_execution_failure(worker_agent):
    """Test tool execution failure when adapter raises runtime exception."""
    failing_adapter = MockToolAdapter(should_fail=True)
    worker_agent.register_adapter("failing_adapter", failing_adapter)

    failing_tool = Tool(
        name="failing_tool",
        version="1.0.0",
        status=ToolState.READY,
        adapter="failing_adapter",
    )
    worker_agent.tool_registry.register(failing_tool)

    task = Task(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        task_name="Failing Execution Task",
        description="Task that will fail execution",
        expected_output="Failed output",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="failing_tool",
    )

    result = await worker_agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert "Tool execution failed internally" in result.error.error_message


@pytest.mark.asyncio
async def test_worker_artifact_generation_failure(worker_agent):
    """Test handling when artifact storage fails during execution registration."""
    artifact_failing_adapter = MockToolAdapter(should_fail=False, fail_artifact=True)
    worker_agent.register_adapter("artifact_adapter", artifact_failing_adapter)

    artifact_tool = Tool(
        name="artifact_tool",
        version="1.0.0",
        status=ToolState.READY,
        adapter="artifact_adapter",
    )
    worker_agent.tool_registry.register(artifact_tool)

    # Mock storage service to raise exception when storing artifact
    worker_agent.artifact_storage_service.register_artifact.side_effect = Exception(
        "Artifact Storage Error: Disk write failed"
    )

    task = Task(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        task_name="Artifact Failure Task",
        description="Task with artifact storage failure",
        expected_output="Artifact output",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="artifact_tool",
    )

    result = await worker_agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert "Artifact Storage Error" in result.error.error_message
