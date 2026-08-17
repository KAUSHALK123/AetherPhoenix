# Desktop Controller & Automation Architecture

**Version:** 1.0  
**Category:** DESKTOP_AUTOMATION  
**Owner:** Worker Agent / AI Runtime Team  

---

## Overview

The **Desktop Controller** provides a controlled, sandboxed abstraction for interacting with the user's desktop environment. It coordinates desktop automation capabilities without placing OS-specific automation logic directly inside the Worker Agent.

The Desktop Controller acts as the single source of truth for:
- Desktop session management and process tracking
- Permitted application launch and termination
- Window discovery, inspection, and focus control
- Desktop state snapshot retrieval (active window, open windows, screen resolution, processes)
- Keyboard and mouse input coordination
- Permission verification via the `PermissionManager`
- Structured audit logging and metrics capture

---

## Architecture

```
Worker Agent / Task
        │
        ▼
DesktopToolAdapter (BaseToolAdapter)
        │
        ▼
DesktopController
   ├── Permission Verification (PermissionType.DESKTOP_AUTOMATION)
   ├── DesktopSessionManager (Session Lifecycle, Limits, Timeouts)
   ├── ApplicationController (Launch, Terminate, Process Registry)
   ├── Window Manager (Discovery, Focus, Active Window Info)
   ├── Input Controllers (MouseController, KeyboardController)
   └── Structured Execution Logging (get_logger)
        │
        ▼
Operating System (pywinauto / Windows API / pyautogui)
```

---

## Key Features

1. **Desktop Session Management (`DesktopSession`, `DesktopSessionManager`)**:
   - Creates scoped execution boundaries for tasks or workflows.
   - Enforces configurable session lifetimes (`session_timeout_seconds`) and idle limits (`idle_timeout_seconds`).
   - Tracks launched process IDs and limits concurrent applications (`max_applications`).

2. **Permitted Application Management (`ApplicationController`)**:
   - Safely launches permitted applications with argument and path validation.
   - Prohibits unsafe commands (e.g., shell command execution, arbitrary interpreters) to enforce security boundaries.
   - Supports graceful and forced application termination by process ID or window title.
   - Handles unavailable applications and missing binaries with explicit error reporting.

3. **Window Management & Discovery**:
   - Enumerates visible top-level windows with handles, titles, process IDs, visibility flags, class names, and bounding boxes (`WindowBounds`).
   - Supports filtering by title substrings or process IDs.
   - Retrieves active foreground window information gracefully.
   - Focuses target windows by title, handle, or PID with timeout enforcement.

4. **Desktop State Inspection (`DesktopState`)**:
   - Returns a comprehensive snapshot including screen resolution, active foreground window, open windows list, running session processes, and session status.

5. **Security & Permission Integration**:
   - Strictly enforces `PermissionType.DESKTOP_AUTOMATION` using `PermissionManager`.
   - Rejects unpermitted desktop actions with `PermissionDeniedException`.
   - Never executes arbitrary system commands directly or bypasses OS permissions.

6. **Tool Registry & Worker Adapter Integration**:
   - Exposes `DesktopTool` and `DesktopToolAdapter` (`BaseToolAdapter`) in `ToolRegistry` under `desktop_automation`.
   - Translates worker `Task` contracts into desktop operations and produces structured `ExecutionResult` outputs.

7. **Resilient Error Handling Hierarchy**:
   - `DesktopError`
     - `DesktopSessionError` (`DesktopSessionNotFoundError`, `DesktopSessionExpiredError`)
     - `ApplicationLaunchError`, `ApplicationNotFoundError`, `ApplicationTerminationError`, `ApplicationUnavailableError`
     - `WindowNotFoundError`, `WindowFocusError`
     - `DesktopTimeoutError`
     - `DesktopSecurityError`

---

## Data Models

### `DesktopSessionConfig`
| Field | Type | Default | Description |
|---|---|---|---|
| `session_timeout_seconds` | `float` | `300.0` | Maximum total session duration |
| `idle_timeout_seconds` | `float` | `120.0` | Inactivity threshold before session expiry |
| `max_applications` | `int` | `10` | Maximum concurrent tracked applications |
| `allowed_applications` | `List[str] \| None` | `None` | Optional explicit allowlist of application names |

### `WindowInfo`
| Field | Type | Description |
|---|---|---|
| `handle` | `int \| str` | OS window handle identifier |
| `title` | `str` | Window title text |
| `process_id` | `int \| None` | Owning process ID |
| `is_visible` | `bool` | Whether window is currently visible |
| `is_active` | `bool` | Whether window currently has foreground focus |
| `bounds` | `WindowBounds \| None` | Window coordinates (x, y, width, height) |
| `class_name` | `str \| None` | OS window class name |

### `ApplicationInfo`
| Field | Type | Description |
|---|---|---|
| `process_id` | `int` | Operating system process ID |
| `name` | `str` | Application executable name |
| `path` | `str \| None` | Executable filesystem path |
| `title` | `str \| None` | Associated application title |
| `status` | `str` | Application execution status (`running`, etc.) |
| `launched_at` | `datetime` | Launch UTC timestamp |

### `DesktopState`
| Field | Type | Description |
|---|---|---|
| `screen_resolution` | `ScreenResolution` | Display width and height in pixels |
| `active_window` | `WindowInfo \| None` | Current foreground window |
| `open_windows` | `List[WindowInfo]` | List of visible open desktop windows |
| `running_applications` | `List[ApplicationInfo]` | Applications tracked within the active session |
| `session` | `DesktopSessionInfo \| None` | Active session metadata |
| `timestamp` | `datetime` | Snapshot UTC timestamp |

---

## Usage Example

```python
from app.core.permissions.manager import PermissionManager
from app.tools.desktop import DesktopController, DesktopSessionConfig

# Initialize controller with security manager
permission_manager = PermissionManager()
controller = DesktopController(permission_manager=permission_manager)

# 1. Start a managed desktop session
session = await controller.start_session(
    config=DesktopSessionConfig(session_timeout_seconds=600.0)
)

# 2. Launch a permitted application
app_info = await controller.launch_application(
    app_path="notepad.exe",
    timeout=5.0
)

# 3. Discover and focus the window
windows = await controller.get_windows(filter_title="Notepad")
focused = await controller.focus_window(title="Notepad")

# 4. Perform controlled input simulation
await controller.type_text("Automated report content")

# 5. Capture desktop state
state = await controller.get_desktop_state()

# 6. Terminate application and close session
await controller.close_application(pid=app_info.process_id)
await controller.end_session()
```
