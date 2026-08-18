# Browser Automation Capability & Tool Documentation

**Version:** 1.0.0  
**Status:** Approved  
**Module:** `backend/app/tools/browser/`  
**Tool Registry Key:** `browser_automation`  
**Adapter Key:** `app.tools.browser.interface.BrowserAdapter`  

---

## Overview

The **Browser Automation** capability provides the Worker Agent with an interactive, stateful abstraction over headless browser sessions (via Playwright).

Unlike **Web Scraping** (stateless HTML parsing) and **Web Research** (stateless search), **Browser Automation** maintains an active session, allowing the agent to navigate, click, type, and extract content dynamically across multiple steps.

---

## Architecture & Data Flow

The architecture follows a strict separation of concerns, decoupling the underlying Playwright mechanics from the agent's task execution logic.

```
WorkerAgent Task
      │
      ▼
 BrowserAdapter (BaseToolAdapter) -> Translates Task inputs into Controller calls
      │
      ▼
 BrowserController
 ┌────┴──────────────────────────┐
 │ 1. Session Management         │ (Starts/Closes Playwright & Browser)
 │ 2. Navigation                 │ (goto with timeout & error handling)
 │ 3. Interaction                │ (click, fill, type via locators)
 │ 4. Extraction                 │ (HTML/text parsing from active DOM)
 └────┬──────────────────────────┘
      ▼
 BrowserResult -> ExecutionResult (output, metrics, logs)
```

### Components

1. **`BrowserState`, `BrowserSession`, `BrowserResult`** (`shared.contracts.browser`):
   - Defines the data contracts used to track the session state and return values.
2. **`BrowserController`** (`backend/app/tools/browser/controller.py`):
   - Encapsulates the actual `async_playwright` interactions.
   - Responsible for launching the browser, opening pages, evaluating JS, and handling Playwright errors gracefully.
3. **`BrowserAdapter`** (`backend/app/tools/browser/interface.py`):
   - Implements `BaseToolAdapter`.
   - Dispatches incoming `Task` execution based on the `action` input (`start_session`, `navigate`, `interact`, etc.).
   - Converts `BrowserResult` into `ExecutionResult`.

---

## Safety & Security Constraints

The Browser Automation tool strictly enforces:

- **Permissions:** Execution requires both `BROWSER_ACCESS` and `INTERNET` permissions.
- **Resource Management:** Sessions are tracked; only one active page/browser instance is maintained per controller to prevent runaway memory usage.
- **Timeouts:** All interactions (`navigate`, `interact`) have bounded timeouts (e.g., 30s for navigation, 10s for interactions) to prevent agent starvation.

---

## Data Contracts

### `BrowserTask Inputs` (via Task.inputs)

The `BrowserAdapter` expects specific `inputs` in the `Task` based on the requested `action`.

#### Action: `start_session` / `close_session`
No additional parameters required.

#### Action: `navigate`
| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `url` | `str` | Public target URL | *Required* |
| `timeout_ms` | `float`| Maximum navigation duration in ms | `30000.0` |

#### Action: `interact`
| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `selector` | `str` | CSS selector for target element | *Required* |
| `interaction_action` | `str` | Type of action (`click`, `fill`, etc.) | *Required* |
| `value` | `str` | Input value (required for `fill`) | `None` |
| `timeout_ms` | `float`| Maximum interaction duration in ms | `10000.0` |

#### Action: `extract_content`
| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `include_html` | `bool` | Whether to include raw HTML in output | `False` |

---

## Usage Example

```python
from app.tools.registry import ToolRegistry
from app.engine.registry import CapabilityRegistry
from app.tools.browser.interface import register_browser_capability

tool_registry = ToolRegistry()
cap_registry = CapabilityRegistry()

# Registers "browser_automation" tool and "web_searcher" capability
register_browser_capability(tool_registry, cap_registry)
```
