# Controlled Mouse Controller

**Version:** 1.0  
**Status:** Implemented  
**Milestone:** Sprint 6 – Desktop & Browser Automation  
**Last Updated:** August 2026  

---

## 1. Overview

The **Controlled Mouse Controller** (`MouseController`) provides secure, deterministic, and auditable mouse interaction capabilities for the AetherPhoenix Desktop Automation system.

Operating within the Desktop Controller (`DesktopTool`) and Worker Agent execution architecture, the Mouse Controller enables autonomous agents to perform controlled mouse interactions (cursor tracking, cursor movement, left/right/double clicks, and scrolling) while strictly preventing unrestricted or covert background automation.

---

## 2. Architecture & Execution Flow

Mouse operations are coordinated through the layered tool execution pipeline:

```
                  ┌───────────────────────┐
                  │     Worker Agent      │
                  └──────────┬────────────┘
                             │ (Task Contract)
                             ▼
                  ┌───────────────────────┐
                  │  DesktopToolAdapter   │
                  └──────────┬────────────┘
                             │
                             ▼
                  ┌───────────────────────┐
                  │      DesktopTool      │
                  │ (Desktop Controller)  │
                  └──────────┬────────────┘
                             │
            ┌────────────────┴────────────────┐
            │                                 │
            ▼                                 ▼
┌───────────────────────┐         ┌───────────────────────┐
│   PermissionManager   │         │    MouseController    │
│ (DESKTOP_AUTOMATION)  │         └──────────┬────────────┘
└───────────────────────┘                    │
                                             ├─► Coordinate Validator
                                             ├─► Timeout Guardian
                                             ├─► Session Detector
                                             ├─► Structured Logger
                                             │
                                             ▼
                                  ┌───────────────────────┐
                                  │   PyAutoGUI Engine    │
                                  │  (FailSafe Protected) │
                                  └──────────┬────────────┘
                                             │
                                             ▼
                                  ┌───────────────────────┐
                                  │   Operating System    │
                                  │    Desktop Screen     │
                                  └───────────────────────┘
```

---

## 3. Core Features & Capabilities

### 3.1. Cursor Position Retrieval
- **Method:** `get_position()`
- **Action Name:** `"mouse_get_position"`
- **Description:** Returns the current `(x, y)` coordinate position of the mouse cursor as a structured `MousePosition` model.

### 3.2. Cursor Movement
- **Method:** `move_to(x, y, duration=0.5, timeout=10.0)`
- **Action Name:** `"mouse_move"`
- **Description:** Moves the mouse cursor from its current position to the destination coordinates with controlled trajectory and speed.
- **Constraints:** Target coordinates must reside within valid display boundaries. Movement duration must be non-negative.

### 3.3. Mouse Clicking (Left, Right, Double Click)
- **Methods:**
  - `click(x=None, y=None, button="left", duration=0.0, clicks=1, interval=0.0)`
  - `right_click(x=None, y=None, duration=0.0)`
  - `double_click(x=None, y=None, button="left", interval=0.1, duration=0.0)`
- **Action Names:** `"mouse_click"`, `"mouse_right_click"`, `"mouse_double_click"`
- **Description:** Dispatches physical mouse click events. If `x` and `y` are provided, coordinates are validated before executing the click.

### 3.4. Mouse Scrolling
- **Method:** `scroll(clicks, x=None, y=None)`
- **Action Name:** `"mouse_scroll"`
- **Description:** Generates vertical mouse wheel scroll events. Positive click values scroll upwards; negative click values scroll downwards.

---

## 4. Coordinate Validation & Boundary Enforcement

The `MouseController` enforces strict screen coordinate checks before executing any movement or positional action:

1. **Type & Value Validation:**
   - Coordinates must be numeric integers (`x`, `y`).
   - Floats with fractional values (e.g. `10.5`), booleans, `None`, or string types are rejected with `InvalidCoordinatesError`.

2. **Non-Negative Constraints:**
   - Coordinates cannot be negative (`x >= 0` and `y >= 0`).

3. **Screen Resolution Bounds:**
   - The controller queries the active screen resolution `(width, height)`.
   - Coordinates must satisfy `0 <= x < width` and `0 <= y < height`. Out-of-bounds coordinates raise `InvalidCoordinatesError`.

4. **Desktop Session Availability:**
   - If the system is running in a headless environment without an active GUI display session, a `DesktopSessionUnavailableError` is raised.

---

## 5. Security & Safety Constraints

To prevent unconstrained or unsafe desktop automation, the following constraints are enforced:

- **Permission Enforcement:** All mouse interactions require `PermissionType.DESKTOP_AUTOMATION`. Unapproved requests raise `PermissionDeniedException`.
- **PyAutoGUI Fail-Safe:** `pyautogui.FAILSAFE = True` is unconditionally enabled. Moving the mouse cursor into any screen corner triggers an emergency abort.
- **No Background/Hidden Hooks:** Actions simulate visible user interactions with configurable durations, preventing hidden or unmonitored script execution.
- **Timeout Protection:** Every action executes within a bounded timeout to prevent runaway execution in background threads.

---

## 6. Error Handling Hierarchy

```
DesktopActionError (Base)
├── MouseActionError
│   ├── InvalidCoordinatesError
│   └── MouseTimeoutError
└── DesktopSessionUnavailableError
```

| Exception | Cause |
|---|---|
| `InvalidCoordinatesError` | Negative coordinates, non-integer inputs, or target points outside display dimensions |
| `DesktopSessionUnavailableError` | Missing GUI display server, locked session, or unreadable screen resolution |
| `MouseTimeoutError` | Mouse action execution exceeded configured timeout window |
| `MouseActionError` | General hardware simulation failure or PyAutoGUI fail-safe triggered |
| `PermissionDeniedException` | Missing or rejected `DESKTOP_AUTOMATION` permission |

---

## 7. Data Models (`shared.contracts.desktop`)

### `MouseActionRequest`
```python
class MouseActionRequest(BaseModel):
    action: MouseActionType
    x: Optional[int] = None
    y: Optional[int] = None
    button: MouseButton = MouseButton.LEFT
    clicks: int = 1
    duration: float = 0.5
    interval: float = 0.1
    timeout: float = 10.0
    workflow_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
```

### `MouseActionResult`
```python
class MouseActionResult(BaseModel):
    action: MouseActionType
    success: bool = True
    position: Optional[MousePosition] = None
    execution_time_ms: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime
```

---

## 8. Usage Examples

### 8.1. Direct MouseController Usage

```python
from app.tools.desktop import MouseController

controller = MouseController()

# Get cursor position
pos = controller.get_position()
print(f"Current position: ({pos.x}, {pos.y})")

# Move cursor safely
result = controller.move_to(x=500, y=400, duration=0.3)

# Perform double click
controller.double_click(x=500, y=400, button="left")

# Scroll down
controller.scroll(clicks=-5, x=500, y=400)
```

### 8.2. Execution via Worker Agent & Tool Adapter

```python
from app.agents.worker.agent import WorkerAgent
from app.tools.desktop import register_desktop_tool
from app.tools.registry import ToolRegistry
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus

# Register tool with Worker Agent
registry = ToolRegistry()
worker = WorkerAgent(tool_registry=registry)
register_desktop_tool(registry, worker_agent=worker)

# Execute desktop task
task = Task(
    task_name="Click Submit Button",
    description="Click the submit button at coordinates (600, 750)",
    category=TaskCategory.DESKTOP,
    priority=TaskPriority.HIGH,
    status=TaskStatus.PENDING,
    required_tool="desktop_automation",
    inputs={"action": "mouse_click", "x": 600, "y": 750, "button": "left"},
)

result = await worker.execute(task)
print(f"Task status: {result.success}, output: {result.output}")
```
