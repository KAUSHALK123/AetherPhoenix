import asyncio
import base64
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

try:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
except ImportError:
    Browser = Any  # type: ignore
    BrowserContext = Any  # type: ignore
    Page = Any  # type: ignore
    Playwright = Any  # type: ignore
    async_playwright = None

from shared.contracts.browser import BrowserResult, BrowserSession, BrowserState
from shared.contracts.permission import PermissionType

from app.core.events import Event, EventType, get_event_bus
from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager, get_permission_manager

logger = get_logger(__name__)


class BrowserActionError(Exception):
    pass


AGENT_CURSOR_SCRIPT = """
(function() {
    const CURSOR_ID = '__antigravity_agent_cursor__';
    const STYLE_ID = '__antigravity_cursor_styles__';
    
    function injectCursor() {
        if (document.getElementById(CURSOR_ID)) return;
        
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            #__antigravity_agent_cursor__ {
                position: fixed;
                top: 0;
                left: 0;
                width: 24px;
                height: 24px;
                pointer-events: none;
                z-index: 2147483647;
                transform: translate(-100px, -100px);
                transition: transform 0.18s cubic-bezier(0.22, 1, 0.36, 1);
                will-change: transform;
            }
            #__antigravity_agent_cursor__ svg {
                filter: drop-shadow(0 2px 5px rgba(0,0,0,0.45));
            }
            .antigravity-click-ring {
                position: fixed;
                border-radius: 50%;
                pointer-events: none;
                z-index: 2147483646;
                transform: translate(-50%, -50%) scale(0.2);
                border: 3px solid #6366f1;
                background: rgba(99, 102, 241, 0.25);
                animation: antigravity-ripple 0.45s ease-out forwards;
            }
            @keyframes antigravity-ripple {
                0% { transform: translate(-50%, -50%) scale(0.2); opacity: 1; }
                100% { transform: translate(-50%, -50%) scale(2.2); opacity: 0; }
            }
        `;
        (document.head || document.documentElement).appendChild(style);

        const cursor = document.createElement('div');
        cursor.id = CURSOR_ID;
        cursor.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5.5 3.5L19 12L12 14L8.5 21L5.5 3.5Z" fill="#4f46e5" stroke="#ffffff" stroke-width="1.8" stroke-linejoin="round"/>
                <circle cx="8" cy="8" r="2.5" fill="#f43f5e" />
            </svg>
        `;
        (document.body || document.documentElement).appendChild(cursor);
    }

    window.__antigravity_move_cursor = function(x, y) {
        injectCursor();
        const cur = document.getElementById(CURSOR_ID);
        if (cur) {
            cur.style.transform = `translate(${x}px, ${y}px)`;
        }
    };

    window.__antigravity_click_ripple = function(x, y) {
        injectCursor();
        window.__antigravity_move_cursor(x, y);
        const ring = document.createElement('div');
        ring.className = 'antigravity-click-ring';
        ring.style.left = `${x}px`;
        ring.style.top = `${y}px`;
        ring.style.width = '36px';
        ring.style.height = '36px';
        (document.body || document.documentElement).appendChild(ring);
        setTimeout(() => ring.remove(), 480);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectCursor);
    } else {
        injectCursor();
    }
})();
"""


class BrowserController:
    """
    Core controller providing a controlled abstraction over browser automation.
    Manages Playwright sessions safely with persistent headful context, visible agent cursor,
    safe execution policy gating, and interactive human handoff upon login/captcha barriers.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        user_data_dir: str = "./browser_profile/canva",
    ):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._session: Optional[BrowserSession] = None
        self._permission_manager = permission_manager
        self._user_data_dir = user_data_dir

        # Human handoff state
        self._handoff_event: Optional[asyncio.Event] = None
        self._handoff_active: bool = False
        self._handoff_info: Optional[Dict[str, Any]] = None

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

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context

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
        headless: bool = False,
        persistent: bool = True,
        user_data_dir: Optional[str] = None,
    ) -> BrowserResult:
        """
        Starts a Playwright instance.
        Uses launch_persistent_context with dedicated user-data-dir for headful persistence,
        and injects the visible agent cursor overlay.
        Falls back gracefully to standard launch in unit-test mock setups.
        """
        await self._check_permission(
            action="start_session",
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if self._browser is not None or self._context is not None:
            logger.warning("Browser session already running.")
            return BrowserResult(success=False, error="Session already running")

        target_dir = Path(user_data_dir or self._user_data_dir).resolve()
        os.makedirs(target_dir, exist_ok=True)

        logger.info(
            f"Starting browser session (headless={headless}, persistent={persistent}, dir={target_dir})..."
        )
        try:
            self._playwright = await async_playwright().start()

            # Attempt persistent context if requested and supported
            launched_persistent = False
            if persistent and hasattr(self._playwright.chromium, "launch_persistent_context"):
                try:
                    self._context = await self._playwright.chromium.launch_persistent_context(
                        user_data_dir=str(target_dir),
                        headless=headless,
                        viewport={"width": 1280, "height": 800},
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                    # Register visible cursor overlay script
                    await self._context.add_init_script(AGENT_CURSOR_SCRIPT)
                    if self._context.pages:
                        self._page = self._context.pages[0]
                    else:
                        self._page = await self._context.new_page()
                    launched_persistent = True
                except (TypeError, AttributeError):
                    # Mock or fallback
                    launched_persistent = False

            if not launched_persistent:
                self._browser = await self._playwright.chromium.launch(headless=headless)
                self._page = await self._browser.new_page()
                try:
                    await self._page.add_init_script(AGENT_CURSOR_SCRIPT)
                except Exception:
                    pass

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
        """Gracefully closes the browser context and session."""
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

            if self._session:
                self._session.state = BrowserState.CLOSED
                self._session = None

            return BrowserResult(success=True)
        except Exception as e:
            logger.error(f"Failed to close browser session: {e}")
            raise BrowserActionError("Failed to close browser") from e

    async def close(self) -> BrowserResult:
        """Alias for close_session to support standard controller lifecycle."""
        return await self.close_session()

    async def _animate_cursor(self, x: float, y: float, click: bool = False) -> None:
        """Triggers visible cursor movement and optional click highlight ripple."""
        if not self._page:
            return
        try:
            if click:
                await self._page.evaluate(
                    "([x, y]) => window.__antigravity_click_ripple && window.__antigravity_click_ripple(x, y)",
                    [x, y],
                )
            else:
                await self._page.evaluate(
                    "([x, y]) => window.__antigravity_move_cursor && window.__antigravity_move_cursor(x, y)",
                    [x, y],
                )
            await asyncio.sleep(0.06)
        except Exception as e:
            logger.debug(f"Cursor animation evaluation note: {e}")

    async def _move_cursor_to_selector(
        self, selector: str, click: bool = False
    ) -> Optional[tuple[float, float]]:
        """Computes bounding center of target element and moves overlay cursor there."""
        if not self._page or "Mock" in type(self._page).__name__:
            return None
        try:
            loc = self._page.locator(selector)
            if hasattr(loc, "first"):
                loc = loc.first
            if hasattr(loc, "bounding_box"):
                bb = loc.bounding_box()
                box = await bb if hasattr(bb, "__await__") else bb
                if box and isinstance(box, dict):
                    cx = box["x"] + box["width"] / 2.0
                    cy = box["y"] + box["height"] / 2.0
                    await self._animate_cursor(cx, cy, click=click)
                    return (cx, cy)
        except Exception as e:
            logger.debug(f"Cursor target calculation note for '{selector}': {e}")
        return None

    async def detect_human_handoff_wall(self) -> Optional[Dict[str, Any]]:
        """
        Detects login, captcha, or 2FA barriers on the current page.
        Returns a dictionary with detection details if a wall is found, else None.
        """
        if not self._page or "Mock" in type(self._page).__name__:
            return None
        try:
            raw_url = getattr(self._page, "url", "")
            if isinstance(raw_url, str):
                url = raw_url.lower()
                current_url_str = raw_url
            else:
                url = ""
                current_url_str = ""
            wall_reasons = []

            # 1. URL pattern check
            login_url_patterns = [
                "/login",
                "/signin",
                "/sign-in",
                "/checkpoint",
                "/challenge",
                "/auth",
                "/accounts/login",
                "/2fa",
                "/two-factor",
                "/verification",
                "/signup",
                "/sign-up",
            ]
            if url and any(pat in url for pat in login_url_patterns):
                wall_reasons.append(f"Authentication/Sign-in URL detected: {current_url_str}")

            # 2. Password field check
            pw_count = 0
            try:
                if hasattr(self._page, "locator"):
                    cnt_res = self._page.locator("input[type='password']").count()
                    pw_count = await cnt_res if hasattr(cnt_res, "__await__") else cnt_res
                    if pw_count > 0:
                        wall_reasons.append("Password input field detected on page")
            except Exception:
                pw_count = 0

            # 3. Captcha / Bot challenge check
            captcha_selectors = [
                "iframe[src*='captcha']",
                "iframe[src*='recaptcha']",
                "iframe[src*='turnstile']",
                "iframe[src*='hcaptcha']",
                "[class*='captcha']",
                "[id*='captcha']",
                ".g-recaptcha",
                ".cf-turnstile",
            ]
            for c_sel in captcha_selectors:
                try:
                    if hasattr(self._page, "locator"):
                        c_res = self._page.locator(c_sel).count()
                        c_cnt = await c_res if hasattr(c_res, "__await__") else c_res
                        if c_cnt > 0:
                            wall_reasons.append(f"Captcha or anti-bot challenge detected ({c_sel})")
                            break
                except Exception:
                    continue

            # 4. Prominent Sign-in buttons
            for btn_text in ["Sign in", "Log in", "Sign In", "Log In", "Continue with Google"]:
                try:
                    if hasattr(self._page, "locator"):
                        btn_loc = self._page.locator(f"button:has-text('{btn_text}'), a:has-text('{btn_text}')")
                        if hasattr(btn_loc, "first"):
                            btn_loc = btn_loc.first
                        if hasattr(btn_loc, "is_visible"):
                            vis_res = btn_loc.is_visible(timeout=250)
                            is_vis = await vis_res if hasattr(vis_res, "__await__") else vis_res
                            if is_vis:
                                if "login" in url or "signin" in url or "auth" in url or pw_count > 0:
                                    wall_reasons.append(f"Authentication action button '{btn_text}'")
                                    break
                except Exception:
                    continue

            if wall_reasons:
                return {
                    "detected": True,
                    "reasons": wall_reasons,
                    "reason": "; ".join(wall_reasons),
                    "url": current_url_str,
                }
            return None
        except Exception as e:
            logger.debug(f"Wall detection scan note: {e}")
            return None

    async def handle_human_handoff(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
        timeout_seconds: float = 600.0,
    ) -> bool:
        """
        Pauses the workflow when a login/captcha wall is encountered,
        emits the 'task.needs_human' EventBus event with reason and screenshot,
        keeps the browser open, and waits for human resume or timeout.
        Returns True if wall is cleared, False or raises on timeout.
        """
        wall_info = await self.detect_human_handoff_wall()
        if not wall_info:
            return True

        reason = wall_info["reason"]
        current_url = wall_info["url"]
        logger.info(f"Human handoff required: {reason} at {current_url}")

        screenshot_b64 = None
        try:
            screenshot_bytes = await self._page.screenshot(type="png")
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception as e:
            logger.debug(f"Failed to capture screenshot during handoff: {e}")

        # Emit EventBus event with validated string IDs and source_component
        wf_str = str(workflow_id) if workflow_id else None
        t_str = str(task_id) if task_id else None
        try:
            event_bus = get_event_bus()
            event_payload = {
                "workflow_id": wf_str,
                "task_id": t_str,
                "reason": reason,
                "url": current_url,
                "screenshot": screenshot_b64,
                "status": "WAITING_FOR_HUMAN",
                "timeout_seconds": timeout_seconds,
            }
            await event_bus.publish(
                Event(
                    event_type=EventType.TASK_NEEDS_HUMAN,
                    workflow_id=wf_str,
                    task_id=t_str,
                    source_component="BrowserController",
                    payload=event_payload,
                )
            )
            await event_bus.publish(
                Event(
                    event_type="task.needs_human",
                    workflow_id=wf_str,
                    task_id=t_str,
                    source_component="BrowserController",
                    payload=event_payload,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to emit EventBus task.needs_human event: {e}")

        self._handoff_event = asyncio.Event()
        self._handoff_active = True
        self._handoff_info = {
            "workflow_id": wf_str,
            "task_id": t_str,
            "reason": reason,
            "url": current_url,
            "timeout_seconds": timeout_seconds,
        }

        # Keep browser open and await resume signal or timeout (default 10 min)
        try:
            await asyncio.wait_for(self._handoff_event.wait(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            self._handoff_active = False
            raise BrowserActionError(
                f"Human handoff timed out after {int(timeout_seconds / 60)} minutes: "
                "login/captcha was not completed by user."
            )

        self._handoff_active = False

        # On resume, re-check that the wall is gone
        recheck_wall = await self.detect_human_handoff_wall()
        if recheck_wall:
            logger.warning(
                f"Human resumed, but wall barrier still present: {recheck_wall['reason']}"
            )
            return False

        logger.info("Human handoff barrier cleared successfully. Resuming task execution.")
        return True

    def resume_human_handoff(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> bool:
        """Signals resumption of paused human handoff."""
        if hasattr(self, "_handoff_event") and self._handoff_event:
            self._handoff_event.set()
            return True
        return False

    async def navigate(
        self,
        url: str,
        timeout_ms: float = 30000.0,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
        auto_handoff: bool = True,
        handoff_timeout: float = 600.0,
    ) -> BrowserResult:
        """Navigates to a specific URL with automatic cursor injection and login-wall handoff."""
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

            # Auto human handoff detection
            if auto_handoff:
                wall = await self.detect_human_handoff_wall()
                if wall:
                    await self.handle_human_handoff(
                        workflow_id=workflow_id,
                        task_id=task_id,
                        timeout_seconds=handoff_timeout,
                    )

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
        Abstractions for page interactions (click, fill, hover, scroll).
        All actions animate the visible agent cursor overlay to the target before acting.
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
            # Move cursor overlay to the target element and trigger click ripple if clicking
            await self._move_cursor_to_selector(selector, click=(action == "click"))

            if action == "click":
                await self._page.click(selector, timeout=timeout_ms)
            elif action == "fill":
                if value is None:
                    raise ValueError("Value must be provided for 'fill' action.")
                await self._page.fill(selector, value, timeout=timeout_ms)
            elif action == "hover":
                await self._page.hover(selector, timeout=timeout_ms)
            elif action == "scroll":
                loc = self._page.locator(selector).first
                await loc.scroll_into_view_if_needed(timeout=timeout_ms)
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


_active_browser_controller: Optional[BrowserController] = None


def get_browser_controller(
    permission_manager: Optional[PermissionManager] = None,
    user_data_dir: str = "./browser_profile/canva",
) -> BrowserController:
    """Returns the active or global BrowserController instance."""
    global _active_browser_controller
    if _active_browser_controller is None:
        _active_browser_controller = BrowserController(
            permission_manager=permission_manager,
            user_data_dir=user_data_dir,
        )
    return _active_browser_controller
