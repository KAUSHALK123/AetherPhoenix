from unittest.mock import patch

import pytest

from app.tools.desktop.mouse import MouseActionError, MouseController


@patch("app.tools.desktop.mouse.pyautogui.click")
def test_mouse_click_success(mock_click):
    MouseController.click(10, 20, "right")
    mock_click.assert_called_once_with(x=10, y=20, button="right")


@patch("app.tools.desktop.mouse.pyautogui.click")
def test_mouse_click_failure(mock_click):
    mock_click.side_effect = Exception("Click failed")
    with pytest.raises(MouseActionError, match="Failed to click at \\(10, 20\\)"):
        MouseController.click(10, 20)


@patch("app.tools.desktop.mouse.pyautogui.moveTo")
def test_mouse_move_to_success(mock_move):
    MouseController.move_to(100, 200, 0.2)
    mock_move.assert_called_once_with(x=100, y=200, duration=0.2)


@patch("app.tools.desktop.mouse.pyautogui.scroll")
def test_mouse_scroll_success(mock_scroll):
    MouseController.scroll(-500)
    mock_scroll.assert_called_once_with(-500)
