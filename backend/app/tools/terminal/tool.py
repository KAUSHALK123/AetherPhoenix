import logging
from typing import Optional

from pydantic import BaseModel, Field
from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class TerminalToolInput(BaseModel):
    """Input arguments for the Terminal integration tool."""

    command: str = Field(
        ...,
        description="The terminal command to execute in the system shell.",
    )
    working_directory: Optional[str] = Field(
        None,
        description=(
            "Working directory for the command execution. "
            "Defaults to current directory."
        ),
    )


class TerminalToolOutput(BaseModel):
    """Output from the Terminal tool execution."""

    stdout: str
    stderr: str
    exit_code: int


def register_terminal_tool(registry: ToolRegistry) -> None:
    """Registers the terminal tool with the global registry."""
    tool = Tool(
        name="terminal_tool",
        description=(
            "Executes terminal commands directly in the local " "environment shell."
        ),
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="terminal_tool_adapter",
        required_permissions=[PermissionType.TERMINAL.value],
    )

    registry.register(tool)
    logger.info("Registered terminal_tool")
