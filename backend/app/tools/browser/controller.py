import time
import uuid
from typing import Any, Dict, Optional
from uuid import UUID

try:
    from playwright.async_api import Browser, Page, Playwright, async_playwright
except ImportError:
    Browser = Any  # type: ignore
    Page = Any  # type: ignore
    Playwright = Any  # type: ignore
    async_playwright = None

from shared.contracts.browser import BrowserResult, BrowserSession, BrowserState
from shared.contracts.permission import PermissionType

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager, get_permission_manager

logger = get_logger(__name__)


class BrowserActionError(Exception):
    pass


class BrowserController:
    """
    Core controller providing a controlled abstraction over browser automation.
    Manages Playwright sessions safely with integrated Safe Execution Mode validation.
    """

    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._session: Optional[BrowserSession] = None
        self._permission_manager = permission_manager

    @property
    def permission_manager(self) -> Optional[PermissionManager]:
        if self._permission_manager is None:
            try:
                self._permission_manager = get_permission_manager()
            except Exception:
                pass
        return self._permission_manager

    @property
    def session(self) -> Optional[BrowserSession]:
        return self._session

    async def _check_permission(
        self,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> None:
        """Enforces Safe Execution Mode and permissions for browser automation."""
        pm = self.permission_manager
        if not pm:
            return

        ctx = context or {}
        if workflow_id:
            ctx["workflow_id"] = str(workflow_id)
        if task_id:
            ctx["task_id"] = str(task_id)

        res = pm.check_permission(
            action=f"BrowserAction: {action}",
            permission_type=PermissionType.BROWSER_ACCESS,
            context=ctx,
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if hasattr(res, "__await__"):
            is_approved = await res
        else:
            is_approved = bool(res)

        if not is_approved:
            logger.warning(
                f"Safe execution mode rejected or denied browser action: {action}"
            )
            raise PermissionDeniedException(
                f"Permission or safe policy denied for browser action '{action}'."
            )

    async def start_session(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Starts a headless Playwright Chromium instance."""
        await self._check_permission(
            action="start_session",
            workflow_id=workflow_id,
            task_id=task_id,
        )

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

    async def close_session(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Gracefully closes the browser session."""
        await self._check_permission(
            action="close_session",
            workflow_id=workflow_id,
            task_id=task_id,
        )

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

    async def navigate(
        self,
        url: str,
        timeout_ms: float = 30000.0,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Navigates to a specific URL."""
        await self._check_permission(
            action="navigate",
            context={"url": url, "timeout_ms": timeout_ms},
            workflow_id=workflow_id,
            task_id=task_id,
        )

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

    async def extract_content(
        self,
        include_html: bool = False,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Extracts text or HTML content from the current page."""
        await self._check_permission(
            action="extract_content",
            context={"include_html": include_html},
            workflow_id=workflow_id,
            task_id=task_id,
        )

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
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """
        Abstractions for basic page interactions (click, fill).
        """
        await self._check_permission(
            action="interact",
            context={
                "selector": selector,
                "interaction_action": action,
                "value": value,
                "timeout_ms": timeout_ms,
            },
            workflow_id=workflow_id,
            task_id=task_id,
        )

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

    async def capture_screenshot(
        self,
        output_path: Optional[str] = None,
        full_page: bool = False,
        clip: Optional[dict] = None,
        image_type: str = "png",
        quality: Optional[int] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Captures a screenshot of the current page."""
        await self._check_permission(
            action="capture_screenshot",
            context={
                "output_path": output_path,
                "full_page": full_page,
                "image_type": image_type,
            },
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if not self._page:
            raise BrowserActionError("Browser session not started.")

        try:
            logger.info(f"Capturing browser screenshot (full_page={full_page})")
            kwargs = {
                "full_page": full_page,
                "type": "jpeg" if image_type.lower() in ("jpeg", "jpg") else "png",
            }
            if output_path:
                kwargs["path"] = output_path
            if clip:
                kwargs["clip"] = clip
            if quality and kwargs["type"] == "jpeg":
                kwargs["quality"] = quality

            screenshot_bytes = await self._page.screenshot(**kwargs)
            logger.info("Successfully captured browser screenshot.")
            return BrowserResult(
                success=True,
                data={
                    "screenshot_bytes": screenshot_bytes,
                    "path": output_path,
                },
            )
        except Exception as e:
            logger.error(f"Failed to capture browser screenshot: {str(e)}")
            return BrowserResult(success=False, error=str(e))
