import logging
from typing import Optional

from playwright.async_api import Browser, Page, Playwright, async_playwright
from shared.contracts.capability import Capability
from shared.contracts.permission import PermissionType
from shared.contracts.task import TaskCategory
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.engine.registry import CapabilityRegistry
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_browser_capability(
    tool_registry: ToolRegistry, cap_registry: CapabilityRegistry
):
    """Registers the browser tool and capability into the system."""
    browser_tool = Tool(
        name="browser_automation",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.browser.BrowserTool",
        dependencies=["playwright"],
        required_permissions=[
            PermissionType.BROWSER_ACCESS.value,
            PermissionType.INTERNET.value,
        ],
    )
    tool_registry.register(browser_tool)

    browser_cap = Capability(
        name="web_searcher",
        description="Searches and extracts content from the web",
        category=TaskCategory.BROWSER,
        required_tools=["browser_automation"],
    )
    cap_registry.register(browser_cap)


class BrowserTool:
    """
    Provides isolated browser automation capabilities for the Worker Agent.
    Handles session management, navigation, and content extraction safely.
    """

    def __init__(self, permission_checker=None):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self.permission_checker = permission_checker

    def _check_permission(self, permission: PermissionType) -> None:
        if self.permission_checker and not self.permission_checker(permission):
            raise PermissionError(
                f"Action denied: Missing {permission.value} permission."
            )

    async def start_session(self) -> None:
        """Starts a headless Playwright Chromium instance."""
        self._check_permission(PermissionType.BROWSER_ACCESS)

        if self._browser is not None:
            logger.warning("Browser session already running.")
            return

        logger.info("Starting browser session...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._page = await self._browser.new_page()

    async def close_session(self) -> None:
        """Gracefully closes the browser session."""
        logger.info("Closing browser session...")
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None

    async def navigate(self, url: str) -> bool:
        """Navigates to a specific URL."""
        self._check_permission(PermissionType.INTERNET)

        if not self._page:
            raise RuntimeError(
                "Browser session not started. Call start_session() first."
            )

        try:
            logger.info(f"Navigating to {url}")
            await self._page.goto(url, wait_until="domcontentloaded")
            return True
        except Exception as e:
            logger.error(f"Navigation to {url} failed: {str(e)}")
            return False

    async def extract_content(self, include_html: bool = False) -> str:
        """Extracts text or HTML content from the current page."""
        if not self._page:
            raise RuntimeError("Browser session not started.")

        try:
            if include_html:
                return await self._page.content()

            # Simple text extraction
            text_content = await self._page.evaluate("document.body.innerText")
            return text_content or ""
        except Exception as e:
            logger.error(f"Failed to extract content: {str(e)}")
            return ""

    async def interact(self, selector: str, action: str, value: str = None) -> bool:
        """
        Abstractions for basic page interactions (click, fill).
        """
        if not self._page:
            raise RuntimeError("Browser session not started.")

        try:
            if action == "click":
                await self._page.click(selector)
            elif action == "fill":
                if value is None:
                    raise ValueError("Value must be provided for 'fill' action.")
                await self._page.fill(selector, value)
            else:
                raise ValueError(f"Unsupported action: {action}")
            return True
        except Exception as e:
            logger.error(f"Interaction '{action}' on '{selector}' failed: {str(e)}")
            return False
