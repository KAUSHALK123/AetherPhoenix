from unittest.mock import patch

import pytest
from shared.contracts.keyboard import (
    KeyboardActionRequest,
    KeyboardActionResult,
    KeyboardActionType,
    SpecialKey,
)

from app.tools.desktop.keyboard import (
    DesktopUnavailableError,
    InvalidKeyboardActionError,
    KeyboardActionError,
    KeyboardController,
    KeyboardTimeoutError,
)


@pytest.fixture(autouse=True)
def mock_desktop_session():
    """Ensure desktop session check passes by default across tests."""
    with patch("app.tools.desktop.keyboard.pyautogui.size", return_value=(1920, 1080)):
        yield


# --- Single Key Press Tests ---


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_single_character(mock_press):
    result = KeyboardController.press_key("a")
    mock_press.assert_called_once_with("a", presses=1, interval=0.0)
    assert result["status"] == "success"
    assert result["action"] == "keyboard_press"
    assert result["key"] == "a"


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_uppercase_normalized(mock_press):
    result = KeyboardController.press_key("A")
    mock_press.assert_called_once_with("a", presses=1, interval=0.0)
    assert result["status"] == "success"
    assert result["key"] == "a"


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_number_and_symbol(mock_press):
    KeyboardController.press_key("1")
    mock_press.assert_called_with("1", presses=1, interval=0.0)


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_failure(mock_press):
    mock_press.side_effect = Exception("OS driver error")
    with pytest.raises(KeyboardActionError, match="Failed to press key: a"):
        KeyboardController.press_key("a")


# --- Key Down & Key Up Tests ---


@patch("app.tools.desktop.keyboard.pyautogui.keyDown")
def test_keyboard_key_down(mock_key_down):
    result = KeyboardController.key_down("shift")
    mock_key_down.assert_called_once_with("shift")
    assert result["status"] == "success"
    assert result["action"] == "keyboard_down"
    assert result["key"] == "shift"


@patch("app.tools.desktop.keyboard.pyautogui.keyDown")
def test_keyboard_key_down_failure(mock_key_down):
    mock_key_down.side_effect = Exception("Hold failure")
    with pytest.raises(KeyboardActionError, match="Failed to hold key: ctrl"):
        KeyboardController.key_down("ctrl")


@patch("app.tools.desktop.keyboard.pyautogui.keyUp")
def test_keyboard_key_up(mock_key_up):
    result = KeyboardController.key_up("shift")
    mock_key_up.assert_called_once_with("shift")
    assert result["status"] == "success"
    assert result["action"] == "keyboard_up"
    assert result["key"] == "shift"


@patch("app.tools.desktop.keyboard.pyautogui.keyUp")
def test_keyboard_key_up_failure(mock_key_up):
    mock_key_up.side_effect = Exception("Release failure")
    with pytest.raises(KeyboardActionError, match="Failed to release key: alt"):
        KeyboardController.key_up("alt")


# --- Text Typing Tests ---


@patch("app.tools.desktop.keyboard.pyautogui.write")
def test_keyboard_type_text(mock_write):
    result = KeyboardController.type_text("Hello World", interval=0.1)
    mock_write.assert_called_once_with("Hello World", interval=0.1)
    assert result["status"] == "success"
    assert result["action"] == "keyboard_type"
    assert result["characters_typed"] == 11
    assert result["interval"] == 0.1
    assert "execution_time_ms" in result


@patch("app.tools.desktop.keyboard.pyautogui.write")
def test_keyboard_type_text_failure(mock_write):
    mock_write.side_effect = Exception("Write failed")
    with pytest.raises(KeyboardActionError, match="Failed to type text"):
        KeyboardController.type_text("Hello")


def test_keyboard_type_text_null_byte_rejection():
    with pytest.raises(InvalidKeyboardActionError, match="contains invalid null byte"):
        KeyboardController.type_text("malicious\x00input")


def test_keyboard_type_text_length_limit():
    huge_text = "a" * 50001
    with pytest.raises(
        InvalidKeyboardActionError, match="exceeds maximum allowed limit"
    ):
        KeyboardController.type_text(huge_text)


def test_keyboard_type_text_timeout():
    long_text = "a" * 1000
    with pytest.raises(
        KeyboardTimeoutError, match="estimated duration .* exceeds timeout"
    ):
        KeyboardController.type_text(long_text, interval=0.1, timeout=5.0)


# --- Special Keys Tests (Enter, Backspace, Tab, Esc, Space, Arrows, Function keys) ---


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_enter(mock_press):
    result = KeyboardController.press_key("enter")
    mock_press.assert_called_once_with("enter", presses=1, interval=0.0)
    assert result["status"] == "success"
    assert result["key"] == "enter"


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_return_alias(mock_press):
    result = KeyboardController.press_key("return")
    mock_press.assert_called_once_with("enter", presses=1, interval=0.0)
    assert result["key"] == "enter"


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_backspace(mock_press):
    result = KeyboardController.press_key("backspace")
    mock_press.assert_called_once_with("backspace", presses=1, interval=0.0)
    assert result["key"] == "backspace"


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_special_keys(mock_press):
    special_keys = [
        "tab",
        "escape",
        "space",
        "delete",
        "up",
        "down",
        "left",
        "right",
        "f5",
        "home",
        "end",
    ]
    for k in special_keys:
        KeyboardController.press_key(k)
        mock_press.assert_called_with(k, presses=1, interval=0.0)


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_keyboard_press_special_method(mock_press):
    result = KeyboardController.press_special(SpecialKey.ENTER)
    mock_press.assert_called_once_with("enter", presses=1, interval=0.0)
    assert result["status"] == "success"


# --- Keyboard Shortcuts & Combinations Tests ---


@patch("app.tools.desktop.keyboard.pyautogui.hotkey")
def test_keyboard_hotkey(mock_hotkey):
    result = KeyboardController.hotkey("ctrl", "c")
    mock_hotkey.assert_called_once_with("ctrl", "c")
    assert result["status"] == "success"
    assert result["action"] == "keyboard_hotkey"
    assert result["shortcut"] == "ctrl+c"
    assert result["keys"] == ["ctrl", "c"]


@patch("app.tools.desktop.keyboard.pyautogui.hotkey")
def test_keyboard_shortcut_three_keys(mock_hotkey):
    result = KeyboardController.shortcut(["ctrl", "shift", "esc"])
    mock_hotkey.assert_called_once_with("ctrl", "shift", "escape")
    assert result["status"] == "success"
    assert result["shortcut"] == "ctrl+shift+escape"


@patch("app.tools.desktop.keyboard.pyautogui.hotkey")
def test_keyboard_hotkey_failure(mock_hotkey):
    mock_hotkey.side_effect = Exception("Hotkey failed")
    with pytest.raises(KeyboardActionError, match="Failed to execute hotkey: ctrl\\+v"):
        KeyboardController.hotkey("ctrl", "v")


def test_keyboard_hotkey_empty_rejected():
    with pytest.raises(
        InvalidKeyboardActionError, match="Shortcut key combination cannot be empty"
    ):
        KeyboardController.hotkey()


def test_keyboard_hotkey_too_long_rejected():
    with pytest.raises(InvalidKeyboardActionError, match="too long"):
        KeyboardController.shortcut(["ctrl", "alt", "shift", "win", "a", "b", "c"])


# --- Invalid Key Rejection Tests ---


def test_keyboard_invalid_key_rejected():
    with pytest.raises(
        InvalidKeyboardActionError,
        match="Invalid or unsupported key: 'invalid_super_key_999'",
    ):
        KeyboardController.press_key("invalid_super_key_999")


def test_keyboard_empty_key_rejected():
    with pytest.raises(
        InvalidKeyboardActionError, match="Key must be a non-empty string"
    ):
        KeyboardController.press_key("")


def test_keyboard_non_string_key_rejected():
    with pytest.raises(
        InvalidKeyboardActionError, match="Key must be a non-empty string"
    ):
        KeyboardController.press_key(None)  # type: ignore


# --- Desktop Session Unavailable Tests ---


def test_keyboard_desktop_session_unavailable():
    with patch("app.tools.desktop.keyboard.pyautogui.size", return_value=(0, 0)):
        with pytest.raises(
            DesktopUnavailableError, match="Desktop display session unavailable"
        ):
            KeyboardController.press_key("a")


def test_keyboard_desktop_session_exception():
    with patch(
        "app.tools.desktop.keyboard.pyautogui.size",
        side_effect=Exception("Display connection lost"),
    ):
        with pytest.raises(
            DesktopUnavailableError, match="Active desktop session is not available"
        ):
            KeyboardController.press_key("a")


# --- Duration & Multi-press Tests ---


@patch("app.tools.desktop.keyboard.pyautogui.keyDown")
@patch("app.tools.desktop.keyboard.pyautogui.keyUp")
@patch("time.sleep")
def test_keyboard_press_with_duration(mock_sleep, mock_key_up, mock_key_down):
    result = KeyboardController.press_key("enter", duration=0.5, presses=2)
    assert mock_key_down.call_count == 2
    assert mock_key_up.call_count == 2
    mock_sleep.assert_called_with(0.5)
    assert result["duration"] == 0.5
    assert result["presses"] == 2


# --- Structured execute_action Tests ---


@patch("app.tools.desktop.keyboard.pyautogui.write")
def test_execute_action_type_text(mock_write):
    request = KeyboardActionRequest(
        action=KeyboardActionType.TYPE_TEXT,
        text="Hello World",
        interval=0.05,
    )
    result = KeyboardController.execute_action(request)
    assert isinstance(result, KeyboardActionResult)
    assert result.status == "success"
    assert result.action == "type_text"
    assert result.details["characters_typed"] == 11
    assert result.execution_time_ms >= 0


@patch("app.tools.desktop.keyboard.pyautogui.press")
def test_execute_action_press(mock_press):
    request = KeyboardActionRequest(
        action=KeyboardActionType.PRESS,
        key="enter",
    )
    result = KeyboardController.execute_action(request)
    assert result.status == "success"
    assert result.action == "press"
    mock_press.assert_called_once_with("enter", presses=1, interval=0.0)


@patch("app.tools.desktop.keyboard.pyautogui.hotkey")
def test_execute_action_hotkey(mock_hotkey):
    request = KeyboardActionRequest(
        action=KeyboardActionType.HOTKEY,
        keys=["ctrl", "c"],
    )
    result = KeyboardController.execute_action(request)
    assert result.status == "success"
    assert result.action == "hotkey"
    mock_hotkey.assert_called_once_with("ctrl", "c")


def test_execute_action_invalid_returns_failed_result():
    request = KeyboardActionRequest(
        action=KeyboardActionType.PRESS,
        key="unsupported_key_xyz",
    )
    result = KeyboardController.execute_action(request)
    assert result.status == "failed"
    assert "Invalid or unsupported key" in result.error
