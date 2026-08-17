import concurrent.futures
import time
from typing import Any, Callable, Optional
from uuid import UUID

import pyautogui
from shared.contracts.desktop import (
    MouseActionRequest,
    MouseActionResult,
    MouseActionType,
    MouseButton,
    MousePosition,
    ScreenResolution,
)
from shared.contracts.permission import PermissionType

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.tools.desktop.exceptions import (
    DesktopSessionUnavailableError,
    InvalidCoordinatesError,
    MouseActionError,
    MouseTimeoutError,
)

logger = get_logger(__name__)

# Ensure PyAutoGUI fail-safe is enabled for controlled execution
pyautogui.FAILSAFE = True


class MouseController:
    """
    Controlled and auditable Mouse Controller for Desktop Automation.
    Coordinates mouse operations with permission checks, boundary validations,
    safe execution, and structured logging.
    """

    def __init__(
        self,
        permission_manager: Optional[Any] = None,
        screen_size_provider: Optional[Callable[[], tuple[int, int]]] = None,
        position_provider: Optional[Callable[[], tuple[int, int]]] = None,
        default_timeout: float = 10.0,
    ) -> None:
        self.permission_manager = permission_manager
        self.screen_size_provider = screen_size_provider or pyautogui.size
        self.position_provider = position_provider or pyautogui.position
        self.default_timeout = default_timeout

    def _check_permission(
        self,
        action_name: str,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> None:
        """Enforces DESKTOP_AUTOMATION permission if PermissionManager is present."""
        if not self.permission_manager:
            return

        perm_type = PermissionType.DESKTOP_AUTOMATION
        wf_id = str(workflow_id) if workflow_id else "default_desktop_workflow"

        # Check via check_permission if available
        if hasattr(self.permission_manager, "check_permission"):
            try:
                res = self.permission_manager.check_permission(
                    action=f"Mouse action: {action_name}",
                    permission_type=perm_type,
                    context={"task_id": str(task_id) if task_id else None},
                )
                if hasattr(res, "__await__") and not isinstance(res, bool):
                    # In sync context, check bool wrapper
                    if hasattr(res, "value") and not res.value:
                        raise PermissionDeniedException(
                            f"Permission denied for {perm_type.value}: {action_name}"
                        )
                elif not res:
                    raise PermissionDeniedException(
                        f"Permission denied for {perm_type.value}: {action_name}"
                    )
            except PermissionDeniedException:
                raise
            except Exception as e:
                logger.warning(f"Permission check returned error: {e}")

        # Check via enforce_permission if available
        if hasattr(self.permission_manager, "enforce_permission"):
            try:
                self.permission_manager.enforce_permission(perm_type, wf_id)
            except PermissionDeniedException:
                raise

    def get_screen_resolution(self) -> ScreenResolution:
        """
        Retrieves the active desktop display resolution.
        Raises DesktopSessionUnavailableError if display/session is inaccessible.
        """
        try:
            size = self.screen_size_provider()
            if not size or len(size) < 2 or size[0] <= 0 or size[1] <= 0:
                raise ValueError(f"Invalid screen resolution received: {size}")
            return ScreenResolution(width=int(size[0]), height=int(size[1]))
        except Exception as e:
            logger.error(f"Failed to query desktop screen resolution: {e}")
            raise DesktopSessionUnavailableError(
                f"Desktop GUI session or screen is unavailable: {str(e)}"
            ) from e

    def validate_coordinates(self, x: Any, y: Any) -> tuple[int, int]:
        """
        Validates target screen coordinates against screen resolution.

        Args:
            x: Target horizontal coordinate.
            y: Target vertical coordinate.

        Returns:
            Validated (x, y) integer tuple.

        Raises:
            InvalidCoordinatesError: If coordinates are non-integer, negative,
                                     or outside screen bounds.
            DesktopSessionUnavailableError: If display resolution cannot be obtained.
        """
        if x is None or y is None:
            raise InvalidCoordinatesError("Coordinates (x, y) cannot be None.")

        if isinstance(x, bool) or isinstance(y, bool):
            raise InvalidCoordinatesError(
                f"Coordinates must be integers, received boolean: ({x}, {y})"
            )

        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            type_x = type(x).__name__
            type_y = type(y).__name__
            raise InvalidCoordinatesError(
                f"Coordinates must be numeric integers, received: ({type_x}, {type_y})"
            )

        # Disallow non-integer floats (e.g. 10.5)
        if int(x) != x or int(y) != y:
            raise InvalidCoordinatesError(
                f"Coordinates must be whole integers, received: ({x}, {y})"
            )

        int_x, int_y = int(x), int(y)

        if int_x < 0 or int_y < 0:
            raise InvalidCoordinatesError(
                f"Coordinates ({int_x}, {int_y}) cannot be negative."
            )

        screen = self.get_screen_resolution()
        if int_x >= screen.width or int_y >= screen.height:
            raise InvalidCoordinatesError(
                f"Coordinates ({int_x}, {int_y}) out of screen bounds "
                f"({screen.width}x{screen.height})."
            )

        return int_x, int_y

    def _execute_with_timeout(
        self, func: Callable[..., Any], timeout: float, *args: Any, **kwargs: Any
    ) -> Any:
        """Executes a function with strict timeout enforcement."""
        if timeout <= 0:
            timeout = self.default_timeout

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError as te:
                logger.error(f"Mouse action timed out after {timeout}s")
                raise MouseTimeoutError(
                    f"Mouse operation timed out after {timeout} seconds"
                ) from te
            except pyautogui.FailSafeException as fse:
                logger.error(f"PyAutoGUI fail-safe triggered: {fse}")
                raise MouseActionError(
                    "PyAutoGUI fail-safe triggered: "
                    "mouse cursor moved to screen corner."
                ) from fse
            except (
                InvalidCoordinatesError,
                DesktopSessionUnavailableError,
                MouseActionError,
                PermissionDeniedException,
            ):
                raise
            except Exception as e:
                logger.error(f"Mouse operation failed with unexpected error: {e}")
                raise MouseActionError(f"Mouse operation failed: {str(e)}") from e

    def get_position(
        self,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> MousePosition:
        """
        Retrieves current mouse cursor position.

        Returns:
            MousePosition with current (x, y) coordinates.
        """
        self._check_permission("get_position", workflow_id, task_id)
        start_time = time.time()
        try:
            pos = self.position_provider()
            if not pos or len(pos) < 2:
                raise DesktopSessionUnavailableError("Failed to read cursor position.")
            pos_x, pos_y = int(pos[0]), int(pos[1])
            duration_ms = (time.time() - start_time) * 1000.0
            logger.info(
                f"Mouse cursor position retrieved: ({pos_x}, {pos_y}) "
                f"in {duration_ms:.2f}ms"
            )
            return MousePosition(x=pos_x, y=pos_y)
        except (PermissionDeniedException, DesktopSessionUnavailableError):
            raise
        except Exception as e:
            logger.error(f"Failed to get mouse position: {e}")
            raise DesktopSessionUnavailableError(
                f"Failed to retrieve cursor position: {str(e)}"
            ) from e

    def move_to(
        self_or_x: Any,
        x_or_y: Any = None,
        duration_or_none: float = 0.5,
        timeout: Optional[float] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> MouseActionResult:
        """
        Moves the mouse cursor to target coordinates with controlled speed/duration.
        Supports both instance and classmethod-style invocation.
        """
        if not isinstance(self_or_x, MouseController):
            ctrl = MouseController()
            duration = kwargs.get("duration", duration_or_none)
            return ctrl.move_to(
                x=self_or_x,
                y=x_or_y,
                duration=duration,
                timeout=timeout,
                workflow_id=workflow_id,
                task_id=task_id,
            )

        self = self_or_x
        x = kwargs.get("x", x_or_y) if x_or_y is not None else kwargs.get("x")
        y = kwargs.get("y")

        # Resolve parameters if called as self.move_to(x, y, duration)
        if x_or_y is not None and "y" not in kwargs:
            x = x_or_y
            y = duration_or_none
            duration = kwargs.get("duration", 0.5)
        else:
            duration = kwargs.get("duration", 0.5)

        self._check_permission("move_to", workflow_id, task_id)
        val_x, val_y = self.validate_coordinates(x, y)

        if duration < 0.0:
            raise InvalidCoordinatesError("Movement duration cannot be negative.")

        exec_timeout = timeout or max(self.default_timeout, duration + 2.0)
        start_time = time.time()

        logger.info(
            f"Moving mouse cursor to ({val_x}, {val_y}) over {duration:.2f}s "
            f"(timeout: {exec_timeout}s)"
        )

        def _do_move():
            pyautogui.moveTo(x=val_x, y=val_y, duration=duration)
            return MousePosition(x=val_x, y=val_y)

        try:
            final_pos = self._execute_with_timeout(_do_move, timeout=exec_timeout)
            duration_ms = (time.time() - start_time) * 1000.0
            logger.info(
                f"Mouse moved successfully to ({val_x}, {val_y}) in {duration_ms:.2f}ms"
            )
            return MouseActionResult(
                action=MouseActionType.MOVE,
                success=True,
                position=final_pos,
                execution_time_ms=duration_ms,
                details={"target_x": val_x, "target_y": val_y, "duration": duration},
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(f"Mouse move to ({val_x}, {val_y}) failed: {e}")
            if isinstance(
                e,
                (
                    InvalidCoordinatesError,
                    DesktopSessionUnavailableError,
                    MouseTimeoutError,
                    PermissionDeniedException,
                    MouseActionError,
                ),
            ):
                raise
            raise MouseActionError(f"Failed to move to ({val_x}, {val_y})") from e

    def click(
        self_or_x: Any = None,
        x_or_y: Any = None,
        y_or_button: Any = None,
        button: str = "left",
        duration: float = 0.0,
        clicks: int = 1,
        interval: float = 0.0,
        timeout: Optional[float] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> MouseActionResult:
        """
        Performs a mouse click at specified coordinates or current position.
        Supports both instance and classmethod-style invocation.
        """
        if not isinstance(self_or_x, MouseController):
            ctrl = MouseController()
            btn = y_or_button if isinstance(y_or_button, str) else button
            return ctrl.click(
                x=self_or_x,
                y=x_or_y,
                button=btn,
                duration=duration,
                clicks=clicks,
                interval=interval,
                timeout=timeout,
                workflow_id=workflow_id,
                task_id=task_id,
            )

        self = self_or_x
        # Resolve coordinates and button
        x = kwargs.get("x")
        y = kwargs.get("y")
        btn = kwargs.get("button", button)

        if x_or_y is not None and "x" not in kwargs:
            x = x_or_y
            if y_or_button is not None and not isinstance(y_or_button, str):
                y = y_or_button
            elif isinstance(y_or_button, str):
                btn = y_or_button
        elif y_or_button is not None and "y" not in kwargs:
            if isinstance(y_or_button, (int, float)):
                y = y_or_button
            elif isinstance(y_or_button, str):
                btn = y_or_button

        self._check_permission(f"click_{btn}", workflow_id, task_id)
        btn_str = btn.lower().strip() if isinstance(btn, str) else "left"
        if btn_str not in ("left", "right", "middle"):
            raise MouseActionError(
                f"Unsupported mouse button: '{btn}'. Must be left, right, or middle."
            )

        target_x, target_y = None, None
        if x is not None or y is not None:
            target_x, target_y = self.validate_coordinates(x, y)

        exec_timeout = timeout or self.default_timeout
        start_time = time.time()

        pos_str = (
            f"({target_x}, {target_y})"
            if target_x is not None
            else "current position"
        )
        logger.info(f"Mouse {btn_str} click at {pos_str} clicks={clicks}")

        def _do_click():
            if target_x is not None and target_y is not None:
                pyautogui.click(
                    x=target_x,
                    y=target_y,
                    button=btn_str,
                    clicks=clicks,
                    interval=interval,
                    duration=duration,
                )
                return MousePosition(x=target_x, y=target_y)
            else:
                pyautogui.click(button=btn_str, clicks=clicks, interval=interval)
                cur = self.position_provider()
                return MousePosition(x=int(cur[0]), y=int(cur[1]))

        try:
            final_pos = self._execute_with_timeout(_do_click, timeout=exec_timeout)
            duration_ms = (time.time() - start_time) * 1000.0
            logger.info(
                f"Mouse {btn_str} click completed at ({final_pos.x}, {final_pos.y}) "
                f"in {duration_ms:.2f}ms"
            )
            return MouseActionResult(
                action=MouseActionType.CLICK
                if btn_str == "left"
                else MouseActionType.RIGHT_CLICK,
                success=True,
                position=final_pos,
                execution_time_ms=duration_ms,
                details={
                    "button": btn_str,
                    "clicks": clicks,
                    "x": final_pos.x,
                    "y": final_pos.y,
                },
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(f"Mouse click failed: {e}")
            if isinstance(
                e,
                (
                    InvalidCoordinatesError,
                    DesktopSessionUnavailableError,
                    MouseTimeoutError,
                    PermissionDeniedException,
                    MouseActionError,
                ),
            ):
                raise
            raise MouseActionError(
                f"Failed to click at ({target_x}, {target_y})"
            ) from e

    def right_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        duration: float = 0.0,
        timeout: Optional[float] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> MouseActionResult:
        """Performs a right mouse click."""
        return self.click(
            x=x,
            y=y,
            button="right",
            duration=duration,
            timeout=timeout,
            workflow_id=workflow_id,
            task_id=task_id,
        )

    def double_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        interval: float = 0.1,
        duration: float = 0.0,
        timeout: Optional[float] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> MouseActionResult:
        """
        Performs a double click at target coordinates or current position.

        Args:
            x: Optional X coordinate.
            y: Optional Y coordinate.
            button: Button to double click ('left', 'right', 'middle').
            interval: Interval between the two clicks.
            duration: Pre-click move duration.
            timeout: Execution timeout.
            workflow_id: Optional workflow ID.
            task_id: Optional task ID.

        Returns:
            MouseActionResult.
        """
        self._check_permission(f"double_click_{button}", workflow_id, task_id)
        btn = button.lower().strip() if isinstance(button, str) else "left"
        if btn not in ("left", "right", "middle"):
            raise MouseActionError(f"Unsupported mouse button: '{button}'")

        target_x, target_y = None, None
        if x is not None or y is not None:
            target_x, target_y = self.validate_coordinates(x, y)

        exec_timeout = timeout or self.default_timeout
        start_time = time.time()

        pos_str = (
            f"({target_x}, {target_y})"
            if target_x is not None
            else "current position"
        )
        logger.info(f"Mouse double click at {pos_str} interval={interval}s")

        def _do_double_click():
            if target_x is not None and target_y is not None:
                pyautogui.doubleClick(
                    x=target_x,
                    y=target_y,
                    button=btn,
                    interval=interval,
                    duration=duration,
                )
                return MousePosition(x=target_x, y=target_y)
            else:
                pyautogui.doubleClick(button=btn, interval=interval)
                cur = self.position_provider()
                return MousePosition(x=int(cur[0]), y=int(cur[1]))

        try:
            final_pos = self._execute_with_timeout(
                _do_double_click, timeout=exec_timeout
            )
            duration_ms = (time.time() - start_time) * 1000.0
            logger.info(
                f"Mouse double click completed at ({final_pos.x}, {final_pos.y}) "
                f"in {duration_ms:.2f}ms"
            )
            return MouseActionResult(
                action=MouseActionType.DOUBLE_CLICK,
                success=True,
                position=final_pos,
                execution_time_ms=duration_ms,
                details={
                    "button": btn,
                    "interval": interval,
                    "x": final_pos.x,
                    "y": final_pos.y,
                },
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(f"Mouse double click failed: {e}")
            if isinstance(
                e,
                (
                    InvalidCoordinatesError,
                    DesktopSessionUnavailableError,
                    MouseTimeoutError,
                    PermissionDeniedException,
                    MouseActionError,
                ),
            ):
                raise
            raise MouseActionError(
                f"Failed to double click at ({target_x}, {target_y})"
            ) from e

    def scroll(
        self_or_clicks: Any,
        clicks_or_x: Any = None,
        x_or_y: Any = None,
        y: Optional[int] = None,
        timeout: Optional[float] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> MouseActionResult:
        """
        Performs mouse wheel scrolling. Positive values scroll up, negative scroll down.
        Supports both instance and classmethod-style invocation.
        """
        if not isinstance(self_or_clicks, MouseController):
            ctrl = MouseController()
            clicks = self_or_clicks
            is_int_click = isinstance(clicks_or_x, int)
            x = clicks_or_x if is_int_click and x_or_y is not None else None
            y_val = x_or_y if isinstance(x_or_y, int) else y
            return ctrl.scroll(
                clicks=clicks,
                x=x,
                y=y_val,
                timeout=timeout,
                workflow_id=workflow_id,
                task_id=task_id,
            )

        self = self_or_clicks
        clicks = kwargs.get("clicks", clicks_or_x)
        x = kwargs.get("x", x_or_y if y is not None else None)
        y_val = kwargs.get("y", y)

        self._check_permission("scroll", workflow_id, task_id)
        if isinstance(clicks, bool) or not isinstance(clicks, int):
            raise MouseActionError(
                f"Scroll clicks must be an integer, received: {clicks}"
            )

        target_x, target_y = None, None
        if x is not None or y_val is not None:
            target_x, target_y = self.validate_coordinates(x, y_val)

        exec_timeout = timeout or self.default_timeout
        start_time = time.time()

        pos_str = (
            f"({target_x}, {target_y})"
            if target_x is not None
            else "current position"
        )
        logger.info(f"Mouse scrolling {clicks} clicks at {pos_str}")

        def _do_scroll():
            if target_x is not None and target_y is not None:
                pyautogui.scroll(clicks, x=target_x, y=target_y)
                return MousePosition(x=target_x, y=target_y)
            else:
                pyautogui.scroll(clicks)
                cur = self.position_provider()
                return MousePosition(x=int(cur[0]), y=int(cur[1]))

        try:
            final_pos = self._execute_with_timeout(_do_scroll, timeout=exec_timeout)
            duration_ms = (time.time() - start_time) * 1000.0
            logger.info(f"Mouse scroll completed in {duration_ms:.2f}ms")
            return MouseActionResult(
                action=MouseActionType.SCROLL,
                success=True,
                position=final_pos,
                execution_time_ms=duration_ms,
                details={
                    "clicks": clicks,
                    "direction": "up" if clicks > 0 else "down",
                    "x": final_pos.x,
                    "y": final_pos.y,
                },
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(f"Mouse scroll failed: {e}")
            if isinstance(
                e,
                (
                    InvalidCoordinatesError,
                    DesktopSessionUnavailableError,
                    MouseTimeoutError,
                    PermissionDeniedException,
                    MouseActionError,
                ),
            ):
                raise
            raise MouseActionError(f"Failed to scroll {clicks} clicks") from e

    def execute_action(self, request: MouseActionRequest) -> MouseActionResult:
        """
        Executes a mouse action requested via the MouseActionRequest contract.

        Args:
            request: The MouseActionRequest contract payload.

        Returns:
            MouseActionResult.
        """
        action = request.action
        btn_val = (
            request.button.value
            if isinstance(request.button, MouseButton)
            else str(request.button)
        )

        if action == MouseActionType.GET_POSITION:
            pos = self.get_position(
                workflow_id=request.workflow_id, task_id=request.task_id
            )
            return MouseActionResult(
                action=MouseActionType.GET_POSITION,
                success=True,
                position=pos,
                execution_time_ms=0.0,
                details={"x": pos.x, "y": pos.y},
            )
        elif action == MouseActionType.MOVE:
            if request.x is None or request.y is None:
                raise InvalidCoordinatesError(
                    "Move action requires 'x' and 'y' coordinates."
                )
            return self.move_to(
                x=request.x,
                y=request.y,
                duration=request.duration,
                timeout=request.timeout,
                workflow_id=request.workflow_id,
                task_id=request.task_id,
            )
        elif action == MouseActionType.CLICK:
            return self.click(
                x=request.x,
                y=request.y,
                button=btn_val,
                duration=request.duration,
                clicks=request.clicks,
                interval=request.interval,
                timeout=request.timeout,
                workflow_id=request.workflow_id,
                task_id=request.task_id,
            )
        elif action == MouseActionType.RIGHT_CLICK:
            return self.right_click(
                x=request.x,
                y=request.y,
                duration=request.duration,
                timeout=request.timeout,
                workflow_id=request.workflow_id,
                task_id=request.task_id,
            )
        elif action == MouseActionType.DOUBLE_CLICK:
            return self.double_click(
                x=request.x,
                y=request.y,
                button=btn_val,
                interval=request.interval,
                duration=request.duration,
                timeout=request.timeout,
                workflow_id=request.workflow_id,
                task_id=request.task_id,
            )
        elif action == MouseActionType.SCROLL:
            return self.scroll(
                clicks=request.clicks,
                x=request.x,
                y=request.y,
                timeout=request.timeout,
                workflow_id=request.workflow_id,
                task_id=request.task_id,
            )
        else:
            raise MouseActionError(f"Unsupported mouse action type: '{action}'")
