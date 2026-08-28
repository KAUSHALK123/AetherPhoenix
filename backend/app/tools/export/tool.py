import logging

from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_export_tool(registry: ToolRegistry) -> Tool:
    """
    Registers the Unified Export Tool contract with the provided ToolRegistry.

    Args:
        registry: The application ToolRegistry instance.

    Returns:
        The registered Tool contract object.
    """
    export_tool = Tool(
        name="export",
        description=(
            "Unified export layer for converting workflow artifacts into supported "
            "formats (PDF, PPTX, Markdown, DOCX, HTML, Images, CSV, JSON, TXT)."
        ),
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="ExportToolAdapter",
        dependencies=[],
        required_permissions=[
            PermissionType.FILE_SYSTEM.value,
        ],
    )
    registry.register(export_tool)
    logger.info("Successfully registered 'export' tool in ToolRegistry.")
    return export_tool
