from unittest.mock import patch
from uuid import uuid4

import pytest
from shared.contracts.execution import ExecutionResult
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.tool import ToolHealth, ToolState

from app.agents.worker.agent import WorkerAgent
from app.tools.desktop import (
    DesktopTool,
    DesktopToolAdapter,
    MouseController,
    register_desktop_tool,
)
from app.tools.registry import ToolRegistry


class MockPermissionManager:
    def __init__(self, should_approve=True):
        self.should_approve = should_approve

    async def check_permission(
        self, action: str, permission_type: PermissionType, context=None
    ) -> bool:
        return self.should_approve


@pytest.fixture
def mock_mouse_ctrl():
    return MouseController(
        screen_size_provider=lambda: (1920, 1080),
        position_provider=lambda: (300, 400),
    )


@pytest.fixture
def desktop_tool(mock_mouse_ctrl):
    return DesktopTool(mouse_controller=mock_mouse_ctrl)


@pytest.fixture
def adapter(desktop_tool):
    return DesktopToolAdapter(desktop_tool=desktop_tool)


def create_task(task_name: str, inputs: dict) -> Task:
    task = Task(
        task_id=uuid4(),
        workflow_id=uuid4(),
        task_name=task_name,
        description=f"Description for {task_name}",
        category=TaskCategory.DESKTOP,
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.READY,
        required_tool="desktop_automation",
        expected_output="Desktop action result",
    )
    # Attach inputs attribute for adapter
    object.__setattr__(task, "inputs", inputs)
    return task


@pytest.mark.asyncio
@patch("app.tools.desktop.mouse.pyautogui.moveTo")
async def test_adapter_execute_mouse_move(mock_move, adapter):
    task = create_task(
        "Mouse Move Task",
        {"action": "mouse_move", "x": 150, "y": 250, "duration": 0.2},
    )
    result = await adapter.execute(task)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.output["status"] == "success"
    assert result.output["action"] == "mouse_move"
    mock_move.assert_called_once_with(x=150, y=250, duration=0.2)


@pytest.mark.asyncio
@patch("app.tools.desktop.mouse.pyautogui.click")
async def test_adapter_execute_mouse_click(mock_click, adapter):
    task = create_task(
        "Mouse Click Task",
        {"action": "mouse_click", "x": 100, "y": 200, "button": "left"},
    )
    result = await adapter.execute(task)

    assert result.success is True
    assert result.output["action"] == "mouse_click"
    mock_click.assert_called_once_with(
        x=100, y=200, button="left", clicks=1, interval=0.0, duration=0.0
    )


@pytest.mark.asyncio
@patch("app.tools.desktop.mouse.pyautogui.scroll")
async def test_adapter_execute_mouse_scroll(mock_scroll, adapter):
    task = create_task(
        "Mouse Scroll Task",
        {"action": "mouse_scroll", "clicks": -5},
    )
    result = await adapter.execute(task)

    assert result.success is True
    assert result.output["action"] == "mouse_scroll"
    mock_scroll.assert_called_once_with(-5)


@pytest.mark.asyncio
async def test_adapter_execute_invalid_coordinates(adapter):
    task = create_task(
        "Invalid Coords Task",
        {"action": "mouse_move", "x": -50, "y": 100},
    )
    result = await adapter.execute(task)

    assert result.success is False
    assert result.error is not None
    assert (
        "InvalidCoordinatesError" in result.error.error_code
        or "Coordinates" in result.error.error_message
    )


def test_register_desktop_tool_registry():
    registry = ToolRegistry()
    tool = register_desktop_tool(registry)

    assert tool.name == "desktop_automation"
    assert tool.status == ToolState.READY
    assert tool.health == ToolHealth.HEALTHY
    assert registry.get("desktop_automation") is not None


@pytest.mark.asyncio
@patch("app.tools.desktop.mouse.pyautogui.click")
async def test_worker_agent_integration_with_desktop_tool(
    mock_click, mock_mouse_ctrl
):
    registry = ToolRegistry()
    worker = WorkerAgent(tool_registry=registry)
    register_desktop_tool(registry, worker_agent=worker)

    # Override tool desktop instance for mocking
    desktop_tool = DesktopTool(mouse_controller=mock_mouse_ctrl)
    worker.register_adapter(
        "desktop_adapter", DesktopToolAdapter(desktop_tool=desktop_tool)
    )

    task = create_task(
        "Click Login Button",
        {"action": "mouse_click", "x": 400, "y": 500, "button": "left"},
    )
    result = await worker.execute(task)

    assert result.success is True
    assert result.output["action"] == "mouse_click"
    mock_click.assert_called_once_with(
        x=400, y=500, button="left", clicks=1, interval=0.0, duration=0.0
    )


@pytest.mark.asyncio
async def test_worker_agent_permission_denied_desktop(mock_mouse_ctrl):
    pm = MockPermissionManager(should_approve=False)
    registry = ToolRegistry()
    worker = WorkerAgent(tool_registry=registry, permission_manager=pm)
    register_desktop_tool(registry, worker_agent=worker)

    desktop_tool = DesktopTool(
        permission_manager=pm, mouse_controller=mock_mouse_ctrl
    )
    worker.register_adapter(
        "desktop_adapter", DesktopToolAdapter(desktop_tool=desktop_tool)
    )

    task = create_task(
        "Click Privileged Button", {"action": "mouse_click", "x": 400, "y": 500}
    )
    result = await worker.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "PERMISSION_DENIED"
