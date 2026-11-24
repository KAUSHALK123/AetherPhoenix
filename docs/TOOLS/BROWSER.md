# Browser Automation Capability & Runtime Documentation

**Version:** 2.0.0  
**Status:** Approved  
**Module:** `backend/app/tools/browser/`  
**Tool Registry Key:** `browser_automation`  
**Adapter Key:** `app.tools.browser.interface.BrowserAdapter`  

---

## Overview

The **Browser Automation** runtime provides AetherPhoenix with an interactive, observable browser engine powered by Playwright and integrated into the frontend interface.

Unlike stateless HTML fetching or basic web search, this runtime maintains active browser sessions, streams live viewport frames directly to the user interface, manages multiple tabs, preserves authenticated profiles securely, and executes tasks using a resilient **Observe–Act–Verify** loop with semantic DOM inspection.

---

## Architecture & Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    AetherPhoenix UI                          │
│  Chat Interface  ◄───────────►  LiveBrowserPanel (Stream/SSE) │
└──────────────┬──────────────────────────────▲────────────────┘
               │ HTTP / SSE                   │
               ▼                              │
┌─────────────────────────────────────────────┴────────────────┐
│               FastAPI Endpoints                              │
│   /browser/session, /navigate, /step, /stream, /mcp/browser  │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│                 MCP & Tool Adapters                          │
│  MCPBrowserAdapter  │  BrowserAdapter (BaseToolAdapter)       │
└──────────────┬──────────────────────┬────────────────────────┘
               │                      │
               ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│                    BrowserController                         │
│  - Session & Tab Management (new_tab, switch_tab, close_tab) │
│  - Persistent Authentication Profiles                        │
│  - Live Viewport Frame Capture (JPEG / WebP Base64)          │
│  - Dialog / Pop-up Handling                                  │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│               Observe–Act–Verify Engine                      │
│                                                              │
│       Observe Webpage (Snapshot DOM, Elements, URL)          │
│                      │                                       │
│                      ▼                                       │
│    Understand Page & Identify Target Element (DOM Matching)  │
│                      │                                       │
│                      ▼                                       │
│           Perform Action (Click, Fill, Scroll)               │
│                      │                                       │
│                      ▼                                       │
│          Observe Updated Page State                          │
│                      │                                       │
│                      ▼                                       │
│           Verify Action Succeeded                            │
│           ├── Success  ──► Continue Next Step                │
│           └── Mismatch ──► Self-Recovery Attempt             │
└──────────────────────────────────────────────────────────────┘
```

---

## Observe–Act–Verify Interaction Loop

Rather than relying on blind pixel coordinates or hardcoded delays, the browser interaction engine adheres to a strict 5-stage loop:

1. **Observe Webpage (`observe`)**:
   - Gathers current URL, page title, readyState, and scans interactive DOM elements (buttons, links, inputs, selects) using `DOMAutomation.get_interactive_elements`.
   - Records element tag names, visible text, ARIA roles, CSS selectors, visibility, and bounding client rects.

2. **Understand & Identify Element (`identify_element`)**:
   - Matches user or agent instructions against discovered elements using multi-tiered heuristics:
     - Exact selector match.
     - Case-insensitive visible text match.
     - Placeholder, label, `name`, `id`, `aria-label`, or title attribute match.
     - Semantic role matching (e.g. `button`, `searchbox`, `link`).

3. **Perform Action (`act`)**:
   - Highlights the element on screen for visual clarity (`DOMAutomation.highlight_element`).
   - Scrolls the target element smoothly into view (`scroll_into_view`).
   - Performs the intended action (`click`, `fill`, `type`, `press`, `scroll`).

4. **Observe Updated Page**:
   - Waits for DOM stabilization, network idle, or navigation triggers.
   - Takes a new post-action observation snapshot.

5. **Verify Action Succeeded (`verify`)**:
   - **Click Verification**: Checks for navigation, URL change, dialog trigger, title update, or interactive element hierarchy change.
   - **Fill Verification**: Inspects `input_value()` of the targeted field to confirm the expected value is present.
   - **Recovery**: If the initial action fails or element is detached, the engine re-observes the page and searches with looser semantic criteria before returning failure.

---

## Tab Management & Authenticated Sessions

### Tab Management
- `new_tab(url)`: Spawns a new tab, attaches dialog handlers, and sets it as the active tab.
- `switch_tab(index)`: Switches active focus to the tab at `index` and triggers live frame capture.
- `close_tab(index)`: Closes the specified tab, adjusting active tab index gracefully.

### Safe Authenticated Sessions
- Browser sessions support persistent user profiles via `auth_profile` identifiers.
- Context directories are scoped under a secure local state directory (`~/.aetherphoenix/browser_profiles/<profile_id>`).
- Credentials (passwords, tokens, cookies) are automatically masked in logs with `[MASKED_CREDENTIAL]`.

---

## Live Browser UI Integration

The frontend (`LiveBrowserPanel.tsx`) displays the browser alongside the chat panel:

- **Viewport Display**: Streams real-time base64-encoded viewport frames over SSE (`/api/v1/browser/stream`) or polled state updates.
- **Address Bar**: Shows current URL, navigation buttons (Back, Reload, Go), and manual URL entry.
- **Tabs Strip**: Visualizes all open tabs with active indicator and one-click tab switching or closing.
- **Action & Verification Banners**: Displays the active Observe-Act-Verify action and live verification outcomes (`READY`, `LOADING`, `ACTING`, `VERIFYING`, `ERROR`).
- **DOM Elements Drawer**: Collapsible panel listing all discovered interactive elements with one-click agent action triggers.

---

## MCP Browser Tools Catalog

The runtime exposes standard Model Context Protocol (MCP) tool schemas via `MCPBrowserToolCatalog` and `MCPBrowserAdapter`:

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `browser_navigate` | Navigates to a URL with timeout | `url`, `timeout_ms` |
| `browser_click` | Clicks an element by selector or text | `target`, `timeout_ms` |
| `browser_fill` | Enters text into an input or textarea | `target`, `value` |
| `browser_observe` | Returns interactive DOM elements & state | `max_elements` |
| `browser_execute_step`| Executes full Observe-Act-Verify loop | `action`, `target`, `value`, `expected_outcome` |
| `browser_screenshot` | Captures JPEG/PNG screenshot | `full_page` |
| `browser_scroll` | Scrolls page horizontally or vertically | `direction`, `amount` |
| `browser_tabs` | Manages tabs (list, new, switch, close) | `action`, `url`, `tab_index` |

---

## Security & Safety Constraints

1. **Permission Manager Enforcement**:
   - Requires `BROWSER_ACCESS` and `INTERNET` permissions via `PermissionManager`.
   - Denied permissions immediately raise `PermissionDeniedException`.
2. **Credential Sanitization**:
   - Password fields and sensitive inputs are identified and their values replaced with `[MASKED_CREDENTIAL]` in all logs and telemetry.
3. **Safe Navigation**:
   - Disallows unsafe URI schemes (`file://`, `javascript:`, `data:`).
   - Reports HTTP errors (e.g. 404, 500) cleanly without crashing session state.
4. **Dialog Handling**:
   - Auto-handles alerts, confirms, and prompts safely to prevent thread locking.

---

## API Endpoints

- `GET /api/v1/browser/session`: Retrieve active session metadata and current viewport frame.
- `POST /api/v1/browser/session/start`: Launch browser session (headless or visible).
- `POST /api/v1/browser/session/close`: Terminate active browser session.
- `POST /api/v1/browser/navigate`: Navigate active page to target URL.
- `POST /api/v1/browser/step`: Execute an Observe-Act-Verify step.
- `GET /api/v1/browser/elements`: Discover and return interactive elements.
- `GET /api/v1/browser/stream`: Server-Sent Events (SSE) live frame and state stream.
- `GET /api/v1/mcp/browser/catalog`: Retrieve MCP tool definitions.
- `POST /api/v1/mcp/browser/execute`: Execute a tool through the MCP adapter.
