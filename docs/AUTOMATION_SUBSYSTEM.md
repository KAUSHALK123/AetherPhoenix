# Automation Subsystem Architecture & Integration Guide (Sprint 6)

## 1. Overview & System Topology
The **AetherPhoenix Automation Subsystem** enables Planner-generated goals to reach Worker Agents and execute through sandboxed, permission-controlled, and audited automation tools (Browser and Desktop).

```
User Query / Goal
       │
       ▼
Planner Agent (Task Decomposition & Capability Discovery)
       │
       ▼
Workflow Engine (SharedWorkflowState & Topological Task Queue)
       │
       ▼
Worker Agent (Tool Resolution & Permission Enforcement)
       │
  ┌────┴───────────────────────────┐
  ▼                                ▼
Browser Automation              Desktop Automation
  ├── Browser Controller          ├── Desktop Controller
  └── DOM Automation              ├── Mouse Controller
                                  ├── Keyboard Controller
                                  └── Screenshot Engine
       │                                │
       └────────────────┬───────────────┘
                        ▼
            Safe Execution Mode & Policy
                        │
                        ▼
                System Execution
                        │
                        ▼
         Supervisor Agent (Validation & QA)
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
 [Passed / Completed]       [Failed -> Healing Agent]
```

---

## 2. Integrated Components

### A. Planner Agent
- **Decomposition**: Translates user goals (`"Open a website and search for cars"`, `"Open text editor and type Hello"`) into hierarchical phases and atomic `LEAF` tasks.
- **Capability Discovery**: Assigns `browser_automation` and `desktop_automation` based on `CapabilityRegistry` categories.

### B. Worker Agent & Tool Adapters
- **`BrowserAdapter`**: Connects Worker Agent tasks to `BrowserController` for navigation, DOM extraction, interactions, and screenshots.
- **`DesktopToolAdapter`**: Bridges Worker Agent tasks to `DesktopController` for mouse clicks, dragging, keyboard typing, window focusing, and application lifecycles.

### C. Permission Manager & Safe Execution Mode
- Evaluates risk levels dynamically (`SAFE`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- In `SAFE` mode:
  - Low-risk read-only tasks execute automatically without dialog popups.
  - High-risk operations require explicit user approval.
  - Dangerous actions (e.g. `Alt+F4`, `file://` URLs, destructive commands) are **hard-blocked**.
- Enforces task-level execution rate limits (`max_actions_per_task`).

### D. Supervisor & Healing Agent
- **Validation**: Inspects execution outputs, verify tool success criteria, and checks for timeouts or permission errors.
- **Healing Loop**: Catches transient or recoverable failures, triggers controlled retries, and escalates non-recoverable errors to user feedback loops.

---

## 3. End-to-End Execution Lifecycles

### 1. Browser Navigation Flow
```
Planner -> Enqueue(Task[category=BROWSER, required_tool=browser_automation])
  -> WorkerAgent.execute()
  -> PermissionManager.check_permission(action='navigate')
  -> BrowserController.navigate(url) -> DOM load -> Result
  -> Supervisor.validate() -> TaskStatus.COMPLETED
```

### 2. Desktop Control Flow
```
Planner -> Enqueue(Task[category=DESKTOP, required_tool=desktop_automation])
  -> WorkerAgent.execute()
  -> PermissionManager.check_permission(action='keyboard_type')
  -> DesktopController.execute_action(action='keyboard_type', text=...)
  -> Application input dispatched -> Result
  -> Supervisor.validate() -> TaskStatus.COMPLETED
```
