from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from shared.contracts.execution import ExecutionResult
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task, TaskCategory
from shared.contracts.tool import ToolHealth, ToolState

from app.core.permissions.manager import PermissionManager
from app.tools.desktop.controller import DesktopController
from app.tools.desktop.interface import (
    DesktopToolAdapter,
    register_desktop_tool,
)
from app.tools.desktop.models import DesktopActionResult
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_desktop_tool_adapter_execute_success():
    mock_controller = MagicMock(spec=DesktopController)
    mock_controller.execute_action = AsyncMock(
        return_value=DesktopActionResult(
            action="mouse_click",
            success=True,
            output={"status": "clicked", "x": 100, "y": 200},
            execution_time_ms=15.0,
        )
    )

    adapter = DesktopToolAdapter(controller=mock_controller)

    task = Task(
        workflow_id=uuid4(),
        task_name="Click Button",
        description="Click desktop button",
        required_tool="desktop_automation",
        category=TaskCategory.DESKTOP,
        expected_output="Clicked",
    )
    # Attach input parameters to task instance
    object.__setattr__(
        task, "input_parameters", {"action": "mouse_click", "x": 100, "y": 200}
    )

    result = await adapter.execute(task)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.output["status"] == "clicked"
    assert result.task_id == task.task_id
    assert "Desktop action 'mouse_click' succeeded" in result.logs[0]


@pytest.mark.asyncio
async def test_desktop_tool_adapter_execute_failure():
    mock_controller = MagicMock(spec=DesktopController)
    mock_controller.execute_action = AsyncMock(
        return_value=DesktopActionResult(
            action="launch_app",
            success=False,
            error="Application not found",
            execution_time_ms=25.0,
        )
    )

    adapter = DesktopToolAdapter(controller=mock_controller)

    task = Task(
        workflow_id=uuid4(),
        task_name="Launch Ghost App",
        description="Launch missing application",
        required_tool="desktop_automation",
        category=TaskCategory.DESKTOP,
        expected_output="Launched",
    )
    object.__setattr__(
        task, "input_parameters", {"action": "launch_app", "app_path": "ghost.exe"}
    )

    result = await adapter.execute(task)

    assert isinstance(result, ExecutionResult)
    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "DESKTOP_ACTION_FAILED"
    assert "Application not found" in result.error.error_message


def test_register_desktop_tool():
    registry = ToolRegistry()
    pm = MagicMock(spec=PermissionManager)

    tool = register_desktop_tool(registry=registry, permission_manager=pm)

    assert tool.name == "desktop_automation"
    assert tool.status == ToolState.READY
    assert tool.health == ToolHealth.HEALTHY
    assert PermissionType.DESKTOP_AUTOMATION in tool.required_permissions

    retrieved = registry.get("desktop_automation")
    assert retrieved == tool
    assert registry.get_instance("desktop_automation") is not None
