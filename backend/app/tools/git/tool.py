import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from shared.contracts.permission import PermissionType
from shared.contracts.tool import (
    Tool,
    ToolHealth,
    ToolState,
)

from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class GitToolInput(BaseModel):
    """Input arguments for the Git integration tool."""
    operation: str = Field(
        ...,
        description=(
            "The git operation to perform: status, branches, history, "
            "checkout, stage, commit, diff, pull, push."
        )
    )
    branch: Optional[str] = Field(None, description="The branch name for checkout.")
    create_branch: Optional[bool] = Field(
        False, description="Whether to create the branch if it doesn't exist."
    )
    files: Optional[List[str]] = Field(
        None, description="Files to stage or check diff for."
    )
    message: Optional[str] = Field(None, description="Commit message.")
    limit: Optional[int] = Field(10, description="Limit for git history.")
    working_directory: Optional[str] = Field(
        None,
        description=(
            "Working directory for the git repository. "
            "Defaults to current directory."
        ),
    )


class GitToolOutput(BaseModel):
    """Output for the Git integration tool."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


def register_git_tool(registry: ToolRegistry) -> Tool:
    """
    Registers the Git tool with the provided ToolRegistry.
    
    Args:
        registry: The application ToolRegistry instance.
        
    Returns:
        The registered Tool contract instance.
    """
    tool = Tool(
        name="git_tool",
        description="Executes Git commands to interact with local repositories.",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="git_tool_adapter",
        required_permissions=[PermissionType.GIT_OPERATIONS.value],
    )
    
    registry.register(tool)
    logger.info("Successfully registered 'git_tool' tool in ToolRegistry.")
    return tool
