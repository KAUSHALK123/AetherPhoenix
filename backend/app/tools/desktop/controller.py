import ctypes
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

try:
    from pywinauto import Desktop
except (ImportError, Exception):
    Desktop = None

try:
    import pyautogui
except (ImportError, Exception):
    pyautogui = None

from shared.contracts.permission import PermissionType

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager
from app.tools.desktop.application import ApplicationController
from app.tools.desktop.exceptions import (
    DesktopError,
    DesktopTimeoutError,
    WindowNotFoundError,
)
from app.tools.desktop.keyboard import KeyboardController
from app.tools.desktop.models import (
    ApplicationInfo,
    DesktopActionResult,
    DesktopSessionConfig,
    DesktopState,
    ScreenResolution,
    WindowBounds,
    WindowInfo,
)
from app.tools.desktop.mouse import MouseController
from app.tools.desktop.screenshot import DesktopScreenshotController
from app.tools.desktop.session import DesktopSession, DesktopSessionManager

logger = get_logger(__name__)


class DesktopController:
    """
    Central Controller for desktop automation operations.
    Coordinates desktop sessions, applications, windows, desktop state,
    input actions, permission enforcement, and structured execution logging.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        session_manager: Optional[DesktopSessionManager] = None,
    ):
        self.permission_manager = permission_manager
        self.session_manager = session_manager or DesktopSessionManager()

    def _get_foreground_window_handle(self) -> Optional[int]:
        """Safely retrieves the OS foreground window handle."""
        if os.name == "nt":
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                return int(hwnd) if hwnd else None
            except Exception:
                pass
        return None

    @staticmethod
    def _extract_bounds(rect: Any) -> Optional[WindowBounds]:
        """Safely extracts integer WindowBounds from pywinauto or mock rectangle."""
        if rect is None:
            return None
        try:
            left = getattr(rect, "left", 0)
            top = getattr(rect, "top", 0)
            if callable(left):
                left = left()
            if callable(top):
                top = top()

            width_attr = getattr(rect, "width", None)
            if width_attr is not None:
                width = width_attr() if callable(width_attr) else width_attr
                if callable(width):
                    width = width()
            else:
                right = getattr(rect, "right", left)
                if callable(right):
                    right = right()
                width = right - left

            height_attr = getattr(rect, "height", None)
            if height_attr is not None:
                height = height_attr() if callable(height_attr) else height_attr
                if callable(height):
                    height = height()
            else:
                bottom = getattr(rect, "bottom", top)
                if callable(bottom):
                    bottom = bottom()
                height = bottom - top

            return WindowBounds(
                x=int(left), y=int(top), width=int(width), height=int(height)
            )
        except Exception as e:
            logger.debug(f"Failed to extract rectangle bounds: {e}")
            return None

    async def _check_permission(
        self,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[Any] = None,
    ) -> None:
        """Enforces DESKTOP_AUTOMATION permission via PermissionManager."""
        if not self.permission_manager:
            return

        ctx = context or {}
        if workflow_id:
            ctx["workflow_id"] = str(workflow_id)

        res = self.permission_manager.check_permission(
            action=f"DesktopAction: {action}",
            permission_type=PermissionType.DESKTOP_AUTOMATION,
            context=ctx,
            workflow_id=workflow_id,
        )
        if hasattr(res, "__await__"):
            is_approved = await res
        else:
            is_approved = bool(res)

        if not is_approved:
            logger.warning(f"Permission denied for desktop action: {action}")
            raise PermissionDeniedException(
                f"Permission denied for desktop action '{action}'."
            )

    # --------------------------------------------------------------------------
    # Desktop Session Management
    # --------------------------------------------------------------------------

    async def start_session(
        self,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        config: Optional[DesktopSessionConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DesktopSession:
        """Starts and registers a new desktop session."""
        await self._check_permission(
            action="start_session",
            context={"workflow_id": str(workflow_id) if workflow_id else None},
            workflow_id=workflow_id,
        )

        session = self.session_manager.create_session(
            workflow_id=workflow_id,
            task_id=task_id,
            config=config,
            metadata=metadata,
        )
        logger.info(f"DesktopController started session {session.session_id}")
        return session

    async def end_session(self, session_id: Optional[UUID | str] = None) -> None:
        """Ends the specified or active desktop session."""
        await self._check_permission(action="end_session")

        target_session = None
        if session_id:
            target_session = self.session_manager.get_session(session_id)
        else:
            target_session = self.session_manager.get_active_session()

        if target_session:
            self.session_manager.close_session(target_session.session_id)
            logger.info(f"DesktopController ended session {target_session.session_id}")

    def get_session(self, session_id: UUID | str) -> DesktopSession:
        """Retrieves a desktop session by ID."""
        return self.session_manager.get_session(session_id)

    def get_active_session(self) -> Optional[DesktopSession]:
        """Returns the currently active desktop session, if any."""
        return self.session_manager.get_active_session()

    def is_session_active(self) -> bool:
        """Checks if there is an active valid desktop session."""
        session = self.session_manager.get_active_session()
        return session is not None and session.is_active and not session.is_expired()

    # --------------------------------------------------------------------------
    # Application Management
    # --------------------------------------------------------------------------

    async def launch_application(
        self,
        app_path: str,
        args: Optional[List[str]] = None,
        timeout: float = 10.0,
        working_dir: Optional[str] = None,
        session_id: Optional[UUID | str] = None,
    ) -> ApplicationInfo:
        """
        Safely launches a permitted application within the desktop session.
        """
        await self._check_permission(
            action="launch_application",
            context={"app_path": app_path, "args": args},
        )

        session = (
            self.session_manager.get_session(session_id)
            if session_id
            else self.session_manager.get_active_session()
        )

        allowed_apps = session.config.allowed_applications if session else None

        start_time = time.time()
        try:
            app_info = ApplicationController.launch_app(
                app_path=app_path,
                args=args,
                timeout=timeout,
                working_dir=working_dir,
                allowed_apps=allowed_apps,
            )
        except Exception as e:
            if time.time() - start_time >= timeout:
                raise DesktopTimeoutError(
                    f"Launch timed out for '{app_path}' after {timeout}s"
                ) from e
            raise

        if session:
            session.register_process(app_info)

        logger.info(
            f"DesktopController launched application: {app_info.name} "
            f"(PID: {app_info.process_id})"
        )
        return app_info

    async def close_application(
        self,
        pid: Optional[int] = None,
        title: Optional[str] = None,
        force: bool = False,
        timeout: float = 5.0,
        session_id: Optional[UUID | str] = None,
    ) -> bool:
        """
        Terminates a desktop application by PID or window title.
        """
        await self._check_permission(
            action="close_application",
            context={"pid": pid, "title": title, "force": force},
        )

        start_time = time.time()
        try:
            terminated = ApplicationController.terminate_app(
                pid=pid,
                title=title,
                force=force,
                timeout=timeout,
            )
        except Exception as e:
            if time.time() - start_time >= timeout:
                raise DesktopTimeoutError(
                    f"Close application timed out after {timeout}s"
                ) from e
            raise

        # Unregister from session if tracked
        session = (
            self.session_manager.get_session(session_id)
            if session_id
            else self.session_manager.get_active_session()
        )
        if session and pid is not None:
            session.unregister_process(pid)

        logger.info(
            f"DesktopController closed application (PID: {pid}, Title: {title})"
        )
        return terminated

    # --------------------------------------------------------------------------
    # Window Management
    # --------------------------------------------------------------------------

    async def get_windows(
        self,
        include_invisible: bool = False,
        filter_title: Optional[str] = None,
        filter_process_id: Optional[int] = None,
        timeout: float = 5.0,
    ) -> List[WindowInfo]:
        """
        Discovers and lists open top-level desktop windows.
        """
        await self._check_permission(action="get_windows")

        start_time = time.time()
        windows_list: List[WindowInfo] = []

        try:
            fg_hwnd = self._get_foreground_window_handle()

            if Desktop is not None:
                try:
                    dt = Desktop(backend="uia")
                    top_windows = dt.windows()
                    for w in top_windows:
                        try:
                            title = ""
                            if hasattr(w, "window_text"):
                                t = (
                                    w.window_text()
                                    if callable(w.window_text)
                                    else w.window_text
                                )
                                if isinstance(t, str):
                                    title = t
                                elif t is not None:
                                    title = str(t)

                            if not title and not include_invisible:
                                continue

                            is_vis = True
                            if hasattr(w, "is_visible"):
                                v = (
                                    w.is_visible()
                                    if callable(w.is_visible)
                                    else w.is_visible
                                )
                                is_vis = bool(v) if v is not None else True

                            if not is_vis and not include_invisible:
                                continue

                            handle: int | str = 0
                            if hasattr(w, "handle"):
                                h = w.handle() if callable(w.handle) else w.handle
                                if isinstance(h, (int, str)):
                                    handle = h

                            pid = None
                            if hasattr(w, "process_id"):
                                p = (
                                    w.process_id()
                                    if callable(w.process_id)
                                    else w.process_id
                                )
                                if isinstance(p, int):
                                    pid = p
                            if pid is None and hasattr(w, "element_info"):
                                ei_pid = getattr(w.element_info, "process_id", None)
                                if callable(ei_pid):
                                    ei_pid = ei_pid()
                                if isinstance(ei_pid, int):
                                    pid = ei_pid

                            # Filter title
                            if (
                                filter_title
                                and filter_title.lower() not in title.lower()
                            ):
                                continue

                            # Filter PID
                            if (
                                filter_process_id is not None
                                and pid != filter_process_id
                            ):
                                continue

                            rect = w.rectangle() if hasattr(w, "rectangle") else None
                            bounds = self._extract_bounds(rect)

                            is_active = (
                                (handle == fg_hwnd)
                                if (fg_hwnd is not None and handle != 0)
                                else False
                            )

                            class_name = None
                            if hasattr(w, "class_name"):
                                cn = (
                                    w.class_name()
                                    if callable(w.class_name)
                                    else w.class_name
                                )
                                if isinstance(cn, str):
                                    class_name = cn

                            windows_list.append(
                                WindowInfo(
                                    handle=handle,
                                    title=title,
                                    process_id=pid,
                                    is_visible=bool(is_vis),
                                    is_active=bool(is_active),
                                    bounds=bounds,
                                    class_name=class_name,
                                )
                            )
                        except Exception as win_err:
                            logger.debug(f"Skipping window element: {win_err}")
                except Exception as dt_err:
                    logger.warning(f"pywinauto desktop discovery failed: {dt_err}")

            if time.time() - start_time >= timeout:
                raise DesktopTimeoutError(
                    f"Window discovery timed out after {timeout}s"
                )

        except DesktopTimeoutError:
            raise
        except Exception as e:
            logger.error(f"Failed to discover desktop windows: {e}")
            raise DesktopError(f"Window discovery failed: {e}") from e

        logger.info(f"DesktopController discovered {len(windows_list)} windows.")
        return windows_list

    async def get_active_window(self, timeout: float = 5.0) -> Optional[WindowInfo]:
        """
        Retrieves information about the currently focused / foreground window.
        Returns None if no active window is available.
        """
        await self._check_permission(action="get_active_window")

        windows = await self.get_windows(include_invisible=False, timeout=timeout)
        for w in windows:
            if w.is_active:
                return w

        # Fallback to direct foreground handle on Windows if not matched in list
        fg_hwnd = self._get_foreground_window_handle()
        if fg_hwnd:
            try:
                length = ctypes.windll.user32.GetWindowTextLengthW(fg_hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(fg_hwnd, buff, length + 1)
                title = buff.value
                if title:
                    pid_val = ctypes.c_ulong()
                    ctypes.windll.user32.GetWindowThreadProcessId(
                        fg_hwnd, ctypes.byref(pid_val)
                    )
                    return WindowInfo(
                        handle=fg_hwnd,
                        title=title,
                        process_id=pid_val.value,
                        is_visible=True,
                        is_active=True,
                    )
            except Exception as e:
                logger.debug(f"Direct foreground window retrieval fallback failed: {e}")

        return None

    async def focus_window(
        self,
        title: Optional[str] = None,
        handle: Optional[int | str] = None,
        process_id: Optional[int] = None,
        timeout: float = 5.0,
    ) -> WindowInfo:
        """
        Finds and brings a specified desktop window into focus.
        """
        await self._check_permission(
            action="focus_window",
            context={"title": title, "handle": handle, "process_id": process_id},
        )

        if not title and handle is None and process_id is None:
            raise WindowNotFoundError(
                "Either title, handle, or process_id must be provided to focus window."
            )

        start_time = time.time()
        target_win = None

        if Desktop is not None:
            try:
                dt = Desktop(backend="uia")
                for w in dt.windows():
                    try:
                        w_title = ""
                        if hasattr(w, "window_text"):
                            t = (
                                w.window_text()
                                if callable(w.window_text)
                                else w.window_text
                            )
                            if isinstance(t, str):
                                w_title = t
                            elif t is not None:
                                w_title = str(t)

                        w_handle: int | str = 0
                        if hasattr(w, "handle"):
                            h = w.handle() if callable(w.handle) else w.handle
                            if isinstance(h, (int, str)):
                                w_handle = h

                        w_pid = None
                        if hasattr(w, "process_id"):
                            p = (
                                w.process_id()
                                if callable(w.process_id)
                                else w.process_id
                            )
                            if isinstance(p, int):
                                w_pid = p
                        if w_pid is None and hasattr(w, "element_info"):
                            ei_pid = getattr(w.element_info, "process_id", None)
                            if callable(ei_pid):
                                ei_pid = ei_pid()
                            if isinstance(ei_pid, int):
                                w_pid = ei_pid

                        matched = False
                        if handle is not None and w_handle == handle:
                            matched = True
                        elif title and title.lower() in w_title.lower():
                            matched = True
                        elif process_id is not None and w_pid == process_id:
                            matched = True

                        if matched:
                            if hasattr(w, "restore"):
                                try:
                                    w.restore()
                                except Exception:
                                    pass
                            if hasattr(w, "set_focus"):
                                w.set_focus()

                            rect = w.rectangle() if hasattr(w, "rectangle") else None
                            bounds = self._extract_bounds(rect)

                            target_win = WindowInfo(
                                handle=w_handle or 0,
                                title=w_title,
                                process_id=w_pid,
                                is_visible=True,
                                is_active=True,
                                bounds=bounds,
                            )
                            break
                    except Exception as err:
                        logger.debug(f"Focus check error for window item: {err}")

            except Exception as e:
                logger.warning(f"pywinauto focus failed: {e}")

        # Windows API fallback
        if not target_win and os.name == "nt" and handle is not None:
            try:
                hwnd_int = int(handle)
                ctypes.windll.user32.ShowWindow(hwnd_int, 9)  # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd_int)
                target_win = WindowInfo(
                    handle=hwnd_int,
                    title=title or "Focused Window",
                    process_id=process_id,
                    is_visible=True,
                    is_active=True,
                )
            except Exception as e:
                logger.error(f"SetForegroundWindow failed: {e}")

        if time.time() - start_time >= timeout:
            raise DesktopTimeoutError(f"Focus window timed out after {timeout}s")

        if not target_win:
            raise WindowNotFoundError(
                f"Window not found (Title: {title}, Handle: {handle}, "
                f"PID: {process_id})"
            )

        logger.info(f"DesktopController focused window: '{target_win.title}'")
        return target_win

    # --------------------------------------------------------------------------
    # Desktop State
    # --------------------------------------------------------------------------

    async def get_screen_resolution(self) -> ScreenResolution:
        """Retrieves screen resolution width and height."""
        if pyautogui is not None:
            try:
                sz = pyautogui.size()
                return ScreenResolution(width=sz.width, height=sz.height)
            except Exception:
                pass

        if os.name == "nt":
            try:
                user32 = ctypes.windll.user32
                return ScreenResolution(
                    width=user32.GetSystemMetrics(0),
                    height=user32.GetSystemMetrics(1),
                )
            except Exception:
                pass

        return ScreenResolution(width=1920, height=1080)

    async def get_desktop_state(
        self, session_id: Optional[UUID | str] = None
    ) -> DesktopState:
        """
        Captures a comprehensive snapshot of the desktop state.
        """
        await self._check_permission(action="get_desktop_state")

        resolution = await self.get_screen_resolution()
        active_window = await self.get_active_window()
        open_windows = await self.get_windows(include_invisible=False)

        session = (
            self.session_manager.get_session(session_id)
            if session_id
            else self.session_manager.get_active_session()
        )

        running_apps = session.get_processes() if session else []

        state = DesktopState(
            screen_resolution=resolution,
            active_window=active_window,
            open_windows=open_windows,
            running_applications=running_apps,
            session=session.to_info() if session else None,
            timestamp=datetime.now(timezone.utc),
        )
        logger.info(
            f"DesktopController captured desktop state: {len(open_windows)} windows, "
            f"active: '{active_window.title if active_window else None}'"
        )
        return state

    # --------------------------------------------------------------------------
    # Input Actions (Mouse & Keyboard)
    # --------------------------------------------------------------------------

    async def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        session_id: Optional[UUID | str] = None,
    ) -> Dict[str, Any]:
        """Performs a controlled mouse click."""
        await self._check_permission(
            action="mouse_click", context={"x": x, "y": y, "button": button}
        )
        MouseController.click(x=x, y=y, button=button)
        session = self.get_active_session()
        if session:
            session.touch()
        return {"action": "mouse_click", "x": x, "y": y, "button": button}

    async def move_to(
        self,
        x: int,
        y: int,
        duration: float = 0.5,
        session_id: Optional[UUID | str] = None,
    ) -> Dict[str, Any]:
        """Performs a controlled mouse movement."""
        await self._check_permission(
            action="mouse_move", context={"x": x, "y": y, "duration": duration}
        )
        MouseController.move_to(x=x, y=y, duration=duration)
        session = self.get_active_session()
        if session:
            session.touch()
        return {"action": "mouse_move", "x": x, "y": y, "duration": duration}

    async def scroll(
        self, clicks: int, session_id: Optional[UUID | str] = None
    ) -> Dict[str, Any]:
        """Performs a controlled mouse scroll."""
        await self._check_permission(action="mouse_scroll", context={"clicks": clicks})
        MouseController.scroll(clicks=clicks)
        session = self.get_active_session()
        if session:
            session.touch()
        return {"action": "mouse_scroll", "clicks": clicks}

    async def type_text(
        self,
        text: str,
        interval: float = 0.05,
        session_id: Optional[UUID | str] = None,
    ) -> Dict[str, Any]:
        """Performs controlled keyboard text typing."""
        await self._check_permission(
            action="keyboard_type", context={"length": len(text)}
        )
        KeyboardController.type_text(text=text, interval=interval)
        session = self.get_active_session()
        if session:
            session.touch()
        return {"action": "keyboard_type", "length": len(text)}

    async def press_key(
        self, key: str, session_id: Optional[UUID | str] = None
    ) -> Dict[str, Any]:
        """Performs a single keyboard key press."""
        await self._check_permission(action="keyboard_press", context={"key": key})
        KeyboardController.press_key(key=key)
        session = self.get_active_session()
        if session:
            session.touch()
        return {"action": "keyboard_press", "key": key}

    async def hotkey(
        self, *keys: str, session_id: Optional[UUID | str] = None
    ) -> Dict[str, Any]:
        """Performs a keyboard hotkey combination."""
        await self._check_permission(action="keyboard_hotkey", context={"keys": keys})
        KeyboardController.hotkey(*keys)
        session = self.get_active_session()
        if session:
            session.touch()
        return {"action": "keyboard_hotkey", "keys": list(keys)}

    # --------------------------------------------------------------------------
    # Unified Action Dispatcher for Worker Agent
    # --------------------------------------------------------------------------

    async def execute_action(
        self,
        action: str,
        params: Dict[str, Any],
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> DesktopActionResult:
        """
        Unified entrypoint for executing atomic desktop tasks from Worker Agent.
        Dispatches to concrete controller methods and produces structured results.
        """
        start_time = time.time()
        logger.info(f"DesktopController executing action: '{action}'")

        try:
            output_data: Dict[str, Any] = {}

            if action == "start_session":
                config_dict = params.get("config")
                config = (
                    DesktopSessionConfig.model_validate(config_dict)
                    if config_dict
                    else None
                )
                session = await self.start_session(
                    workflow_id=workflow_id,
                    task_id=task_id,
                    config=config,
                    metadata=params.get("metadata"),
                )
                output_data = {"session": session.to_info().model_dump(mode="json")}

            elif action == "end_session":
                await self.end_session(session_id=params.get("session_id"))
                output_data = {"status": "session_ended"}

            elif action in ("launch_app", "app_launch"):
                app_info = await self.launch_application(
                    app_path=params["app_path"],
                    args=params.get("args"),
                    timeout=params.get("timeout", 10.0),
                    working_dir=params.get("working_dir"),
                    session_id=params.get("session_id"),
                )
                output_data = {"application": app_info.model_dump(mode="json")}

            elif action in ("close_app", "app_close", "terminate_app"):
                closed = await self.close_application(
                    pid=params.get("pid"),
                    title=params.get("title"),
                    force=params.get("force", False),
                    timeout=params.get("timeout", 5.0),
                    session_id=params.get("session_id"),
                )
                output_data = {"closed": closed}

            elif action in ("get_windows", "list_windows", "discover_windows"):
                windows = await self.get_windows(
                    include_invisible=params.get("include_invisible", False),
                    filter_title=params.get("filter_title"),
                    filter_process_id=params.get("filter_process_id"),
                    timeout=params.get("timeout", 5.0),
                )
                output_data = {
                    "windows": [w.model_dump(mode="json") for w in windows],
                    "count": len(windows),
                }

            elif action in ("get_active_window", "active_window"):
                active_win = await self.get_active_window(
                    timeout=params.get("timeout", 5.0)
                )
                output_data = {
                    "active_window": (
                        active_win.model_dump(mode="json") if active_win else None
                    )
                }

            elif action in ("focus_window", "window_focus"):
                win = await self.focus_window(
                    title=params.get("title"),
                    handle=params.get("handle"),
                    process_id=params.get("process_id"),
                    timeout=params.get("timeout", 5.0),
                )
                output_data = {"window": win.model_dump(mode="json")}

            elif action in ("get_desktop_state", "desktop_state"):
                state = await self.get_desktop_state(
                    session_id=params.get("session_id")
                )
                output_data = {"desktop_state": state.model_dump(mode="json")}

            elif action == "mouse_click":
                output_data = await self.click(
                    x=params["x"],
                    y=params["y"],
                    button=params.get("button", "left"),
                    session_id=params.get("session_id"),
                )

            elif action == "mouse_move":
                output_data = await self.move_to(
                    x=params["x"],
                    y=params["y"],
                    duration=params.get("duration", 0.5),
                    session_id=params.get("session_id"),
                )

            elif action == "mouse_scroll":
                output_data = await self.scroll(
                    clicks=params["clicks"], session_id=params.get("session_id")
                )

            elif action == "keyboard_type":
                output_data = await self.type_text(
                    text=params["text"],
                    interval=params.get("interval", 0.05),
                    session_id=params.get("session_id"),
                )

            elif action == "keyboard_press":
                output_data = await self.press_key(
                    key=params["key"], session_id=params.get("session_id")
                )

            elif action == "keyboard_hotkey":
                output_data = await self.hotkey(
                    *params["keys"], session_id=params.get("session_id")
                )

            elif action in (
                "screenshot_fullscreen",
                "desktop_screenshot",
                "screenshot",
            ):
                img = DesktopScreenshotController.capture_fullscreen(
                    output_path=params.get("output_path")
                )
                output_data = {
                    "width": img.width,
                    "height": img.height,
                    "output_path": params.get("output_path"),
                }

            elif action == "screenshot_region":
                img = DesktopScreenshotController.capture_region(
                    x=params["x"],
                    y=params["y"],
                    width=params["width"],
                    height=params["height"],
                    output_path=params.get("output_path"),
                )
                output_data = {
                    "width": img.width,
                    "height": img.height,
                    "output_path": params.get("output_path"),
                }

            elif action == "app_connect":
                # Legacy app connect
                ApplicationController.connect(title=params["title"])
                output_data = {"status": "success", "action": "app_connect"}

            else:
                raise ValueError(f"Unsupported desktop action: '{action}'")

            duration_ms = (time.time() - start_time) * 1000.0
            return DesktopActionResult(
                action=action,
                success=True,
                output=output_data,
                execution_time_ms=duration_ms,
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(f"Desktop action '{action}' failed: {exc}")
            return DesktopActionResult(
                action=action,
                success=False,
                output={},
                error=str(exc),
                execution_time_ms=duration_ms,
                timestamp=datetime.now(timezone.utc),
            )
