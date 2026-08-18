import time
from typing import Any, Dict, List, Set, Union

import pyautogui
from shared.contracts.keyboard import (
    KeyboardActionRequest,
    KeyboardActionResult,
    KeyboardActionType,
    SpecialKey,
)

from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class KeyboardActionError(Exception):
    """Base exception for keyboard automation failures."""

    pass


class InvalidKeyboardActionError(KeyboardActionError):
    """Raised when an invalid, unsupported, or unsafe keyboard action is requested."""

    pass


class DesktopUnavailableError(KeyboardActionError):
    """Raised when the desktop session or display is not accessible."""

    pass


class KeyboardTimeoutError(KeyboardActionError):
    """Raised when a keyboard action exceeds the maximum allowed timeout."""

    pass


# Normalized mapping for common key aliases
KEY_ALIASES: Dict[str, str] = {
    "return": "enter",
    "esc": "escape",
    "del": "delete",
    "ins": "insert",
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "win": "win",
    "windows": "win",
    "cmd": "command",
    "command": "command",
    "opt": "option",
    "option": "option",
    "spacebar": "space",
    "page_up": "pageup",
    "page_down": "pagedown",
    "pgup": "pageup",
    "pgdn": "pagedown",
    "caps_lock": "capslock",
    "num_lock": "numlock",
    "scroll_lock": "scrolllock",
    "prtscr": "printscreen",
    "print_screen": "printscreen",
}

# Permitted special keys
PERMITTED_SPECIAL_KEYS: Set[str] = {key.value for key in SpecialKey} | {
    "enter",
    "return",
    "backspace",
    "tab",
    "escape",
    "esc",
    "space",
    "delete",
    "del",
    "insert",
    "up",
    "down",
    "left",
    "right",
    "home",
    "end",
    "pageup",
    "pagedown",
    "capslock",
    "numlock",
    "scrolllock",
    "printscreen",
    "pause",
    "ctrl",
    "ctrlleft",
    "ctrlright",
    "alt",
    "altleft",
    "altright",
    "shift",
    "shiftleft",
    "shiftright",
    "win",
    "winleft",
    "winright",
    "command",
    "option",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
}


def _get_pyautogui_keys() -> Set[str]:
    """Retrieves all recognized PyAutoGUI keys if available."""
    try:
        return set(pyautogui.KEYBOARD_KEYS)
    except Exception:
        return set()


PYAUTOGUI_KEYS: Set[str] = _get_pyautogui_keys()


class KeyboardController:
    """
    Controlled Keyboard Controller providing validated, auditable,
    and safe keyboard automation for the Worker Agent via DesktopTool.
    """

    @classmethod
    def check_desktop_session(cls) -> None:
        """
        Validates that an active desktop session is available.
        Raises DesktopUnavailableError if the display or session is inaccessible.
        """
        try:
            size = pyautogui.size()
            if not size or size[0] <= 0 or size[1] <= 0:
                raise DesktopUnavailableError(
                    "Desktop display session unavailable or invalid screen resolution."
                )
        except DesktopUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Desktop session check failed: {e}")
            raise DesktopUnavailableError(
                f"Active desktop session is not available: {e}"
            ) from e

    @classmethod
    def normalize_key(cls, key: str) -> str:
        """
        Normalizes a key name to standard lowercase form and resolves aliases.
        """
        if not key or not isinstance(key, str):
            raise InvalidKeyboardActionError("Key must be a non-empty string.")
        cleaned = key.strip().lower()
        return KEY_ALIASES.get(cleaned, cleaned)

    @classmethod
    def validate_key(cls, key: str) -> str:
        """
        Validates whether a single key is supported and safe to press.
        Returns the normalized key name or raises InvalidKeyboardActionError.
        """
        normalized = cls.normalize_key(key)

        # Allow single printable ASCII characters
        if len(normalized) == 1 and normalized.isprintable():
            return normalized

        # Allow valid special keys and PyAutoGUI keys
        if normalized in PERMITTED_SPECIAL_KEYS or normalized in PYAUTOGUI_KEYS:
            return normalized

        logger.warning(f"Rejected invalid key: '{key}'")
        raise InvalidKeyboardActionError(
            f"Invalid or unsupported key: '{key}'. Key is not permitted."
        )

    @classmethod
    def validate_shortcut(cls, keys: Union[List[str], tuple]) -> List[str]:
        """
        Validates a list of shortcut / hotkey key combinations.
        """
        if not keys or len(keys) == 0:
            raise InvalidKeyboardActionError(
                "Shortcut key combination cannot be empty."
            )

        if len(keys) > 6:
            raise InvalidKeyboardActionError(
                f"Shortcut key combination too long ({len(keys)} keys). Max is 6."
            )

        validated_keys: List[str] = []
        for k in keys:
            if not isinstance(k, str):
                raise InvalidKeyboardActionError(
                    f"Invalid key type in shortcut: {type(k).__name__}"
                )
            validated_keys.append(cls.validate_key(k))

        return validated_keys

    @classmethod
    def validate_text(cls, text: str) -> str:
        """
        Validates text input for typing operations.
        Ensures length constraints and checks for null bytes.
        """
        if text is None or not isinstance(text, str):
            raise InvalidKeyboardActionError("Text input must be a valid string.")

        if "\x00" in text:
            raise InvalidKeyboardActionError(
                "Text input contains invalid null byte characters."
            )

        max_length = 50000
        if len(text) > max_length:
            raise InvalidKeyboardActionError(
                f"Text length exceeds maximum allowed limit of {max_length} chars."
            )

        return text

    @classmethod
    def type_text(
        cls, text: str, interval: float = 0.05, timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Types text into the active focused application with controlled interval.
        Audits the operation with masked content length for security.
        """
        start_time = time.perf_counter()
        valid_text = cls.validate_text(text)
        cls.check_desktop_session()

        # Check estimated duration vs timeout
        estimated_duration = len(valid_text) * interval
        if estimated_duration > timeout:
            raise KeyboardTimeoutError(
                f"Typing estimated duration ({estimated_duration:.1f}s) "
                f"exceeds timeout ({timeout:.1f}s)."
            )

        logger.info(
            f"Keyboard typing text "
            f"(length: {len(valid_text)} chars, interval: {interval}s)"
        )
        try:
            pyautogui.write(valid_text, interval=interval)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "success",
                "action": "keyboard_type",
                "characters_typed": len(valid_text),
                "interval": interval,
                "execution_time_ms": round(elapsed_ms, 2),
            }
        except KeyboardActionError:
            raise
        except Exception as e:
            logger.error(f"Keyboard type_text failed: {e}")
            raise KeyboardActionError("Failed to type text") from e

    @classmethod
    def press_key(
        cls,
        key: str,
        duration: float = 0.0,
        presses: int = 1,
        interval: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Presses and releases an individual key with optional duration and repetition.
        """
        start_time = time.perf_counter()
        valid_key = cls.validate_key(key)
        cls.check_desktop_session()

        logger.info(
            f"Keyboard press key: '{valid_key}' "
            f"(presses={presses}, duration={duration}s)"
        )
        try:
            if duration > 0.0:
                for _ in range(presses):
                    pyautogui.keyDown(valid_key)
                    time.sleep(duration)
                    pyautogui.keyUp(valid_key)
                    if interval > 0.0:
                        time.sleep(interval)
            else:
                pyautogui.press(valid_key, presses=presses, interval=interval)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "success",
                "action": "keyboard_press",
                "key": valid_key,
                "presses": presses,
                "duration": duration,
                "execution_time_ms": round(elapsed_ms, 2),
            }
        except KeyboardActionError:
            raise
        except Exception as e:
            logger.error(f"Keyboard press failed for '{valid_key}': {e}")
            raise KeyboardActionError(f"Failed to press key: {valid_key}") from e

    @classmethod
    def key_down(cls, key: str) -> Dict[str, Any]:
        """
        Holds down an individual key without releasing.
        """
        start_time = time.perf_counter()
        valid_key = cls.validate_key(key)
        cls.check_desktop_session()

        logger.info(f"Keyboard key_down: '{valid_key}'")
        try:
            pyautogui.keyDown(valid_key)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "success",
                "action": "keyboard_down",
                "key": valid_key,
                "execution_time_ms": round(elapsed_ms, 2),
            }
        except KeyboardActionError:
            raise
        except Exception as e:
            logger.error(f"Keyboard key_down failed for '{valid_key}': {e}")
            raise KeyboardActionError(f"Failed to hold key: {valid_key}") from e

    @classmethod
    def key_up(cls, key: str) -> Dict[str, Any]:
        """
        Releases a held key.
        """
        start_time = time.perf_counter()
        valid_key = cls.validate_key(key)
        cls.check_desktop_session()

        logger.info(f"Keyboard key_up: '{valid_key}'")
        try:
            pyautogui.keyUp(valid_key)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "success",
                "action": "keyboard_up",
                "key": valid_key,
                "execution_time_ms": round(elapsed_ms, 2),
            }
        except KeyboardActionError:
            raise
        except Exception as e:
            logger.error(f"Keyboard key_up failed for '{valid_key}': {e}")
            raise KeyboardActionError(f"Failed to release key: {valid_key}") from e

    @classmethod
    def hotkey(cls, *keys: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Executes a keyboard shortcut combination (e.g. Ctrl+C, Alt+Tab).
        """
        start_time = time.perf_counter()
        validated_keys = cls.validate_shortcut(list(keys))
        cls.check_desktop_session()

        shortcut_str = "+".join(validated_keys)
        logger.info(f"Keyboard hotkey: {shortcut_str}")
        try:
            pyautogui.hotkey(*validated_keys)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "success",
                "action": "keyboard_hotkey",
                "keys": validated_keys,
                "shortcut": shortcut_str,
                "execution_time_ms": round(elapsed_ms, 2),
            }
        except KeyboardActionError:
            raise
        except Exception as e:
            logger.error(f"Keyboard hotkey failed for {validated_keys}: {e}")
            raise KeyboardActionError(
                f"Failed to execute hotkey: {shortcut_str}"
            ) from e

    @classmethod
    def shortcut(cls, keys: List[str], timeout: float = 30.0) -> Dict[str, Any]:
        """
        Executes a keyboard shortcut combination specified as a list.
        """
        return cls.hotkey(*keys, timeout=timeout)

    @classmethod
    def press_special(
        cls, special_key: Union[str, SpecialKey], duration: float = 0.0
    ) -> Dict[str, Any]:
        """
        Presses a standardized special key (e.g. enter, tab, backspace, esc, space).
        """
        key_str = (
            special_key.value
            if isinstance(special_key, SpecialKey)
            else str(special_key)
        )
        return cls.press_key(key=key_str, duration=duration)

    @classmethod
    def execute_action(
        cls, request: Union[KeyboardActionRequest, Dict[str, Any]]
    ) -> KeyboardActionResult:
        """
        Executes a validated keyboard action and returns KeyboardActionResult.
        """
        start_time = time.perf_counter()

        if isinstance(request, dict):
            req = KeyboardActionRequest.model_validate(request)
        else:
            req = request

        action_type = req.action
        try:
            if action_type in (
                KeyboardActionType.PRESS,
                KeyboardActionType.SPECIAL_KEY,
            ):
                if not req.key:
                    raise InvalidKeyboardActionError(
                        f"Action '{action_type}' requires 'key' parameter."
                    )
                details = cls.press_key(
                    key=req.key,
                    duration=req.duration,
                )
            elif action_type == KeyboardActionType.KEY_DOWN:
                if not req.key:
                    raise InvalidKeyboardActionError(
                        "Action 'key_down' requires 'key' parameter."
                    )
                details = cls.key_down(key=req.key)
            elif action_type == KeyboardActionType.KEY_UP:
                if not req.key:
                    raise InvalidKeyboardActionError(
                        "Action 'key_up' requires 'key' parameter."
                    )
                details = cls.key_up(key=req.key)
            elif action_type == KeyboardActionType.TYPE_TEXT:
                if req.text is None:
                    raise InvalidKeyboardActionError(
                        "Action 'type_text' requires 'text' parameter."
                    )
                details = cls.type_text(
                    text=req.text,
                    interval=req.interval,
                    timeout=req.timeout,
                )
            elif action_type in (
                KeyboardActionType.HOTKEY,
                KeyboardActionType.SHORTCUT,
            ):
                keys = req.keys or ([req.key] if req.key else [])
                if not keys:
                    raise InvalidKeyboardActionError(
                        f"Action '{action_type}' requires 'keys' parameter."
                    )
                details = cls.hotkey(*keys, timeout=req.timeout)
            else:
                raise InvalidKeyboardActionError(
                    f"Unsupported keyboard action: {action_type}"
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            act_str = str(
                action_type.value if hasattr(action_type, "value") else action_type
            )
            return KeyboardActionResult(
                status="success",
                action=act_str,
                details=details,
                execution_time_ms=round(elapsed_ms, 2),
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Keyboard action '{action_type}' failed: {e}")
            act_str = str(
                action_type.value if hasattr(action_type, "value") else action_type
            )
            return KeyboardActionResult(
                status="failed",
                action=act_str,
                details={},
                execution_time_ms=round(elapsed_ms, 2),
                error=str(e),
            )
