import logging

from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_file_explorer_tool(registry: ToolRegistry) -> Tool:
    """
    Registers the File Explorer tool contract with the provided ToolRegistry.

    Args:
        registry: The application ToolRegistry instance.

    Returns:
        The registered Tool contract object.
    """
    file_explorer_tool = Tool(
        name="file_explorer",
        description=(
            "Interacts with operating system File Explorer to open folders/files, "
            "reveal artifacts, create directories, detect existence, and "
            "retrieve metadata."
        ),
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="FileExplorerToolAdapter",
        dependencies=[],
        required_permissions=[
            PermissionType.FILE_SYSTEM.value,
            PermissionType.FILE_WRITE.value,
        ],
    )
    registry.register(file_explorer_tool)
    logger.info("Successfully registered 'file_explorer' tool in ToolRegistry.")
    return file_explorer_tool
