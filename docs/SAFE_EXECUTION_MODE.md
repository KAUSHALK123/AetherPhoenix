# Safe Execution Mode Architecture & Specification

## Overview
**Safe Execution Mode** establishes a security perimeter and policy enforcement layer around all browser and desktop automation capabilities executed by AetherPhoenix Worker Agents.

Automated agent actions cannot freely execute unvalidated or dangerous system operations. Safe Execution Mode enforces safety by evaluating operations before execution and failing closed.

```
Planner
  ↓
Worker Agent
  ↓
Automation Request (Browser/Desktop)
  ↓
SafeExecutionPolicy.evaluate()
  ↓
Permission Check & Execution Limit Validation
  ↓
Allowed?
 ├── YES (Low-Risk / Pre-approved) ──> Execute Action
 └── NO (High-Risk / Blocked / Unapproved) ──> Block Action & Audit Log
```

---

## Execution Modes & Risk Behavior

| Execution Mode | Safe / Low Risk Actions | Medium Risk Actions | High Risk Actions | Critical / Blocked Actions |
|---|---|---|---|---|
| **SAFE** | Allowed Automatically | Requires Approval | Requires Approval | **Blocked** |
| **ASSISTED** | Allowed Automatically | Allowed Automatically | Requires Approval | **Blocked** |
| **AUTONOMOUS** | Allowed Automatically | Allowed Automatically | Allowed Automatically | **Blocked** |

---

## Action Classification

### Low-Risk Operations
- **Browser**: `extract_content`, `capture_screenshot`, `start_session`, `close_session`
- **Desktop**: `get_windows`, `get_active_window`, `get_desktop_state`, `mouse_get_position`, `mouse_move`, `mouse_scroll`, `focus_window`, `resize_window`, `move_window`, `minimize_window`, `maximize_window`, `restore_window`
- **Files**: `file_read`

### Medium-Risk Operations
- **Browser**: `navigate`, `interact` (click, fill)
- **Desktop**: `mouse_click`, `mouse_double_click`, `mouse_right_click`, `mouse_drag`, `keyboard_press`, `keyboard_type`, `keyboard_write`
- **Files**: `file_write`

### High-Risk Operations
- **Desktop**: `launch_app`, `terminate_app`, `close_window`, `keyboard_hotkey`
- **Files**: `file_delete`

### Critical & Restricted Operations (Blocked Unconditionally in Safe Mode)
- **Restricted Hotkeys**: `Alt+F4`, `Ctrl+Alt+Del`, `Win+L`, `Win+R`, `Ctrl+Shift+Esc`
- **Restricted URL Schemes**: `file://`, `gopher://`, `data://`, `javascript:`
- **Destructive Commands**: `rm -rf`, `format`, `del /f`, `reg delete`, `drop database`

---

## Safety Limits & Guardrails

1. **Per-Task Action Rate Limits**:
   - `PermissionManager(max_actions_per_task=100)` prevents infinite execution loops or malicious spamming of inputs.
2. **Timeout Enforcement**:
   - Operations that require user confirmation automatically expire and fail closed after `PERMISSION_TIMEOUT_SECONDS` (default: 30s).
3. **Audit Logging & EventBus Notifications**:
   - Every blocked or high-risk attempt publishes `PERMISSION_REJECTED` or `PERMISSION_REQUESTED` events through the system `EventBus`.

---

## Tool Integrations

- **`BrowserController`**: Validates destination URLs against forbidden schemes and invokes `PermissionManager.check_permission` before executing navigations and DOM interactions.
- **`DesktopController`**: Enforces `PermissionManager.check_permission` across mouse, keyboard, window, and process lifecycle operations before dispatching input commands.
