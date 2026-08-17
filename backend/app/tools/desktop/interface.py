import asyncio
import time
from typing import Any, Dict, Optional

from pydantic import PrivateAttr
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager
from app.tools.adapter import BaseToolAdapter
from app.tools.desktop.application import ApplicationController
from app.tools.desktop.controller import DesktopController
from app.tools.desktop.keyboard import KeyboardController
from app.tools.desktop.mouse import MouseController
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class DesktopTool(Tool):
    """
    Desktop automation tool interface providing both direct execution
    and coordination via DesktopController.
    """

    _permission_manager: Optional[PermissionManager] = PrivateAttr(default=None)
    _controller: Optional[DesktopController] = PrivateAttr(default=None)

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        controller: Optional[DesktopController] = None,
        **kwargs: Any,
    ):
        super().__init__(
            name="desktop_automation",
            version="1.0.0",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="desktop",
            dependencies=["pyautogui", "pywinauto"],
            required_permissions=[PermissionType.DESKTOP_AUTOMATION],
            **kwargs,
        )
        self._permission_manager = permission_manager
        self._controller = controller or DesktopController(
            permission_manager=permission_manager
        )

    @property
    def permission_manager(self) -> Optional[PermissionManager]:
        return self._permission_manager

    @property
    def controller(self) -> DesktopController:
        if self._controller is None:
            self._controller = DesktopController(
                permission_manager=self._permission_manager
            )
        return self._controller

    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Executes a desktop action synchronously.
        Supports standard mouse/keyboard/app actions and controller actions.
        """
        logger.info(f"DesktopTool executing action: {action}")
        try:
            if action == "mouse_click":
                MouseController.click(
                    x=params["x"], y=params["y"], button=params.get("button", "left")
                )
                return {"status": "success", "action": "mouse_click"}
            elif action == "mouse_move":
                MouseController.move_to(
                    x=params["x"],
                    y=params["y"],
                    duration=params.get("duration", 0.5),
                )
                return {"status": "success", "action": "mouse_move"}
            elif action == "mouse_scroll":
                MouseController.scroll(clicks=params["clicks"])
                return {"status": "success", "action": "mouse_scroll"}
            elif action == "keyboard_type":
                KeyboardController.type_text(
                    text=params["text"], interval=params.get("interval", 0.05)
                )
                return {"status": "success", "action": "keyboard_type"}
            elif action == "keyboard_press":
                KeyboardController.press_key(key=params["key"])
                return {"status": "success", "action": "keyboard_press"}
            elif action == "keyboard_hotkey":
                KeyboardController.hotkey(*params["keys"])
                return {"status": "success", "action": "keyboard_hotkey"}
            elif action == "app_launch":
                ApplicationController.launch(app_path=params["app_path"])
                return {"status": "success", "action": "app_launch"}
            elif action == "app_connect":
                ApplicationController.connect(title=params["title"])
                return {"status": "success", "action": "app_connect"}
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
        except Exception as e:
            logger.error(f"DesktopTool execution failed: {e}")
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
    ):
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

        params = getattr(task, "input_parameters", {}) or {}
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
) -> Tool:
    """
    Registers the desktop automation tool in the application ToolRegistry.
    """
    desktop_tool = DesktopTool(permission_manager=permission_manager)
    registry.register(desktop_tool, instance=desktop_tool)
    logger.info("Successfully registered 'desktop_automation' tool in ToolRegistry.")
    return desktop_tool
