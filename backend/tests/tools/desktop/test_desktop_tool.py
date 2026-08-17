from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from shared.contracts.desktop import MouseActionRequest, MouseActionType
from shared.contracts.permission import PermissionType
from shared.contracts.tool import ToolHealth, ToolState

from app.core.exceptions import PermissionDeniedException
from app.tools.desktop.interface import DesktopTool
from app.tools.desktop.mouse import MouseController


@pytest.fixture
def mock_mouse_controller():
    return MouseController(
        screen_size_provider=lambda: (1920, 1080),
        position_provider=lambda: (250, 350),
    )


@pytest.fixture(autouse=True)
def mock_desktop_session():
    """Ensure desktop session check passes by default across tests."""
    with patch("app.tools.desktop.keyboard.pyautogui.size", return_value=(1920, 1080)):
        yield


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
def test_desktop_tool_execute_mouse_double_click(mock_double, mock_mouse_controller):
    tool = DesktopTool(mouse_controller=mock_mouse_controller)
    result = tool.execute("mouse_double_click", {"x": 130, "y": 230, "button": "left"})
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
def test_desktop_tool_execute_mouse_action_structured(mock_move, mock_mouse_controller):
    tool = DesktopTool(mouse_controller=mock_mouse_controller)
    req = MouseActionRequest(action=MouseActionType.MOVE, x=300, y=400, duration=0.1)
    result = tool.execute("mouse_action", {"request": req})
    assert result.success is True
    assert result.action == MouseActionType.MOVE
    mock_move.assert_called_once_with(x=300, y=400, duration=0.1)


@patch("app.tools.desktop.keyboard.pyautogui.write")
def test_desktop_tool_execute_keyboard_type(mock_write):
    tool = DesktopTool()
    result = tool.execute("keyboard_type", {"text": "Hello", "interval": 0.02})
    assert result["status"] == "success"
    assert result["action"] == "keyboard_type"
    assert result["characters_typed"] == 5
    mock_write.assert_called_once_with("Hello", interval=0.02)


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_desktop_tool_execute_keyboard_press(mock_press):
    tool = DesktopTool()
    result = tool.execute("keyboard_press", {"key": "enter"})
    assert result["status"] == "success"
    assert result["action"] == "keyboard_press"
    assert result["key"] == "enter"
    mock_press.assert_called_once_with("enter", presses=1, interval=0.0)


@patch("app.tools.desktop.keyboard.pyautogui.keyDown")
def test_desktop_tool_execute_keyboard_down(mock_key_down):
    tool = DesktopTool()
    result = tool.execute("keyboard_down", {"key": "ctrl"})
    assert result["status"] == "success"
    assert result["action"] == "keyboard_down"
    mock_key_down.assert_called_once_with("ctrl")


@patch("app.tools.desktop.keyboard.pyautogui.keyUp")
def test_desktop_tool_execute_keyboard_up(mock_key_up):
    tool = DesktopTool()
    result = tool.execute("keyboard_up", {"key": "ctrl"})
    assert result["status"] == "success"
    assert result["action"] == "keyboard_up"
    mock_key_up.assert_called_once_with("ctrl")


@patch("app.tools.desktop.keyboard.pyautogui.hotkey")
def test_desktop_tool_execute_keyboard_hotkey(mock_hotkey):
    tool = DesktopTool()
    result = tool.execute("keyboard_hotkey", {"keys": ["ctrl", "c"]})
    assert result["status"] == "success"
    assert result["action"] == "keyboard_hotkey"
    mock_hotkey.assert_called_once_with("ctrl", "c")


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_desktop_tool_execute_keyboard_special_key(mock_press):
    tool = DesktopTool()
    result = tool.execute("keyboard_special_key", {"special_key": "tab"})
    assert result["status"] == "success"
    mock_press.assert_called_once_with("tab", presses=1, interval=0.0)


def test_desktop_tool_permission_denied():
    mock_perm_mgr = MagicMock()
    mock_perm_mgr.check_permission.return_value = False
    tool = DesktopTool(permission_manager=mock_perm_mgr)

    wf_id = uuid4()
    with pytest.raises(PermissionDeniedException, match="Permission denied"):
        tool.execute("keyboard_press", {"key": "enter", "workflow_id": wf_id})

    mock_perm_mgr.check_permission.assert_called_once_with(
        PermissionType.DESKTOP_AUTOMATION, workflow_id=wf_id
    )


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_desktop_tool_permission_granted(mock_press):
    mock_perm_mgr = MagicMock()
    mock_perm_mgr.check_permission.return_value = True
    tool = DesktopTool(permission_manager=mock_perm_mgr)

    wf_id = uuid4()
    result = tool.execute("keyboard_press", {"key": "enter", "workflow_id": wf_id})
    assert result["status"] == "success"
    mock_press.assert_called_once_with("enter", presses=1, interval=0.0)


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


def test_register_desktop_tool():
    from app.tools.desktop.interface import register_desktop_tool
    from app.tools.registry import ToolRegistry

    registry = ToolRegistry()
    desktop_tool = register_desktop_tool(registry)

    assert registry.get("desktop_automation") is not None
    assert registry.get_instance("desktop_automation") == desktop_tool
    assert desktop_tool.name == "desktop_automation"
    assert desktop_tool.status == ToolState.READY
