import asyncio
import base64
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
        async_playwright,
    )
except ImportError:
    Browser = Any  # type: ignore
    BrowserContext = Any  # type: ignore
    Page = Any  # type: ignore
    Playwright = Any  # type: ignore
    async_playwright = None

from shared.contracts.browser import BrowserResult, BrowserSession, BrowserState
from shared.contracts.permission import PermissionType

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager, get_permission_manager
from app.tools.browser.dom import DOMAutomation, InteractiveElement
from app.tools.browser.interaction import ObserveActVerifyEngine

logger = get_logger(__name__)

PROFILES_DIR = Path("backend/artifacts/browser_profiles")


class BrowserActionError(Exception):
    pass


class BrowserController:
    """
    Core controller providing a controlled, stateful abstraction over browser automation.
    Manages Playwright sessions, tab handling, DOM inspection, live frame streaming,
    authenticated state preservation, and Observe-Act-Verify loops with Safe Execution Mode.
    """

    _instance: Optional["BrowserController"] = None

    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._pages: List[Page] = []
        self._active_tab_index: int = 0
        self._session: Optional[BrowserSession] = None
        self._permission_manager = permission_manager
        self._interaction_engine = ObserveActVerifyEngine()
        self._latest_frame_base64: Optional[str] = None
        self._last_action: Optional[str] = None
        self._last_action_status: Optional[str] = None
        self._last_verification: Optional[str] = None

    @classmethod
    def get_instance(
        cls, permission_manager: Optional[PermissionManager] = None
    ) -> "BrowserController":
        """Returns the shared BrowserController singleton instance."""
        if cls._instance is None:
            cls._instance = cls(permission_manager=permission_manager)
        return cls._instance

    @property
    def permission_manager(self) -> Optional[PermissionManager]:
        if self._permission_manager is False:
            return None
        if self._permission_manager is None:
            try:
                self._permission_manager = get_permission_manager()
            except Exception:
                pass
        return self._permission_manager

    @property
    def session(self) -> Optional[BrowserSession]:
        return self._session

    @property
    def page(self) -> Optional[Page]:
        return self._page

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

    def _mask_credentials(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Masks sensitive credentials in parameters to prevent logging secrets."""
        masked = dict(params)
        for k in list(masked.keys()):
            k_lower = k.lower()
            if any(s in k_lower for s in ("password", "token", "secret", "cookie")):
                masked[k] = "[MASKED_CREDENTIAL]"
        return masked

    async def _capture_live_frame(self) -> None:
        """Internal helper to capture a lightweight JPEG frame for live UI streaming."""
        if not self._page:
            return
        try:
            frame_bytes = await self._page.screenshot(type="jpeg", quality=65)
            self._latest_frame_base64 = base64.b64encode(frame_bytes).decode("ascii")
        except Exception:
            pass

    async def start_session(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
        headless: Optional[bool] = None,
        auth_profile: Optional[str] = None,
    ) -> BrowserResult:
        """Starts a Playwright Chromium instance with configurable headless mode and tab support."""
        await self._check_permission(
            action="start_session",
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if self._browser is not None and self._session is not None:
            logger.info("Browser session already running; reusing active session.")
            return BrowserResult(
                success=True,
                data={
                    "session_id": self._session.session_id,
                    "reused": True,
                    "current_url": self._session.current_url,
                },
            )

        # Resolve headless mode
        if headless is None:
            env_val = os.getenv("AETHER_BROWSER_HEADLESS", "true").lower()
            is_headless = env_val not in ("false", "0", "no")
        else:
            is_headless = headless

        logger.info(
            f"Starting browser session (headless={is_headless}, auth_profile={auth_profile})..."
        )
        try:
            if async_playwright is None:
                raise RuntimeError("Playwright is not installed or available.")

            self._playwright = await async_playwright().start()
            launch_kwargs: Dict[str, Any] = {"headless": is_headless}
            if not is_headless:
                launch_kwargs["args"] = ["--disable-web-security", "--no-sandbox"]

            self._browser = await self._playwright.chromium.launch(**launch_kwargs)

            # Context & Page setup
            if auth_profile:
                context_kwargs: Dict[str, Any] = {
                    "viewport": {"width": 1280, "height": 800},
                    "accept_downloads": False,
                }
                storage_path = PROFILES_DIR / f"{auth_profile}.json"
                if storage_path.exists():
                    context_kwargs["storage_state"] = str(storage_path)
                    logger.info(f"Loaded storage state for profile '{auth_profile}'")

                self._context = await self._browser.new_context(**context_kwargs)
                self._page = await self._context.new_page()
            else:
                self._page = await self._browser.new_page()
                try:
                    self._context = self._page.context
                except Exception:
                    self._context = None

            self._pages = [self._page]
            self._active_tab_index = 0

            # Attach automatic dialog handler if supported
            try:
                if hasattr(self._page, "on"):
                    self._page.on(
                        "dialog", lambda dialog: asyncio.create_task(dialog.accept())
                    )
            except Exception:
                pass

            self._session = BrowserSession(
                session_id=str(uuid.uuid4()),
                state=BrowserState.READY,
                start_time=time.time(),
                current_url="about:blank",
                page_title="Blank Page",
                tab_count=1,
                active_tab_index=0,
                tabs=[{"index": 0, "url": "about:blank", "title": "Blank Page"}],
            )
            self._last_action = "Browser session initialized"
            self._last_action_status = "SUCCESS"

            # Capture initial frame
            await self._capture_live_frame()

            return BrowserResult(
                success=True,
                data={
                    "session_id": self._session.session_id,
                    "state": self._session.state.value,
                    "headless": is_headless,
                },
            )
        except Exception as e:
            logger.error(f"Failed to start browser session: {e}")
            self._session = None
            raise BrowserActionError(f"Failed to start browser: {e}") from e

    async def close_session(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Gracefully closes the browser session, all tabs, and Playwright instance."""
        await self._check_permission(
            action="close_session",
            workflow_id=workflow_id,
            task_id=task_id,
        )

        logger.info("Closing browser session...")
        try:
            if self._context:
                await self._context.close()
                self._context = None
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            self._page = None
            self._pages = []
            self._active_tab_index = 0

            if self._session:
                self._session.state = BrowserState.CLOSED
                self._session = None

            self._last_action = "Browser session closed"
            self._last_action_status = "SUCCESS"
            self._latest_frame_base64 = None

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
        """Navigates the active tab to a specific URL."""
        await self._check_permission(
            action="navigate",
            context={"url": url, "timeout_ms": timeout_ms},
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if not self._page or not self._session:
            # Auto-start session if not active
            await self.start_session(workflow_id=workflow_id, task_id=task_id)

        try:
            logger.info(f"Navigating to {url}")
            self._session.state = BrowserState.LOADING
            self._last_action = f"Navigating to {url}"

            response = await self._page.goto(
                url, wait_until="domcontentloaded", timeout=timeout_ms
            )

            # Check HTTP response status
            if (
                response
                and isinstance(getattr(response, "status", None), int)
                and response.status >= 400
            ):
                logger.warning(f"Navigation to {url} returned HTTP {response.status}")
                self._session.state = BrowserState.ERROR
                self._last_action_status = "FAILED"
                return BrowserResult(
                    success=False,
                    error=f"Website returned HTTP {response.status} ({getattr(response, 'status_text', '')})",
                    data={"url": url, "status_code": response.status},
                )

            current_url = (
                self._page.url
                if isinstance(getattr(self._page, "url", None), str)
                else url
            )
            try:
                raw_title = await self._page.title()
                title = raw_title if isinstance(raw_title, str) else ""
            except Exception:
                title = ""

            self._session.current_url = current_url
            self._session.page_title = title
            self._session.state = BrowserState.READY
            self._last_action_status = "SUCCESS"
            self._last_verification = f"Navigated to '{title}' ({current_url})"

            # Update tabs list
            await self._update_tabs_list()
            await self._capture_live_frame()

            return BrowserResult(
                success=True,
                data={
                    "url": current_url,
                    "title": title,
                    "session_id": self._session.session_id,
                },
            )
        except Exception as e:
            if self._session:
                self._session.state = BrowserState.ERROR
            self._last_action_status = "FAILED"
            logger.error(f"Navigation to {url} failed: {str(e)}")
            return BrowserResult(success=False, error=str(e), data={"url": url})

    async def new_tab(
        self,
        url: str = "about:blank",
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Opens a new browser tab and makes it active."""
        await self._check_permission(
            action="new_tab",
            context={"url": url},
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if not self._context or not self._session:
            await self.start_session(workflow_id=workflow_id, task_id=task_id)

        try:
            page = await self._context.new_page()
            page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            self._pages.append(page)
            self._active_tab_index = len(self._pages) - 1
            self._page = page

            if url and url != "about:blank":
                await page.goto(url, wait_until="domcontentloaded", timeout=30000.0)

            await self._update_tabs_list()
            await self._capture_live_frame()

            self._last_action = f"Opened new tab ({url})"
            self._last_action_status = "SUCCESS"

            return BrowserResult(
                success=True,
                data={
                    "active_tab_index": self._active_tab_index,
                    "total_tabs": len(self._pages),
                    "url": page.url,
                },
            )
        except Exception as e:
            logger.error(f"Failed to open new tab: {e}")
            return BrowserResult(success=False, error=str(e))

    async def switch_tab(
        self,
        tab_index: int,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Switches to the tab at specified index."""
        await self._check_permission(
            action="switch_tab",
            context={"tab_index": tab_index},
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if not self._pages or tab_index < 0 or tab_index >= len(self._pages):
            return BrowserResult(
                success=False,
                error=f"Invalid tab index: {tab_index} (total: {len(self._pages)})",
            )

        self._active_tab_index = tab_index
        self._page = self._pages[tab_index]
        await self._page.bring_to_front()

        title = await self._page.title()
        url = self._page.url
        if self._session:
            self._session.current_url = url
            self._session.page_title = title
            self._session.active_tab_index = tab_index

        await self._capture_live_frame()
        self._last_action = f"Switched to tab #{tab_index} ({title})"

        return BrowserResult(
            success=True,
            data={"active_tab_index": tab_index, "url": url, "title": title},
        )

    async def close_tab(
        self,
        tab_index: Optional[int] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Closes the specified tab or the active tab."""
        idx = self._active_tab_index if tab_index is None else tab_index
        if not self._pages or idx < 0 or idx >= len(self._pages):
            return BrowserResult(success=False, error=f"Invalid tab index: {idx}")

        closing_page = self._pages.pop(idx)
        await closing_page.close()

        if self._pages:
            self._active_tab_index = max(
                0, min(self._active_tab_index, len(self._pages) - 1)
            )
            self._page = self._pages[self._active_tab_index]
            await self._page.bring_to_front()
            await self._update_tabs_list()
            await self._capture_live_frame()
        else:
            await self.close_session(workflow_id=workflow_id, task_id=task_id)

        return BrowserResult(
            success=True,
            data={"closed_index": idx, "remaining_tabs": len(self._pages)},
        )

    async def _update_tabs_list(self) -> None:
        """Synchronizes open tabs state with the session model."""
        if not self._session:
            return
        tabs_info = []
        for i, p in enumerate(self._pages):
            try:
                t = await p.title()
            except Exception:
                t = "Untitled"
            tabs_info.append({"index": i, "url": p.url, "title": t})
        self._session.tabs = tabs_info
        self._session.tab_count = len(tabs_info)
        self._session.active_tab_index = self._active_tab_index

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
        """Basic page interactions (click, fill) with credential protection and visual live feedback."""
        safe_ctx = self._mask_credentials(
            {
                "selector": selector,
                "interaction_action": action,
                "value": value,
                "timeout_ms": timeout_ms,
            }
        )
        await self._check_permission(
            action="interact",
            context=safe_ctx,
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if not self._page:
            raise BrowserActionError("Browser session not started.")

        if self._session:
            self._session.state = BrowserState.ACTING
        self._last_action = f"{action.capitalize()} on '{selector}'"

        try:
            # Highlight target for live UI feedback if supported
            try:
                dom = DOMAutomation(self._page)
                await dom.highlight_element(selector, timeout=2000)
            except Exception:
                pass

            if action == "click":
                await self._page.click(selector, timeout=timeout_ms)
            elif action in ("fill", "type"):
                if value is None:
                    raise ValueError("Value must be provided for 'fill' action.")
                await self._page.fill(selector, value, timeout=timeout_ms)
            else:
                raise ValueError(f"Unsupported action: {action}")

            if self._session:
                self._session.state = BrowserState.READY
            self._last_action_status = "SUCCESS"
            await self._capture_live_frame()

            return BrowserResult(
                success=True,
                data={
                    "action": action,
                    "selector": selector,
                    "value": "[MASKED_CREDENTIAL]"
                    if value and "password" in selector.lower()
                    else value,
                },
            )
        except Exception as e:
            if self._session:
                self._session.state = BrowserState.ERROR
            self._last_action_status = "FAILED"
            logger.error(f"Interaction '{action}' on '{selector}' failed: {str(e)}")
            return BrowserResult(success=False, error=str(e))

    async def execute_observe_act_verify(
        self,
        action: str,
        target: str,
        value: Optional[str] = None,
        expected_outcome: Optional[str] = None,
        timeout_ms: float = 10000.0,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """
        Executes an atomic Observe-Act-Verify interaction step.
        """
        await self._check_permission(
            action=f"observe_act_verify:{action}",
            context=self._mask_credentials(
                {"action": action, "target": target, "value": value}
            ),
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if not self._page:
            raise BrowserActionError("Browser session not started.")

        if self._session:
            self._session.state = BrowserState.ACTING
        self._last_action = f"Observe-Act-Verify: {action} on '{target}'"

        try:
            success, result_data = await self._interaction_engine.execute_loop(
                page=self._page,
                action=action,
                target=target,
                value=value,
                expected_outcome=expected_outcome,
                timeout_ms=timeout_ms,
            )

            if self._session:
                self._session.state = (
                    BrowserState.READY if success else BrowserState.ERROR
                )
                self._session.current_url = self._page.url
                self._session.page_title = await self._page.title()

            self._last_action_status = "SUCCESS" if success else "FAILED"
            self._last_verification = result_data.get("details", "")
            await self._capture_live_frame()

            return BrowserResult(
                success=success,
                data=result_data,
                error=result_data.get("error") if not success else None,
            )
        except Exception as e:
            if self._session:
                self._session.state = BrowserState.ERROR
            self._last_action_status = "FAILED"
            logger.error(f"Observe-Act-Verify step failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def get_interactive_elements(
        self, limit: int = 50
    ) -> List[InteractiveElement]:
        """Discovers visible interactive elements on the active page."""
        if not self._page:
            return []
        dom = DOMAutomation(self._page)
        return await dom.get_interactive_elements(limit=limit)

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 500,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Scrolls the active webpage."""
        await self._check_permission(
            action="scroll",
            context={"direction": direction, "amount": amount},
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if not self._page:
            raise BrowserActionError("Browser session not started.")

        try:
            delta_y = amount if direction.lower() == "down" else -amount
            await self._page.evaluate(
                f"window.scrollBy({{top: {delta_y}, behavior: 'smooth'}})"
            )
            await self._capture_live_frame()
            self._last_action = f"Scrolled {direction} ({amount}px)"
            self._last_action_status = "SUCCESS"
            return BrowserResult(
                success=True, data={"direction": direction, "amount": amount}
            )
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def save_auth_state(self, profile_name: str) -> BrowserResult:
        """Safely saves session storage and cookies to a persistent profile file."""
        if not self._context:
            return BrowserResult(success=False, error="No active browser context")
        try:
            PROFILES_DIR.mkdir(parents=True, exist_ok=True)
            safe_name = "".join(
                c for c in profile_name if c.isalnum() or c in ("-", "_")
            )
            file_path = PROFILES_DIR / f"{safe_name}.json"
            await self._context.storage_state(path=str(file_path))
            logger.info(f"Saved auth profile to {file_path}")
            return BrowserResult(
                success=True, data={"profile": safe_name, "saved": True}
            )
        except Exception as e:
            logger.error(f"Failed to save auth state: {e}")
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
            kwargs: Dict[str, Any] = {
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
            self._latest_frame_base64 = base64.b64encode(screenshot_bytes).decode(
                "ascii"
            )

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

    async def get_live_state(self) -> Dict[str, Any]:
        """Returns structured real-time state for live browser frontend panel."""
        if not self._session or not self._page:
            return {
                "active": False,
                "session_id": None,
                "state": "closed",
                "current_url": "about:blank",
                "page_title": "",
                "tab_count": 0,
                "active_tab_index": 0,
                "tabs": [],
                "last_action": self._last_action,
                "last_action_status": self._last_action_status,
                "last_verification": self._last_verification,
                "live_frame_base64": None,
                "interactive_elements_count": 0,
            }

        try:
            url = self._page.url
            title = await self._page.title()
        except Exception:
            url = self._session.current_url or "about:blank"
            title = self._session.page_title or ""

        # Update frame if empty
        if not self._latest_frame_base64:
            await self._capture_live_frame()

        return {
            "active": True,
            "session_id": self._session.session_id,
            "state": self._session.state.value,
            "current_url": url,
            "page_title": title,
            "tab_count": len(self._pages),
            "active_tab_index": self._active_tab_index,
            "tabs": self._session.tabs or [{"index": 0, "url": url, "title": title}],
            "last_action": self._last_action,
            "last_action_status": self._last_action_status,
            "last_verification": self._last_verification,
            "live_frame_base64": self._latest_frame_base64,
            "interactive_elements_count": len(
                await self.get_interactive_elements(limit=30)
            ),
        }


def get_browser_controller(
    permission_manager: Optional[PermissionManager] = None,
) -> BrowserController:
    """Helper to retrieve the BrowserController singleton."""
    return BrowserController.get_instance(permission_manager=permission_manager)
