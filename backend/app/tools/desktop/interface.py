import asyncio
import time
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import PrivateAttr
from shared.contracts.desktop import MouseActionRequest
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager
from app.tools.adapter import BaseToolAdapter
from app.tools.desktop.application import ApplicationController
from app.tools.desktop.controller import DesktopController
from app.tools.desktop.keyboard import KeyboardController
from app.tools.desktop.mouse import MouseController
from app.tools.desktop.screenshot import DesktopScreenshotController
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class DesktopTool(Tool):
    """
    Desktop automation tool interface coordinating mouse, keyboard,
    and application interactions with security and permission enforcement.
    Provides both direct execution and coordination via DesktopController.
    """

    _permission_manager: Optional[PermissionManager] = PrivateAttr(default=None)
    _controller: Optional[DesktopController] = PrivateAttr(default=None)
    _mouse_controller: Optional[MouseController] = PrivateAttr(default=None)

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        controller: Optional[DesktopController] = None,
        mouse_controller: Optional[MouseController] = None,
        **kwargs: Any,
    ):
        super().__init__(
            name="desktop_automation",
            version="1.0.0",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="desktop_adapter",
            dependencies=["pyautogui", "pywinauto"],
            required_permissions=[PermissionType.DESKTOP_AUTOMATION],
            **kwargs,
        )
        if permission_manager is None:
            from app.core.permissions import get_permission_manager
            permission_manager = get_permission_manager()
        self._permission_manager = permission_manager
        self._controller = controller or DesktopController(
            permission_manager=permission_manager
        )
        self._mouse_controller = mouse_controller or MouseController(
            permission_manager=permission_manager
        )

    @property
    def permission_manager(self) -> Optional[PermissionManager]:
        return self._permission_manager

    @permission_manager.setter
    def permission_manager(self, value: Optional[PermissionManager]) -> None:
        self._permission_manager = value

    @property
    def controller(self) -> DesktopController:
        if self._controller is None:
            self._controller = DesktopController(
                permission_manager=self._permission_manager
            )
        return self._controller

    @property
    def mouse_controller(self) -> MouseController:
        if self._mouse_controller is None:
            self._mouse_controller = MouseController(
                permission_manager=self._permission_manager
            )
        return self._mouse_controller

    @mouse_controller.setter
    def mouse_controller(self, value: Optional[MouseController]) -> None:
        self._mouse_controller = value

    def execute(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> Any:
        """
        Executes a desktop action synchronously.
        Supports standard mouse/keyboard/app actions and controller actions.
        """
        params = params or {}
        logger.info(f"DesktopTool executing action: {action}")

        # Enforce permission check if permission_manager is configured
        if self._permission_manager:
            workflow_id = workflow_id or params.get("workflow_id")
            if workflow_id:
                has_perm = self._permission_manager.check_permission(
                    PermissionType.DESKTOP_AUTOMATION, workflow_id=workflow_id
                )
                if not has_perm:
                    logger.warning(
                        f"Permission denied for desktop action '{action}' "
                        f"on workflow '{workflow_id}'"
                    )
                    raise PermissionDeniedException(
                        f"Permission denied: {PermissionType.DESKTOP_AUTOMATION} "
                        f"required for {action}"
                    )

        try:
            # Mouse actions (using instance controller)
            if action == "mouse_get_position":
                pos = self.mouse_controller.get_position(
                    workflow_id=workflow_id, task_id=task_id
                )
                return {
                    "status": "success",
                    "action": "mouse_get_position",
                    "x": pos.x,
                    "y": pos.y,
                    "position": {"x": pos.x, "y": pos.y},
                }

            elif action == "mouse_move":
                res = self.mouse_controller.move_to(
                    x=params["x"],
                    y=params["y"],
                    duration=params.get("duration", 0.5),
                    timeout=params.get("timeout"),
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                return {
                    "status": "success",
                    "action": "mouse_move",
                    "position": {
                        "x": res.position.x if res.position else params["x"],
                        "y": res.position.y if res.position else params["y"],
                    },
                    "execution_time_ms": res.execution_time_ms,
                }

            elif action == "mouse_click":
                button = params.get("button", "left")
                res = self.mouse_controller.click(
                    x=params.get("x"),
                    y=params.get("y"),
                    button=button,
                    duration=params.get("duration", 0.0),
                    clicks=params.get("clicks", 1),
                    interval=params.get("interval", 0.0),
                    timeout=params.get("timeout"),
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                return {
                    "status": "success",
                    "action": "mouse_click",
                    "button": button,
                    "position": {
                        "x": res.position.x if res.position else params.get("x"),
                        "y": res.position.y if res.position else params.get("y"),
                    },
                    "execution_time_ms": res.execution_time_ms,
                }

            elif action == "mouse_right_click":
                res = self.mouse_controller.right_click(
                    x=params.get("x"),
                    y=params.get("y"),
                    duration=params.get("duration", 0.0),
                    timeout=params.get("timeout"),
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                return {
                    "status": "success",
                    "action": "mouse_right_click",
                    "position": {
                        "x": res.position.x if res.position else params.get("x"),
                        "y": res.position.y if res.position else params.get("y"),
                    },
                    "execution_time_ms": res.execution_time_ms,
                }

            elif action == "mouse_double_click":
                button = params.get("button", "left")
                res = self.mouse_controller.double_click(
                    x=params.get("x"),
                    y=params.get("y"),
                    button=button,
                    interval=params.get("interval", 0.1),
                    duration=params.get("duration", 0.0),
                    timeout=params.get("timeout"),
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                return {
                    "status": "success",
                    "action": "mouse_double_click",
                    "button": button,
                    "position": {
                        "x": res.position.x if res.position else params.get("x"),
                        "y": res.position.y if res.position else params.get("y"),
                    },
                    "execution_time_ms": res.execution_time_ms,
                }

            elif action == "mouse_scroll":
                clicks = params.get("clicks", 0)
                res = self.mouse_controller.scroll(
                    clicks=clicks,
                    x=params.get("x"),
                    y=params.get("y"),
                    timeout=params.get("timeout"),
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                return {
                    "status": "success",
                    "action": "mouse_scroll",
                    "clicks": clicks,
                    "execution_time_ms": res.execution_time_ms,
                }

            elif action == "mouse_action":
                # Direct structured request
                if "request" in params and isinstance(
                    params["request"], MouseActionRequest
                ):
                    req = params["request"]
                else:
                    req = MouseActionRequest.model_validate(params)
                res = self.mouse_controller.execute_action(req)
                return res

            # Keyboard actions (using KeyboardController classmethods)
            elif action in ("keyboard_type", "type_text"):
                result = KeyboardController.type_text(
                    text=params["text"],
                    interval=params.get("interval", 0.05),
                    timeout=params.get("timeout", 30.0),
                )
                return result
            elif action in ("keyboard_press", "key_press"):
                result = KeyboardController.press_key(
                    key=params["key"],
                    duration=params.get("duration", 0.0),
                    presses=params.get("presses", 1),
                    interval=params.get("interval", 0.0),
                )
                return result
            elif action in ("keyboard_down", "key_down"):
                result = KeyboardController.key_down(key=params["key"])
                return result
            elif action in ("keyboard_up", "key_up"):
                result = KeyboardController.key_up(key=params["key"])
                return result
            elif action in (
                "keyboard_hotkey",
                "keyboard_shortcut",
                "hotkey",
                "shortcut",
            ):
                keys = params.get("keys")
                if not keys and "key" in params:
                    keys = [params["key"]]
                if not keys:
                    raise ValueError("Keyboard shortcut requires 'keys' parameter")
                result = KeyboardController.hotkey(
                    *keys, timeout=params.get("timeout", 30.0)
                )
                return result
            elif action in ("keyboard_special_key", "special_key"):
                result = KeyboardController.press_special(
                    special_key=params.get("special_key") or params["key"],
                    duration=params.get("duration", 0.0),
                )
                return result

            # Application actions
            elif action == "app_launch":
                ApplicationController.launch(app_path=params["app_path"])
                return {"status": "success", "action": "app_launch"}

            elif action == "app_connect":
                ApplicationController.connect(title=params["title"])
                return {"status": "success", "action": "app_connect"}

            elif action == "screenshot_fullscreen":
                img = DesktopScreenshotController.capture_fullscreen(
                    output_path=params.get("output_path")
                )
                return {
                    "status": "success",
                    "action": "screenshot_fullscreen",
                    "width": img.width,
                    "height": img.height,
                }
            elif action == "screenshot_region":
                img = DesktopScreenshotController.capture_region(
                    x=params["x"],
                    y=params["y"],
                    width=params["width"],
                    height=params["height"],
                    output_path=params.get("output_path"),
                )
                return {
                    "status": "success",
                    "action": "screenshot_region",
                    "width": img.width,
                    "height": img.height,
                }

            elif action in (
                "start_session",
                "end_session",
                "launch_app",
                "close_app",
                "get_windows",
                "get_active_window",
                "focus_window",
                "get_desktop_state",
            ):
                # Async dispatch
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        res = pool.submit(
                            asyncio.run,
                            self.controller.execute_action(
                                action=action, params=params
                            ),
                        ).result()
                else:
                    res = asyncio.run(
                        self.controller.execute_action(action=action, params=params)
                    )

                if not res.success:
                    raise RuntimeError(res.error or f"Action {action} failed")
                return {"status": "success", "action": action, "output": res.output}
            else:
                logger.warning(f"Unsupported desktop action: {action}")
                raise ValueError(f"Unsupported action: {action}")

        except PermissionDeniedException:
            logger.warning(f"Permission denied for desktop action: {action}")
            raise
        except Exception as e:
            logger.error(f"DesktopTool execution failed for {action}: {e}")
            raise


class DesktopToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging the Worker Agent to the DesktopController.
    Receives atomic workflow Tasks and executes desktop operations with safety.
    """

    def __init__(
        self,
        controller: Optional[DesktopController] = None,
        permission_manager: Optional[PermissionManager] = None,
        desktop_tool: Optional[DesktopTool] = None,
    ):
        if desktop_tool is not None:
            self.controller = desktop_tool.controller
        else:
            self.controller = controller or DesktopController(
                permission_manager=permission_manager
            )

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a Task containing desktop parameters via DesktopController.
        """
        start_time = time.time()
        logger.info(
            f"DesktopToolAdapter executing task {task.task_id} ({task.task_name})"
        )

        params = (
            getattr(task, "input_parameters", {}) or getattr(task, "inputs", {}) or {}
        )
        action = params.get("action")
        if not action:
            if hasattr(task, "category") and hasattr(task.category, "value"):
                action = task.category.value.lower()
            elif hasattr(task, "task_type") and hasattr(task.task_type, "value"):
                action = task.task_type.value.lower()
            else:
                action = "desktop"

        try:
            res = await self.controller.execute_action(
                action=action,
                params=params,
                workflow_id=task.workflow_id,
                task_id=task.task_id,
            )

            execution_time_ms = (time.time() - start_time) * 1000.0

            if res.success:
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=True,
                    output=res.output,
                    logs=[f"Desktop action '{action}' succeeded."],
                    metrics=ExecutionMetrics(execution_time_ms=execution_time_ms),
                )
            else:
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=False,
                    output={},
                    logs=[f"Desktop action '{action}' failed: {res.error}"],
                    error=TaskError(
                        error_code="DESKTOP_ACTION_FAILED",
                        error_message=res.error or f"Action {action} failed",
                    ),
                    metrics=ExecutionMetrics(execution_time_ms=execution_time_ms),
                )

        except Exception as exc:
            execution_time_ms = (time.time() - start_time) * 1000.0
            logger.error(f"DesktopToolAdapter failed for task {task.task_id}: {exc}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                output={},
                logs=[f"Desktop execution exception: {exc}"],
                error=TaskError(
                    error_code="DESKTOP_EXECUTION_ERROR",
                    error_message=str(exc),
                ),
                metrics=ExecutionMetrics(execution_time_ms=execution_time_ms),
            )


def register_desktop_tool(
    registry: ToolRegistry,
    permission_manager: Optional[PermissionManager] = None,
    worker_agent: Optional[Any] = None,
) -> Tool:
    """
    Registers the desktop automation tool in the application ToolRegistry.
    """
    desktop_tool = DesktopTool(permission_manager=permission_manager)
    registry.register(desktop_tool, instance=desktop_tool)
    if worker_agent is not None:
        adapter = DesktopToolAdapter(desktop_tool=desktop_tool)
        worker_agent.register_adapter("desktop_adapter", adapter)
    logger.info("Successfully registered 'desktop_automation' tool in ToolRegistry.")
    return desktop_tool
