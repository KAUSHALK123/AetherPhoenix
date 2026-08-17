from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import PrivateAttr
from shared.contracts.desktop import MouseActionRequest
from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.tools.desktop.application import ApplicationController
from app.tools.desktop.keyboard import KeyboardController
from app.tools.desktop.mouse import MouseController

logger = get_logger(__name__)


class DesktopTool(Tool):
    """
    Desktop automation tool interface coordinating mouse, keyboard,
    and application interactions with security and permission enforcement.
    """

    _permission_manager: Optional[Any] = PrivateAttr(default=None)
    _mouse_controller: Optional[MouseController] = PrivateAttr(default=None)

    def __init__(
        self,
        permission_manager: Optional[Any] = None,
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
        self._permission_manager = permission_manager
        self._mouse_controller = mouse_controller or MouseController(
            permission_manager=permission_manager
        )

    @property
    def permission_manager(self) -> Optional[Any]:
        return self._permission_manager

    @permission_manager.setter
    def permission_manager(self, value: Optional[Any]) -> None:
        self._permission_manager = value

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
        Executes a desktop action.
        Safety validation, coordinate checks, and logging are handled
        by controller abstractions.

        Args:
            action: Desktop action name to execute.
            params: Parameters dictionary for the action.
            workflow_id: Optional workflow ID for auditing.
            task_id: Optional task ID for auditing.

        Returns:
            Structured execution output dictionary or result model.
        """
        params = params or {}
        logger.info(f"DesktopTool executing action: {action}")

        try:
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

            else:
                logger.warning(f"Unsupported desktop action: {action}")
                raise ValueError(f"Unsupported action: {action}")

        except PermissionDeniedException:
            logger.warning(f"Permission denied for desktop action: {action}")
            raise
        except Exception as e:
            logger.error(f"DesktopTool execution failed for {action}: {e}")
            raise
