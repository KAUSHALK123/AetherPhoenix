from typing import Any, Dict, Optional

from pydantic import PrivateAttr
from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager
from app.tools.desktop.application import ApplicationController
from app.tools.desktop.keyboard import KeyboardController
from app.tools.desktop.mouse import MouseController
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class DesktopTool(Tool):
    """Controlled Desktop Automation Tool interface."""

    _permission_manager: Optional[Any] = PrivateAttr(default=None)

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
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

    @property
    def permission_manager(self) -> Optional[Any]:
        return self._permission_manager

    @permission_manager.setter
    def permission_manager(self, value: Optional[Any]) -> None:
        self._permission_manager = value

    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Executes desktop action with permissions, safety checks, and logging.
        """
        logger.info(f"DesktopTool executing action: {action}")

        # Enforce permission check if permission_manager is configured
        if self._permission_manager:
            workflow_id = params.get("workflow_id")
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
            # Mouse actions
            if action == "mouse_click":
                MouseController.click(
                    x=params["x"],
                    y=params["y"],
                    button=params.get("button", "left"),
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

            # Keyboard actions
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
            else:
                logger.warning(f"Unsupported desktop action: {action}")
                raise ValueError(f"Unsupported action: {action}")
        except Exception as e:
            logger.error(f"DesktopTool execution failed: {e}")
            raise


def register_desktop_tool(
    registry: ToolRegistry,
    permission_manager: Optional[PermissionManager] = None,
) -> DesktopTool:
    """
    Registers the Desktop Automation tool with the ToolRegistry.

    Args:
        registry: The ToolRegistry instance.
        permission_manager: Optional PermissionManager instance for access control.

    Returns:
        The registered DesktopTool instance.
    """
    desktop_tool = DesktopTool(permission_manager=permission_manager)
    registry.register(desktop_tool, instance=desktop_tool)
    logger.info("Successfully registered 'desktop_automation' in ToolRegistry.")
    return desktop_tool
