# Keyboard Controller & Desktop Automation

**Version:** 1.0  
**Component:** `app.tools.desktop.keyboard`  
**Owner:** Worker Agent / Desktop Automation Subsystem  
**Milestone:** Sprint 6 – Desktop & Browser Automation  

---

## 1. Overview

The **Keyboard Controller** provides predictable, validated, and auditable keyboard automation capabilities for the Worker Agent via the Desktop Automation Controller (`DesktopTool`).

It enables automated GUI tasks (such as focusing an application, typing text, pressing special keys, or executing complex keyboard shortcut combinations) while strictly adhering to system safety constraints, access permissions, and session validation.

---

## 2. Core Capabilities

1. **Key Press & Hold (`press_key`, `key_down`)**: Single keystrokes or held keys with configurable hold duration and repeat count.
2. **Key Release (`key_up`)**: Clean release of held modifier or character keys.
3. **Controlled Text Typing (`type_text`)**: Safe text entry with configurable per-keystroke intervals and total operation timeouts.
4. **Special Keys (`press_special`)**: Full support for standard special keys (`enter`, `tab`, `backspace`, `escape`, `space`, `delete`, `f1`–`f12`, arrow navigation keys, etc.).
5. **Keyboard Shortcuts (`hotkey`, `shortcut`)**: Multi-key combinations (e.g., `Ctrl+C`, `Ctrl+V`, `Alt+Tab`, `Ctrl+Shift+Esc`) with strict order and key validation.
6. **Input Validation**: Rejection of unknown keys, oversized payloads, null characters, and malformed shortcut combinations.
7. **Desktop Session Verification**: Proactive detection of active desktop displays and graceful failure when running in headless or detached sessions.
8. **Structured Execution Contracts**: Formal Pydantic request/response models (`KeyboardActionRequest`, `KeyboardActionResult`).
9. **Permission Integration**: Enforcement of `PermissionType.DESKTOP_AUTOMATION` through `PermissionManager`.
10. **Auditable Logging**: Redacted/masked payload logging to prevent credential leakage while maintaining execution traceability.

---

## 3. Architecture & Integration

```
 Worker Agent / Workflow Task
            │
            ▼
   Permission Manager ────────► (Verifies DESKTOP_AUTOMATION Permission)
            │
            ▼
      DesktopTool (Tool Registry: "desktop_automation")
            │
            ▼
    KeyboardController
   ┌──────────────────────────────────────────────┐
   │ • Session Check (Active Display?)            │
   │ • Input Validation (Permitted Keys / Length) │
   │ • Timeout Enforcement                        │
   │ • Masked Execution Logging                   │
   └──────────────────────┬───────────────────────┘
                          │
                          ▼
                       PyAutoGUI
                          │
                          ▼
                   Operating System
```

---

## 4. Contracts and Data Models

Contracts are located in `shared/contracts/keyboard.py`.

### `KeyboardActionType`

| Value | Description |
|---|---|
| `press` | Press and release a single key |
| `key_down` | Hold a key down without releasing |
| `key_up` | Release a currently held key |
| `type_text` | Type text string into active window |
| `hotkey` / `shortcut` | Trigger multi-key combination |
| `special_key` | Press a recognized special key |

### `SpecialKey` Enum

Standardized key definitions including:
- **Navigation:** `ENTER`, `RETURN`, `TAB`, `BACKSPACE`, `ESCAPE`, `SPACE`, `DELETE`, `HOME`, `END`, `PAGE_UP`, `PAGE_DOWN`, `UP`, `DOWN`, `LEFT`, `RIGHT`
- **Modifiers:** `CTRL`, `ALT`, `SHIFT`, `WIN`, `COMMAND`, `OPTION`
- **Function Keys:** `F1` through `F12`
- **Locks & Controls:** `CAPS_LOCK`, `NUM_LOCK`, `SCROLL_LOCK`, `PRINT_SCREEN`, `PAUSE`

### `KeyboardActionRequest`

| Field | Type | Default | Description |
|---|---|---|---|
| `action` | `KeyboardActionType` | *Required* | Keyboard action type to execute |
| `key` | `str \| None` | `None` | Key name for single key actions |
| `keys` | `List[str] \| None` | `None` | List of keys for shortcut combinations |
| `text` | `str \| None` | `None` | Text string to type |
| `interval` | `float` | `0.05` | Inter-key delay in seconds |
| `duration` | `float` | `0.0` | Hold duration in seconds |
| `timeout` | `float` | `30.0` | Maximum operation timeout in seconds |

### `KeyboardActionResult`

| Field | Type | Description |
|---|---|---|
| `status` | `str` | `"success"` or `"failed"` |
| `action` | `str` | Name of executed action |
| `details` | `Dict[str, Any]` | Detailed execution metadata (e.g. chars typed, keys) |
| `execution_time_ms` | `float` | Elapsed execution duration in milliseconds |
| `error` | `str \| None` | Diagnostic error message if failed |

---

## 5. Security & Safety Constraints

To protect system integrity and prevent unintended automation side-effects:

- **Permission Enforcement:** Actions executed through `DesktopTool` enforce `PermissionType.DESKTOP_AUTOMATION` via `PermissionManager`.
- **Sensitive Data Redaction:** Execution logs mask raw text input, logging only string length and timing to avoid writing passwords or sensitive tokens to disk logs.
- **Key Whitelisting:** Key names are validated against known printable ASCII characters and `PERMITTED_SPECIAL_KEYS`. Arbitrary strings or injection payloads are rejected before reaching OS drivers.
- **Null-Byte & Length Checks:** Raw strings containing null bytes (`\x00`) or exceeding 50,000 characters are rejected with `InvalidKeyboardActionError`.
- **Timeout Protection:** Estimated typing duration (`length * interval`) is checked against the configured timeout threshold.

---

## 6. Error Handling

The module provides specialized exceptions inheriting from `KeyboardActionError`:

| Exception | Condition |
|---|---|
| `InvalidKeyboardActionError` | Unknown key name, empty shortcut, null-byte injection, invalid payload |
| `DesktopUnavailableError` | Headless environment, display server disconnected, screen size (0, 0) |
| `KeyboardTimeoutError` | Operation duration exceeded configured timeout limit |
| `KeyboardActionError` | Underlying driver or OS execution failure |

---

## 7. Usage Examples

### Direct Controller Usage

```python
from app.tools.desktop.keyboard import KeyboardController, SpecialKey

# 1. Type text
result = KeyboardController.type_text("Hello, World!", interval=0.05)

# 2. Press Enter
KeyboardController.press_special(SpecialKey.ENTER)

# 3. Trigger Keyboard Shortcut (Ctrl+S)
KeyboardController.hotkey("ctrl", "s")

# 4. Key Hold and Release (Shift key)
KeyboardController.key_down("shift")
KeyboardController.press_key("a")
KeyboardController.key_up("shift")
```

### Via DesktopTool Interface

```python
from app.tools.desktop import DesktopTool

desktop_tool = DesktopTool(permission_manager=permission_mgr)

# Type text into focused window
desktop_tool.execute("keyboard_type", {"text": "Workflow completed", "workflow_id": wf_id})

# Press Enter
desktop_tool.execute("keyboard_press", {"key": "enter", "workflow_id": wf_id})

# Keyboard Shortcut
desktop_tool.execute("keyboard_hotkey", {"keys": ["ctrl", "c"], "workflow_id": wf_id})
```

---

## 8. Verification & Testing

Unit tests for the Keyboard Controller are located in `backend/tests/tools/desktop/`:
- `test_keyboard.py`: Key press, key up/down, typing, special keys, shortcuts, invalid keys, timeouts, desktop unavailability.
- `test_desktop_tool.py`: DesktopTool action routing, registration, permission checks, and error propagation.

Run tests using:
```bash
uv run pytest tests/tools/desktop
```
