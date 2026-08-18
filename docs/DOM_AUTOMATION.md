# DOM Automation

**Version:** 1.0  
**Status:** Implemented  
**Last Updated:** August 2026  

---

## Purpose

The DOM Automation module provides controlled, DOM-level browser interaction so the Worker Agent can inspect and interact with webpage elements through structured browser actions. 

By operating through the Browser Controller (`BrowserTool`), it ensures browser internals (such as Playwright locators and page contexts) are never directly exposed to the Worker Agent. This enforces security boundaries, limits unsafe manipulations, and respects permission settings.

---

## Architecture

The DOM Automation capability sits inside the `BrowserTool`, isolating the execution engine from the underlying automation library (Playwright).

```
Worker Agent
    ↓ (Requests Action)
BrowserTool (Browser Controller)
    ↓ (Check Permissions)
DOMAutomation Module
    ↓ (Safe Interactions)
Playwright Page
```

---

## Core Operations

The `DOMAutomation` module provides the following core actions safely:

### Element Inspection
`inspect_element(selector: str, timeout: int)`
Locates an element and extracts its current state without leaking the Playwright Locator. Returns a structured `DOMElement` abstraction.

### Click Operation
`click_element(selector: str, timeout: int)`
Waits for an element to be attached and visible before dispatching a click event.

### Text Input
`fill_element(selector: str, text: str, timeout: int)`
Waits for an element to become visible, then simulates typing into input fields.

### Text Extraction
`extract_text(selector: str, timeout: int)`
Extracts the inner text of an element safely.

---

## DOMElement Abstraction

When an element is inspected, its state is returned using the `DOMElement` model:

```python
class DOMElement(BaseModel):
    selector: str
    tag_name: str
    text: str = ""
    is_visible: bool
    is_enabled: bool
    attributes: Dict[str, str]
```

This ensures the Worker Agent only receives deterministic state data instead of live DOM nodes.

---

## Error Handling

DOM Automation introduces specific, catchable exceptions:

- `ElementNotFoundError`: Raised when an element cannot be found within the provided timeout.
- `StaleElementError`: Raised when an element detaches from the DOM while an interaction is in progress (e.g., page navigation during an action).
- `DOMAutomationError`: Generic fallback for other execution failures.

These exceptions are gracefully caught by the `BrowserTool` and logged.

---

## Security & Permissions

All DOM actions exposed through the `BrowserTool` require the `BROWSER_ACCESS` permission.
If the Worker Agent attempts an action without this permission, a `PermissionError` is raised.

Selectors are validated to ensure they are not empty before passing them to the browser engine, preventing malformed queries.
