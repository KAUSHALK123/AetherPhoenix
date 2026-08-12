from unittest.mock import patch

import pytest
from shared.contracts.permission import PermissionType
from shared.contracts.tool import ToolHealth, ToolState

from app.tools.desktop.interface import DesktopTool


def test_desktop_tool_initialization():
    tool = DesktopTool()
    assert tool.name == "desktop_automation"
    assert tool.status == ToolState.READY
    assert tool.health == ToolHealth.HEALTHY
    assert PermissionType.DESKTOP_AUTOMATION in tool.required_permissions


@patch("app.tools.desktop.mouse.pyautogui.click")
def test_desktop_tool_execute_mouse_click(mock_click):
    tool = DesktopTool()
    result = tool.execute("mouse_click", {"x": 100, "y": 200, "button": "right"})
    assert result["status"] == "success"
    assert result["action"] == "mouse_click"
    mock_click.assert_called_once_with(x=100, y=200, button="right")


@patch("app.tools.desktop.keyboard.pyautogui.write")
def test_desktop_tool_execute_keyboard_type(mock_write):
    tool = DesktopTool()
    result = tool.execute("keyboard_type", {"text": "Hello"})
    assert result["status"] == "success"
    assert result["action"] == "keyboard_type"
    mock_write.assert_called_once_with("Hello", interval=0.05)


def test_desktop_tool_execute_unsupported_action():
    tool = DesktopTool()
    with pytest.raises(ValueError, match="Unsupported action: unknown_action"):
        tool.execute("unknown_action", {})
