import time
from unittest.mock import patch

import pyautogui
import pytest
from shared.contracts.desktop import (
    MouseActionRequest,
    MouseActionResult,
    MouseActionType,
    MouseButton,
    MousePosition,
)
from shared.contracts.permission import PermissionType

from app.core.exceptions import PermissionDeniedException
from app.tools.desktop.exceptions import (
    DesktopSessionUnavailableError,
    InvalidCoordinatesError,
    MouseActionError,
    MouseTimeoutError,
)
from app.tools.desktop.mouse import MouseController


@pytest.fixture
def mock_screen():
    return lambda: (1920, 1080)


@pytest.fixture
def mock_pos():
    return lambda: (500, 400)


@pytest.fixture
def controller(mock_screen, mock_pos):
    return MouseController(
        screen_size_provider=mock_screen,
        position_provider=mock_pos,
        default_timeout=5.0,
    )


class MockPermissionManager:
    def __init__(self, should_approve=True):
        self.should_approve = should_approve
        self.checked_actions = []

    def check_permission(
        self, action: str, permission_type: PermissionType, context=None
    ) -> bool:
        self.checked_actions.append((action, permission_type))
        return self.should_approve


# 1. Cursor Position Tests
def test_get_cursor_position(controller):
    pos = controller.get_position()
    assert isinstance(pos, MousePosition)
    assert pos.x == 500
    assert pos.y == 400


def test_get_cursor_position_failure():
    def failing_pos():
        raise RuntimeError("Position sensor failure")

    ctrl = MouseController(
        screen_size_provider=lambda: (1920, 1080),
        position_provider=failing_pos,
    )
    with pytest.raises(DesktopSessionUnavailableError):
        ctrl.get_position()


# 2. Movement Tests
@patch("app.tools.desktop.mouse.pyautogui.moveTo")
def test_mouse_move_to_success(mock_move, controller):
    result = controller.move_to(100, 200, duration=0.2)
    mock_move.assert_called_once_with(x=100, y=200, duration=0.2)
    assert isinstance(result, MouseActionResult)
    assert result.success is True
    assert result.action == MouseActionType.MOVE
    assert result.position.x == 100
    assert result.position.y == 200


def test_mouse_move_negative_duration(controller):
    with pytest.raises(InvalidCoordinatesError, match="duration cannot be negative"):
        controller.move_to(100, 200, duration=-1.0)


# 3. Click Tests
@patch("app.tools.desktop.mouse.pyautogui.click")
def test_mouse_click_success(mock_click, controller):
    result = controller.click(10, 20, "right")
    mock_click.assert_called_once_with(
        x=10, y=20, button="right", clicks=1, interval=0.0, duration=0.0
    )
    assert result.success is True
    assert result.action == MouseActionType.RIGHT_CLICK
    assert result.position.x == 10
    assert result.position.y == 20


@patch("app.tools.desktop.mouse.pyautogui.click")
def test_mouse_click_at_current_position(mock_click, controller):
    result = controller.click(button="left")
    mock_click.assert_called_once_with(button="left", clicks=1, interval=0.0)
    assert result.success is True
    assert result.position.x == 500
    assert result.position.y == 400


@patch("app.tools.desktop.mouse.pyautogui.click")
def test_mouse_click_failure(mock_click, controller):
    mock_click.side_effect = Exception("Hardware click failure")
    with pytest.raises(MouseActionError):
        controller.click(10, 20)


def test_mouse_click_invalid_button(controller):
    with pytest.raises(
        MouseActionError, match="Unsupported mouse button: 'middle_unknown'"
    ):
        controller.click(10, 20, button="middle_unknown")


# 4. Right Click & Double Click Tests
@patch("app.tools.desktop.mouse.pyautogui.click")
def test_mouse_right_click(mock_click, controller):
    result = controller.right_click(50, 60)
    mock_click.assert_called_once_with(
        x=50, y=60, button="right", clicks=1, interval=0.0, duration=0.0
    )
    assert result.success is True
    assert result.action == MouseActionType.RIGHT_CLICK


@patch("app.tools.desktop.mouse.pyautogui.doubleClick")
def test_mouse_double_click(mock_double, controller):
    result = controller.double_click(150, 250, button="left", interval=0.2)
    mock_double.assert_called_once_with(
        x=150, y=250, button="left", interval=0.2, duration=0.0
    )
    assert result.success is True
    assert result.action == MouseActionType.DOUBLE_CLICK
    assert result.position.x == 150
    assert result.position.y == 250


@patch("app.tools.desktop.mouse.pyautogui.doubleClick")
def test_mouse_double_click_current_pos(mock_double, controller):
    result = controller.double_click(button="left")
    mock_double.assert_called_once_with(button="left", interval=0.1)
    assert result.success is True
    assert result.position.x == 500
    assert result.position.y == 400


# 5. Scroll Tests
@patch("app.tools.desktop.mouse.pyautogui.scroll")
def test_mouse_scroll_success(mock_scroll, controller):
    result = controller.scroll(-500)
    mock_scroll.assert_called_once_with(-500)
    assert result.success is True
    assert result.action == MouseActionType.SCROLL
    assert result.details["clicks"] == -500
    assert result.details["direction"] == "down"


@patch("app.tools.desktop.mouse.pyautogui.scroll")
def test_mouse_scroll_with_coordinates(mock_scroll, controller):
    result = controller.scroll(300, x=100, y=200)
    mock_scroll.assert_called_once_with(300, x=100, y=200)
    assert result.success is True
    assert result.details["clicks"] == 300
    assert result.details["direction"] == "up"


def test_mouse_scroll_invalid_clicks(controller):
    with pytest.raises(MouseActionError, match="Scroll clicks must be an integer"):
        controller.scroll("three")  # type: ignore


# 6. Coordinate Validation Tests
def test_validate_coordinates_valid(controller):
    x, y = controller.validate_coordinates(100, 200)
    assert x == 100
    assert y == 200


def test_validate_coordinates_none(controller):
    with pytest.raises(
        InvalidCoordinatesError, match="Coordinates \\(x, y\\) cannot be None"
    ):
        controller.validate_coordinates(None, 100)


def test_validate_coordinates_boolean(controller):
    with pytest.raises(InvalidCoordinatesError, match="Coordinates must be integers"):
        controller.validate_coordinates(True, 100)


def test_validate_coordinates_float_non_integer(controller):
    with pytest.raises(
        InvalidCoordinatesError, match="Coordinates must be whole integers"
    ):
        controller.validate_coordinates(10.5, 20)


def test_validate_coordinates_negative(controller):
    with pytest.raises(InvalidCoordinatesError, match="cannot be negative"):
        controller.validate_coordinates(-10, 20)

    with pytest.raises(InvalidCoordinatesError, match="cannot be negative"):
        controller.validate_coordinates(10, -20)


def test_validate_coordinates_out_of_screen_bounds(controller):
    # screen is 1920x1080
    with pytest.raises(InvalidCoordinatesError, match="out of screen bounds"):
        controller.validate_coordinates(1920, 500)

    with pytest.raises(InvalidCoordinatesError, match="out of screen bounds"):
        controller.validate_coordinates(500, 1080)


# 7. Desktop Session / Screen Resolution Unavailable
def test_get_screen_resolution_failure():
    def broken_screen():
        raise Exception("No display server detected")

    ctrl = MouseController(screen_size_provider=broken_screen)
    with pytest.raises(
        DesktopSessionUnavailableError,
        match="Desktop GUI session or screen is unavailable",
    ):
        ctrl.get_screen_resolution()


# 8. Timeout Handling
def test_mouse_timeout_handling(mock_screen, mock_pos):
    def hanging_move(*args, **kwargs):
        time.sleep(1.0)

    with patch("app.tools.desktop.mouse.pyautogui.moveTo", side_effect=hanging_move):
        ctrl = MouseController(
            screen_size_provider=mock_screen,
            position_provider=mock_pos,
            default_timeout=0.1,
        )
        with pytest.raises(MouseTimeoutError, match="timed out"):
            ctrl.move_to(100, 100, duration=0.0, timeout=0.1)


# 9. FailSafe Protection Handling
def test_mouse_failsafe_handling(controller):
    with patch(
        "app.tools.desktop.mouse.pyautogui.moveTo",
        side_effect=pyautogui.FailSafeException("FailSafe"),
    ):
        with pytest.raises(MouseActionError, match="PyAutoGUI fail-safe triggered"):
            controller.move_to(0, 0, duration=0.1)


# 10. Permission Manager Integration
def test_mouse_permission_granted(mock_screen, mock_pos):
    pm = MockPermissionManager(should_approve=True)
    ctrl = MouseController(
        permission_manager=pm,
        screen_size_provider=mock_screen,
        position_provider=mock_pos,
    )
    with patch("app.tools.desktop.mouse.pyautogui.moveTo"):
        res = ctrl.move_to(100, 100)
        assert res.success is True
        assert len(pm.checked_actions) > 0


def test_mouse_permission_denied(mock_screen, mock_pos):
    pm = MockPermissionManager(should_approve=False)
    ctrl = MouseController(
        permission_manager=pm,
        screen_size_provider=mock_screen,
        position_provider=mock_pos,
    )
    with pytest.raises(
        PermissionDeniedException, match="Permission denied for DESKTOP_AUTOMATION"
    ):
        ctrl.move_to(100, 100)


# 11. Model-Driven Action Execution (execute_action)
@patch("app.tools.desktop.mouse.pyautogui.moveTo")
@patch("app.tools.desktop.mouse.pyautogui.click")
@patch("app.tools.desktop.mouse.pyautogui.doubleClick")
@patch("app.tools.desktop.mouse.pyautogui.scroll")
def test_execute_action_model(
    mock_scroll, mock_double, mock_click, mock_move, controller
):
    # GET_POSITION
    req_pos = MouseActionRequest(action=MouseActionType.GET_POSITION)
    res_pos = controller.execute_action(req_pos)
    assert res_pos.success is True
    assert res_pos.position.x == 500

    # MOVE
    req_move = MouseActionRequest(
        action=MouseActionType.MOVE, x=200, y=300, duration=0.1
    )
    res_move = controller.execute_action(req_move)
    assert res_move.success is True
    mock_move.assert_called_once_with(x=200, y=300, duration=0.1)

    # CLICK
    req_click = MouseActionRequest(
        action=MouseActionType.CLICK, x=100, y=150, button=MouseButton.LEFT
    )
    res_click = controller.execute_action(req_click)
    assert res_click.success is True

    # RIGHT_CLICK
    req_rclick = MouseActionRequest(action=MouseActionType.RIGHT_CLICK, x=120, y=160)
    res_rclick = controller.execute_action(req_rclick)
    assert res_rclick.success is True

    # DOUBLE_CLICK
    req_dclick = MouseActionRequest(
        action=MouseActionType.DOUBLE_CLICK, x=140, y=180, interval=0.15
    )
    res_dclick = controller.execute_action(req_dclick)
    assert res_dclick.success is True

    # SCROLL
    req_scroll = MouseActionRequest(
        action=MouseActionType.SCROLL, clicks=10, x=50, y=50
    )
    res_scroll = controller.execute_action(req_scroll)
    assert res_scroll.success is True
    mock_scroll.assert_called_once_with(10, x=50, y=50)
