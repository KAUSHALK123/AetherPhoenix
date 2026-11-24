import logging
from typing import Any, Dict, List, Optional

from app.tools.browser.controller import BrowserController, get_browser_controller

logger = logging.getLogger(__name__)


class MCPBrowserToolCatalog:
    """Standard Model Context Protocol (MCP) tool schema definitions for browser automation."""

    @staticmethod
    def get_tools() -> List[Dict[str, Any]]:
        return [
            {
                "name": "browser_navigate",
                "description": "Navigates the browser to a given web URL with Observe-Act-Verify.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target website URL"},
                        "timeout_ms": {
                            "type": "number",
                            "description": "Navigation timeout in milliseconds",
                            "default": 30000.0,
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "browser_click",
                "description": "Clicks an element on the webpage identified by selector or semantic label.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector, element text, or label to click",
                        },
                        "timeout_ms": {
                            "type": "number",
                            "description": "Timeout in milliseconds",
                            "default": 10000.0,
                        },
                    },
                    "required": ["selector"],
                },
            },
            {
                "name": "browser_fill",
                "description": "Types text into an input field or textarea identified by selector or placeholder.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector, name, or placeholder of input element",
                        },
                        "value": {"type": "string", "description": "Text to enter into field"},
                        "timeout_ms": {
                            "type": "number",
                            "description": "Timeout in milliseconds",
                            "default": 10000.0,
                        },
                    },
                    "required": ["selector", "value"],
                },
            },
            {
                "name": "browser_observe",
                "description": "Observes the current page state and extracts visible interactive elements.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of interactive elements to discover",
                            "default": 50,
                        }
                    },
                },
            },
            {
                "name": "browser_screenshot",
                "description": "Captures a screenshot of the current viewport or full page.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "full_page": {
                            "type": "boolean",
                            "description": "Whether to capture the entire scrollable page",
                            "default": False,
                        }
                    },
                },
            },
            {
                "name": "browser_scroll",
                "description": "Scrolls the page up or down.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["up", "down"],
                            "default": "down",
                        },
                        "amount": {
                            "type": "integer",
                            "description": "Scroll distance in pixels",
                            "default": 500,
                        },
                    },
                },
            },
            {
                "name": "browser_tabs",
                "description": "Manages browser tabs (list, new, switch, close).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "new", "switch", "close"],
                            "description": "Tab action to perform",
                        },
                        "url": {"type": "string", "description": "URL for new tab"},
                        "tab_index": {
                            "type": "integer",
                            "description": "Tab index for switch or close",
                        },
                    },
                    "required": ["action"],
                },
            },
            {
                "name": "browser_execute_step",
                "description": "Executes a complete Observe -> Understand -> Act -> Verify step.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["click", "fill", "navigate", "scroll"],
                        },
                        "target": {
                            "type": "string",
                            "description": "Target selector, label, or URL",
                        },
                        "value": {
                            "type": "string",
                            "description": "Value for fill or direction for scroll",
                        },
                        "expected_outcome": {
                            "type": "string",
                            "description": "Expected result description for verification",
                        },
                    },
                    "required": ["action", "target"],
                },
            },
        ]


class MCPBrowserAdapter:
    """
    Adapter bridging MCP tool execution requests to the active BrowserController.
    Handles unavailable browser states and returns structured MCP responses.
    """

    def __init__(self, controller: Optional[BrowserController] = None):
        self._controller = controller

    @property
    def controller(self) -> BrowserController:
        if self._controller is None:
            self._controller = get_browser_controller()
        return self._controller

    def check_connection(self) -> Dict[str, Any]:
        """Validates MCP browser service connection and readiness status."""
        session = self.controller.session
        is_active = session is not None and self.controller.page is not None
        return {
            "connected": True,
            "browser_active": is_active,
            "session_id": session.session_id if session else None,
            "state": session.state.value if session else "idle",
            "current_url": session.current_url if session else "about:blank",
            "tools_count": len(MCPBrowserToolCatalog.get_tools()),
        }

    async def execute_tool(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes an MCP tool and returns structured MCP result:
        { content: [{ type: "text", text: ... }], isError: bool, data: ... }
        """
        args = arguments or {}
        ctrl = self.controller

        try:
            if name == "browser_navigate":
                url = args.get("url")
                if not url:
                    return self._error_response("Argument 'url' is required.")
                timeout = args.get("timeout_ms", 30000.0)
                res = await ctrl.navigate(url=url, timeout_ms=timeout)
                if not res.success:
                    return self._error_response(f"Navigation failed: {res.error}")
                return self._success_response(
                    f"Successfully navigated to {url}", data=res.data
                )

            elif name == "browser_click":
                selector = args.get("selector")
                if not selector:
                    return self._error_response("Argument 'selector' is required.")
                timeout = args.get("timeout_ms", 10000.0)
                res = await ctrl.interact(selector=selector, action="click", timeout_ms=timeout)
                if not res.success:
                    return self._error_response(f"Click failed: {res.error}")
                return self._success_response(f"Clicked element: {selector}", data=res.data)

            elif name == "browser_fill":
                selector = args.get("selector")
                value = args.get("value")
                if not selector or value is None:
                    return self._error_response("Arguments 'selector' and 'value' are required.")
                timeout = args.get("timeout_ms", 10000.0)
                res = await ctrl.interact(
                    selector=selector, action="fill", value=value, timeout_ms=timeout
                )
                if not res.success:
                    return self._error_response(f"Fill failed: {res.error}")
                return self._success_response(
                    f"Filled element '{selector}' successfully", data=res.data
                )

            elif name == "browser_observe":
                limit = args.get("limit", 50)
                elements = await ctrl.get_interactive_elements(limit=limit)
                live_state = await ctrl.get_live_state()
                return self._success_response(
                    f"Observed page '{live_state['page_title']}' ({live_state['current_url']}). Discovered {len(elements)} interactive elements.",
                    data={
                        "page_title": live_state["page_title"],
                        "current_url": live_state["current_url"],
                        "elements": [el.model_dump() for el in elements],
                    },
                )

            elif name == "browser_screenshot":
                full_page = args.get("full_page", False)
                res = await ctrl.capture_screenshot(full_page=full_page)
                if not res.success:
                    return self._error_response(f"Screenshot failed: {res.error}")
                live_state = await ctrl.get_live_state()
                return self._success_response(
                    "Screenshot captured successfully",
                    data={"live_frame_base64": live_state.get("live_frame_base64")},
                )

            elif name == "browser_scroll":
                direction = args.get("direction", "down")
                amount = args.get("amount", 500)
                res = await ctrl.scroll(direction=direction, amount=amount)
                return self._success_response(f"Scrolled {direction} {amount}px", data=res.data)

            elif name == "browser_tabs":
                action = args.get("action")
                if action == "list":
                    live_state = await ctrl.get_live_state()
                    return self._success_response(
                        f"Active tabs: {live_state['tab_count']}", data={"tabs": live_state["tabs"]}
                    )
                elif action == "new":
                    url = args.get("url", "about:blank")
                    res = await ctrl.new_tab(url=url)
                    return self._success_response(f"Opened new tab: {url}", data=res.data)
                elif action == "switch":
                    idx = args.get("tab_index", 0)
                    res = await ctrl.switch_tab(tab_index=idx)
                    return self._success_response(f"Switched to tab {idx}", data=res.data)
                elif action == "close":
                    idx = args.get("tab_index")
                    res = await ctrl.close_tab(tab_index=idx)
                    return self._success_response(f"Closed tab {idx}", data=res.data)
                else:
                    return self._error_response(f"Unknown tab action: {action}")

            elif name == "browser_execute_step":
                act = args.get("action")
                target = args.get("target")
                val = args.get("value")
                expected = args.get("expected_outcome")
                res = await ctrl.execute_observe_act_verify(
                    action=act,
                    target=target,
                    value=val,
                    expected_outcome=expected,
                )
                if not res.success:
                    return self._error_response(
                        f"Observe-Act-Verify failed: {res.error or 'Verification unsuccessful'}",
                        data=res.data,
                    )
                return self._success_response(
                    f"Step '{act}' on '{target}' completed and verified", data=res.data
                )

            else:
                return self._error_response(f"Tool '{name}' not found in MCP browser catalog.")

        except Exception as e:
            logger.exception(f"MCP browser tool '{name}' failed: {e}")
            return self._error_response(f"Internal MCP browser error: {e}")

    def _success_response(self, text: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "content": [{"type": "text", "text": text}],
            "isError": False,
            "data": data or {},
        }

    def _error_response(self, text: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "content": [{"type": "text", "text": f"Error: {text}"}],
            "isError": True,
            "data": data or {},
        }
