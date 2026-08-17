from typing import Any, Dict

from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.logging.logger import get_logger
from app.tools.desktop.application import ApplicationController
from app.tools.desktop.keyboard import KeyboardController
from app.tools.desktop.mouse import MouseController
from app.tools.desktop.screenshot import DesktopScreenshotController

logger = get_logger(__name__)


class DesktopTool(Tool):
    """Desktop automation tool interface."""

    def __init__(self):
        super().__init__(
            name="desktop_automation",
            version="1.0.0",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="desktop",
            dependencies=["pyautogui", "pywinauto"],
            required_permissions=[PermissionType.DESKTOP_AUTOMATION],
        )

    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Executes a desktop action.
        Safety validation and logging are handled by the controller abstractions.
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
            else:
                logger.warning(f"Unsupported desktop action: {action}")
                raise ValueError(f"Unsupported action: {action}")
        except Exception as e:
            logger.error(f"DesktopTool execution failed: {e}")
            raise
