from unittest.mock import patch

import pytest

from app.tools.desktop.keyboard import KeyboardActionError, KeyboardController


@patch("app.tools.desktop.keyboard.pyautogui.write")
def test_keyboard_type_text(mock_write):
    KeyboardController.type_text("Hello World", interval=0.1)
    mock_write.assert_called_once_with("Hello World", interval=0.1)


@patch("app.tools.desktop.keyboard.pyautogui.write")
def test_keyboard_type_text_failure(mock_write):
    mock_write.side_effect = Exception("Write failed")
    with pytest.raises(KeyboardActionError, match="Failed to type text"):
        KeyboardController.type_text("Hello")


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_key(mock_press):
    KeyboardController.press_key("enter")
    mock_press.assert_called_once_with("enter")


@patch("app.tools.desktop.keyboard.pyautogui.hotkey")
def test_keyboard_hotkey(mock_hotkey):
    KeyboardController.hotkey("ctrl", "c")
    mock_hotkey.assert_called_once_with("ctrl", "c")
