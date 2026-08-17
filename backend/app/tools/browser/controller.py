import time
import uuid
from typing import Optional

from playwright.async_api import Browser, Page, Playwright, async_playwright
from shared.contracts.browser import BrowserResult, BrowserSession, BrowserState

from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class BrowserActionError(Exception):
    pass


class BrowserController:
    """
    Core controller providing a controlled abstraction over browser automation.
    Manages Playwright sessions safely.
    """

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._session: Optional[BrowserSession] = None

    @property
    def session(self) -> Optional[BrowserSession]:
        return self._session

    async def start_session(self) -> BrowserResult:
        """Starts a headless Playwright Chromium instance."""
        if self._browser is not None:
            logger.warning("Browser session already running.")
            return BrowserResult(success=False, error="Session already running")

        logger.info("Starting browser session...")
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            self._page = await self._browser.new_page()

            self._session = BrowserSession(
                session_id=str(uuid.uuid4()),
                state=BrowserState.READY,
                start_time=time.time(),
            )
            return BrowserResult(
                success=True, data={"session_id": self._session.session_id}
            )
        except Exception as e:
            logger.error(f"Failed to start browser session: {e}")
            self._session = None
            raise BrowserActionError("Failed to start browser") from e

    async def close_session(self) -> BrowserResult:
        """Gracefully closes the browser session."""
        logger.info("Closing browser session...")
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            self._page = None

            if self._session:
                self._session.state = BrowserState.CLOSED
                self._session = None

            return BrowserResult(success=True)
        except Exception as e:
            logger.error(f"Failed to close browser session: {e}")
            raise BrowserActionError("Failed to close browser") from e

    async def navigate(self, url: str, timeout_ms: float = 30000.0) -> BrowserResult:
        """Navigates to a specific URL."""
        if not self._page or not self._session:
            raise BrowserActionError(
                "Browser session not started. Call start_session() first."
            )

        try:
            logger.info(f"Navigating to {url}")
            self._session.state = BrowserState.LOADING
            await self._page.goto(
                url, wait_until="domcontentloaded", timeout=timeout_ms
            )
            self._session.current_url = url
            self._session.state = BrowserState.READY
            return BrowserResult(success=True, data={"url": url})
        except Exception as e:
            self._session.state = BrowserState.ERROR
            logger.error(f"Navigation to {url} failed: {str(e)}")
            return BrowserResult(success=False, error=str(e))

    async def extract_content(self, include_html: bool = False) -> BrowserResult:
        """Extracts text or HTML content from the current page."""
        if not self._page:
            raise BrowserActionError("Browser session not started.")

        try:
            if include_html:
                content = await self._page.content()
            else:
                content = await self._page.evaluate("document.body.innerText")

            return BrowserResult(success=True, data={"content": content or ""})
        except Exception as e:
            logger.error(f"Failed to extract content: {str(e)}")
            return BrowserResult(success=False, error=str(e))

    async def interact(
        self,
        selector: str,
        action: str,
        value: Optional[str] = None,
        timeout_ms: float = 10000.0,
    ) -> BrowserResult:
        """
        Abstractions for basic page interactions (click, fill).
        """
        if not self._page:
            raise BrowserActionError("Browser session not started.")

        try:
            if action == "click":
                await self._page.click(selector, timeout=timeout_ms)
            elif action == "fill":
                if value is None:
                    raise ValueError("Value must be provided for 'fill' action.")
                await self._page.fill(selector, value, timeout=timeout_ms)
            else:
                raise ValueError(f"Unsupported action: {action}")
            return BrowserResult(
                success=True, data={"action": action, "selector": selector}
            )
        except Exception as e:
            logger.error(f"Interaction '{action}' on '{selector}' failed: {str(e)}")
            return BrowserResult(success=False, error=str(e))
