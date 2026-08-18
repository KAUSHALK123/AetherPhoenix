import uuid
from unittest.mock import AsyncMock

import pytest
from shared.contracts.execution import ExecutionMetrics, ExecutionResult
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task, TaskCategory
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.agents.worker.agent import WorkerAgent
from app.core.permissions.manager import PermissionManager
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry


class DummyToolAdapter(BaseToolAdapter):
    """A dummy adapter that pretends to succeed without doing side-effects."""

    async def execute(self, task: Task) -> ExecutionResult:
        return ExecutionResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            success=True,
            output={"status": "completed", "data": "dummy output"},
            metrics=ExecutionMetrics(execution_time_ms=15.0),
            logs=["Dummy log line 1", "Dummy log line 2"],
        )


class DummyFailingAdapter(BaseToolAdapter):
    """A dummy adapter that pretends to fail."""

    async def execute(self, task: Task) -> ExecutionResult:
        raise RuntimeError("Simulated failure in adapter")


@pytest.fixture
def integration_environment():
    """Sets up the full worker integration environment."""
    permission_manager = PermissionManager()

    # Mock the check_permission so we don't actually need complex setups
    permission_manager.check_permission = AsyncMock(return_value=True)

    tool_registry = ToolRegistry()

    # Register "browser" tool
    tool_registry.register(
        Tool(
            name="browser_automation",
            adapter="browser_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            required_permissions=[PermissionType.BROWSER_ACCESS.value],
        )
    )

    # Register "filesystem" tool
    tool_registry.register(
        Tool(
            name="file_system",
            adapter="fs_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            required_permissions=[
                PermissionType.FILE_SYSTEM.value,
                PermissionType.FILE_SYSTEM_WRITE.value,
            ],
        )
    )

    # Register "failing_tool" tool
    tool_registry.register(
        Tool(
            name="failing_tool",
            adapter="failing_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            required_permissions=[PermissionType.POWERSHELL.value],
        )
    )

    worker_agent = WorkerAgent(
        tool_registry=tool_registry, permission_manager=permission_manager
    )

    worker_agent.register_adapter("browser_adapter", DummyToolAdapter())
    worker_agent.register_adapter("fs_adapter", DummyToolAdapter())
    worker_agent.register_adapter("failing_adapter", DummyFailingAdapter())

    return {
        "worker_agent": worker_agent,
        "permission_manager": permission_manager,
        "tool_registry": tool_registry,
    }


@pytest.mark.asyncio
async def test_worker_pipeline_end_to_end_success(integration_environment):
    env = integration_environment
    worker = env["worker_agent"]

    task = Task(
        workflow_id=uuid.uuid4(),
        task_name="Scrape website",
        description="Scrape test.com",
        required_tool="browser_automation",
        category=TaskCategory.BROWSER,
        expected_output="Website data",
    )

    result = await worker.execute(task)

    # 1. Execution Result
    assert result.success is True
    assert result.output["data"] == "dummy output"

    # 2. Permissions checked
    env["permission_manager"].check_permission.assert_called_once_with(
        action="Execute tool browser_automation",
        permission_type=PermissionType.BROWSER_ACCESS,
        context={"task_id": str(task.task_id), "workflow_id": str(task.workflow_id)},
    )

    # 3. Execution Logs captured in result
    assert len(result.logs) > 0
    assert any("execution started" in log for log in result.logs)
    assert any("Dummy log line" in log for log in result.logs)


@pytest.mark.asyncio
async def test_worker_pipeline_permission_denied(integration_environment):
    env = integration_environment
    worker = env["worker_agent"]

    # Simulate permission rejection
    env["permission_manager"].check_permission.return_value = False

    task = Task(
        workflow_id=uuid.uuid4(),
        task_name="Write file",
        description="Write sensitive data",
        required_tool="file_system",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="File written",
    )

    result = await worker.execute(task)

    # Task should fail due to permissions
    assert result.success is False
    assert result.error.error_code == "PERMISSION_DENIED"
    assert "Permission denied" in result.error.error_message

    # Ensure no output is leaked
    assert result.output == {}

    # Ensure logs record the failure
    assert any("Permission denied" in log for log in result.logs)


@pytest.mark.asyncio
async def test_worker_pipeline_adapter_failure_logs_error(integration_environment):
    env = integration_environment
    worker = env["worker_agent"]

    task = Task(
        workflow_id=uuid.uuid4(),
        task_name="Run script",
        description="Run malicious script",
        required_tool="failing_tool",
        category=TaskCategory.POWERSHELL,
        expected_output="Script output",
    )

    result = await worker.execute(task)

    assert result.success is False
    assert result.error.error_code == "EXECUTION_FAILED"
    assert "Simulated failure in adapter" in result.error.error_message

    assert any("failed with error" in log for log in result.logs)
