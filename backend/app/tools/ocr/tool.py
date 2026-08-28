import logging

from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_ocr_tool(registry: ToolRegistry) -> Tool:
    """
    Registers the OCR tool contract with the provided ToolRegistry.

    Args:
        registry: The application ToolRegistry instance.

    Returns:
        The registered Tool contract object.
    """
    ocr_tool = Tool(
        name="ocr",
        description=(
            "Extracts readable text from images, screenshots, scanned documents, "
            "and visual inputs."
        ),
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="OCRToolAdapter",
        dependencies=[],
        required_permissions=[
            PermissionType.FILE_SYSTEM.value,
        ],
    )
    registry.register(ocr_tool)
    logger.info("Successfully registered 'ocr' tool in ToolRegistry.")
    return ocr_tool
