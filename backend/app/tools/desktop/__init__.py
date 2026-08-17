from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.tools.desktop.adapter import DesktopToolAdapter
from app.tools.desktop.application import ApplicationActionError, ApplicationController
from app.tools.desktop.exceptions import (
    DesktopActionError,
    DesktopSessionUnavailableError,
    InvalidCoordinatesError,
    MouseActionError,
    MouseTimeoutError,
)
from app.tools.desktop.interface import DesktopTool
from app.tools.desktop.keyboard import KeyboardActionError, KeyboardController
from app.tools.desktop.mouse import MouseController


def register_desktop_tool(registry, worker_agent=None) -> Tool:
    """
    Registers the Desktop Automation tool in the ToolRegistry and optionally
    registers the DesktopToolAdapter with the WorkerAgent.

    Args:
        registry: The application ToolRegistry instance.
        worker_agent: Optional WorkerAgent instance.

    Returns:
        The registered Tool contract object.
    """
    desktop_tool = Tool(
        name="desktop_automation",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="desktop_adapter",
        dependencies=["pyautogui", "pywinauto"],
        required_permissions=[PermissionType.DESKTOP_AUTOMATION.value],
    )
    registry.register(desktop_tool)

    if worker_agent is not None:
        adapter = DesktopToolAdapter()
        worker_agent.register_adapter("desktop_adapter", adapter)

    return desktop_tool


__all__ = [
    "DesktopTool",
    "MouseController",
    "DesktopToolAdapter",
    "ApplicationController",
    "KeyboardController",
    "register_desktop_tool",
    "DesktopActionError",
    "MouseActionError",
    "InvalidCoordinatesError",
    "DesktopSessionUnavailableError",
    "MouseTimeoutError",
    "ApplicationActionError",
    "KeyboardActionError",
]
