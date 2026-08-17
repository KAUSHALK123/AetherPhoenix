from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KeyboardActionType(str, Enum):
    """Supported keyboard action types."""

    PRESS = "press"
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    SHORTCUT = "shortcut"
    SPECIAL_KEY = "special_key"


class SpecialKey(str, Enum):
    """Standardized special key identifiers."""

    ENTER = "enter"
    RETURN = "return"
    BACKSPACE = "backspace"
    TAB = "tab"
    ESCAPE = "escape"
    ESC = "esc"
    SPACE = "space"
    DELETE = "delete"
    DEL = "del"
    INSERT = "insert"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    HOME = "home"
    END = "end"
    PAGE_UP = "pageup"
    PAGE_DOWN = "pagedown"
    CAPS_LOCK = "capslock"
    NUM_LOCK = "numlock"
    SCROLL_LOCK = "scrolllock"
    PRINT_SCREEN = "printscreen"
    PAUSE = "pause"
    CTRL = "ctrl"
    CTRL_L = "ctrlleft"
    CTRL_R = "ctrlright"
    ALT = "alt"
    ALT_L = "altleft"
    ALT_R = "altright"
    SHIFT = "shift"
    SHIFT_L = "shiftleft"
    SHIFT_R = "shiftright"
    WIN = "win"
    WIN_L = "winleft"
    WIN_R = "winright"
    COMMAND = "command"
    OPTION = "option"
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"


class KeyboardActionRequest(BaseModel):
    """Input payload contract for a controlled keyboard action."""

    action: KeyboardActionType = Field(
        ..., description="The keyboard action type to perform"
    )
    key: Optional[str] = Field(
        default=None, description="Single key name or special key identifier"
    )
    keys: Optional[List[str]] = Field(
        default=None, description="List of keys for hotkey / shortcut combinations"
    )
    text: Optional[str] = Field(
        default=None, description="Text string to type into the active application"
    )
    interval: float = Field(
        default=0.05,
        ge=0.0,
        le=5.0,
        description="Delay in seconds between keystrokes when typing text",
    )
    duration: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Duration in seconds to hold a key when pressing",
    )
    timeout: float = Field(
        default=30.0,
        ge=0.1,
        le=300.0,
        description="Maximum execution timeout in seconds",
    )


class KeyboardActionResult(BaseModel):
    """Structured execution output for keyboard operations."""

    status: str = Field(
        default="success", description="Status outcome: 'success' or 'failed'"
    )
    action: str = Field(..., description="Action that was executed")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata and details"
    )
    execution_time_ms: float = Field(
        default=0.0, description="Execution elapsed time in milliseconds"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if operation failed"
    )
