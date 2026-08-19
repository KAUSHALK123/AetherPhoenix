import uuid

import pytest
from shared.contracts.execution import ExecutionMetrics, ExecutionResult
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.agents.worker.agent import WorkerAgent
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry


class MockToolAdapter(BaseToolAdapter):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.execute_called = False

    async def execute(self, task: Task) -> ExecutionResult:
        self.execute_called = True
        if self.should_fail:
            raise RuntimeError("Mock adapter simulated failure")

        return ExecutionResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            success=True,
            output={"result": "success"},
            metrics=ExecutionMetrics(execution_time_ms=10.0),
        )


@pytest.fixture
def tool_registry():
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="valid_tool",
            adapter="mock_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
        )
    )
    registry.register(
        Tool(
            name="broken_tool",
            adapter="mock_adapter_broken",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
        )
    )
    registry.register(
        Tool(
            name="unready_tool",
            adapter="mock_adapter",
            status=ToolState.INSTALLED,
            health=ToolHealth.HEALTHY,
        )
    )
    return registry


@pytest.fixture
def worker_agent(tool_registry):
    agent = WorkerAgent(tool_registry=tool_registry)
    agent.register_adapter("mock_adapter", MockToolAdapter(should_fail=False))
    agent.register_adapter("mock_adapter_fail", MockToolAdapter(should_fail=True))
    return agent


def create_task(tool_name: str) -> Task:
    return Task(
        workflow_id=uuid.uuid4(),
        task_name="Test Task",
        description="Testing worker execution",
        required_tool=tool_name,
        category=TaskCategory.OTHER,
        expected_output="Test output",
    )


@pytest.mark.asyncio
async def test_successful_execution(worker_agent):
    task = create_task("valid_tool")
    result = await worker_agent.execute(task)

    assert result.success is True
    assert result.output == {"result": "success"}
    assert result.task_id == task.task_id
    assert task.status == TaskStatus.RUNNING
    assert result.metrics.execution_time_ms == 10.0


@pytest.mark.asyncio
async def test_missing_required_tool(worker_agent):
    task = create_task("")
    result = await worker_agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code in ("EXECUTION_FAILED", "TOOL_NOT_FOUND")
    assert "missing 'required_tool'" in result.error.error_message


@pytest.mark.asyncio
async def test_tool_not_found_in_registry(worker_agent):
    task = create_task("nonexistent_tool")
    result = await worker_agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert "not found in registry" in result.error.error_message


@pytest.mark.asyncio
async def test_tool_not_ready(worker_agent):
    task = create_task("unready_tool")
    result = await worker_agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert "is not ready" in result.error.error_message


@pytest.mark.asyncio
async def test_adapter_not_registered(worker_agent):
    task = create_task("broken_tool")
    result = await worker_agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert "not registered in WorkerAgent" in result.error.error_message


@pytest.mark.asyncio
async def test_adapter_execution_failure(tool_registry):
    agent = WorkerAgent(tool_registry=tool_registry)
    # Register an adapter that raises an exception
    agent.register_adapter("mock_adapter", MockToolAdapter(should_fail=True))

    task = create_task("valid_tool")
    result = await agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "EXECUTION_FAILED"
    assert "Mock adapter simulated failure" in result.error.error_message
    assert result.metrics.execution_time_ms > 0  # Should record time even on failure
