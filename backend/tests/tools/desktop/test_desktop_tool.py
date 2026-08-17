from unittest.mock import patch

import pytest
from shared.contracts.desktop import MouseActionRequest, MouseActionType
from shared.contracts.permission import PermissionType
from shared.contracts.tool import ToolHealth, ToolState

from app.tools.desktop.interface import DesktopTool
from app.tools.desktop.mouse import MouseController


@pytest.fixture
def mock_mouse_controller():
    return MouseController(
        screen_size_provider=lambda: (1920, 1080),
        position_provider=lambda: (250, 350),
    )


def test_desktop_tool_initialization():
    tool = DesktopTool()
    assert tool.name == "desktop_automation"
    assert tool.status == ToolState.READY
    assert tool.health == ToolHealth.HEALTHY
    assert PermissionType.DESKTOP_AUTOMATION in tool.required_permissions


@patch("app.tools.desktop.mouse.pyautogui.position", return_value=(250, 350))
def test_desktop_tool_execute_mouse_get_position(mock_pos, mock_mouse_controller):
    tool = DesktopTool(mouse_controller=mock_mouse_controller)
    result = tool.execute("mouse_get_position")
    assert result["status"] == "success"
    assert result["action"] == "mouse_get_position"
    assert result["x"] == 250
    assert result["y"] == 350


@patch("app.tools.desktop.mouse.pyautogui.moveTo")
def test_desktop_tool_execute_mouse_move(mock_move, mock_mouse_controller):
    tool = DesktopTool(mouse_controller=mock_mouse_controller)
    result = tool.execute("mouse_move", {"x": 100, "y": 200, "duration": 0.3})
    assert result["status"] == "success"
    assert result["action"] == "mouse_move"
    assert result["position"]["x"] == 100
    assert result["position"]["y"] == 200
    mock_move.assert_called_once_with(x=100, y=200, duration=0.3)


@patch("app.tools.desktop.mouse.pyautogui.click")
def test_desktop_tool_execute_mouse_click(mock_click, mock_mouse_controller):
    tool = DesktopTool(mouse_controller=mock_mouse_controller)
    result = tool.execute("mouse_click", {"x": 100, "y": 200, "button": "right"})
    assert result["status"] == "success"
    assert result["action"] == "mouse_click"
    mock_click.assert_called_once_with(
        x=100, y=200, button="right", clicks=1, interval=0.0, duration=0.0
    )


@patch("app.tools.desktop.mouse.pyautogui.click")
def test_desktop_tool_execute_mouse_right_click(mock_click, mock_mouse_controller):
    tool = DesktopTool(mouse_controller=mock_mouse_controller)
    result = tool.execute("mouse_right_click", {"x": 120, "y": 220})
    assert result["status"] == "success"
    assert result["action"] == "mouse_right_click"
    mock_click.assert_called_once_with(
        x=120, y=220, button="right", clicks=1, interval=0.0, duration=0.0
    )


@patch("app.tools.desktop.mouse.pyautogui.doubleClick")
def test_desktop_tool_execute_mouse_double_click(
    mock_double, mock_mouse_controller
):
    tool = DesktopTool(mouse_controller=mock_mouse_controller)
    result = tool.execute(
        "mouse_double_click", {"x": 130, "y": 230, "button": "left"}
    )
    assert result["status"] == "success"
    assert result["action"] == "mouse_double_click"
    mock_double.assert_called_once_with(
        x=130, y=230, button="left", interval=0.1, duration=0.0
    )


@patch("app.tools.desktop.mouse.pyautogui.scroll")
def test_desktop_tool_execute_mouse_scroll(mock_scroll, mock_mouse_controller):
    tool = DesktopTool(mouse_controller=mock_mouse_controller)
    result = tool.execute("mouse_scroll", {"clicks": 5, "x": 50, "y": 60})
    assert result["status"] == "success"
    assert result["action"] == "mouse_scroll"
    assert result["clicks"] == 5
    mock_scroll.assert_called_once_with(5, x=50, y=60)


@patch("app.tools.desktop.mouse.pyautogui.moveTo")
def test_desktop_tool_execute_mouse_action_structured(
    mock_move, mock_mouse_controller
):
    tool = DesktopTool(mouse_controller=mock_mouse_controller)
    req = MouseActionRequest(
        action=MouseActionType.MOVE, x=300, y=400, duration=0.1
    )
    result = tool.execute("mouse_action", {"request": req})
    assert result.success is True
    assert result.action == MouseActionType.MOVE
    mock_move.assert_called_once_with(x=300, y=400, duration=0.1)


@patch("app.tools.desktop.keyboard.pyautogui.write")
def test_desktop_tool_execute_keyboard_type(mock_write):
    tool = DesktopTool()
    result = tool.execute("keyboard_type", {"text": "Hello"})
    assert result["status"] == "success"
    assert result["action"] == "keyboard_type"
    mock_write.assert_called_once_with("Hello", interval=0.05)


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_desktop_tool_execute_keyboard_press(mock_press):
    tool = DesktopTool()
    result = tool.execute("keyboard_press", {"key": "enter"})
    assert result["status"] == "success"
    mock_press.assert_called_once_with("enter")


@patch("app.tools.desktop.keyboard.pyautogui.hotkey")
def test_desktop_tool_execute_keyboard_hotkey(mock_hotkey):
    tool = DesktopTool()
    result = tool.execute("keyboard_hotkey", {"keys": ["ctrl", "c"]})
    assert result["status"] == "success"
    mock_hotkey.assert_called_once_with("ctrl", "c")


def test_desktop_tool_execute_unsupported_action():
    tool = DesktopTool()
    with pytest.raises(ValueError, match="Unsupported action: unknown_action"):
        tool.execute("unknown_action", {})
