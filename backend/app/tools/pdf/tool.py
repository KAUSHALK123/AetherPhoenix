from typing import Any, Dict, Optional
from uuid import UUID

from shared.contracts.pdf import PDFDocumentInput, PDFGenerationResult
from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.logging import get_logger
from app.core.permissions import PermissionManager
from app.tools.pdf.generator import PDFGenerator
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class PDFToolAdapter:
    """
    Tool Adapter wrapping PDFGenerator for Worker Agent tool execution.
    """

    def __init__(self, permission_manager: Optional[PermissionManager] = None) -> None:
        self.generator = PDFGenerator(permission_manager=permission_manager)

    def execute(
        self, payload: Dict[str, Any], workflow_id: Optional[UUID] = None
    ) -> PDFGenerationResult:
        """
        Executes PDF generation from raw dictionary payload or PDFDocumentInput.

        Args:
            payload: Input parameter dictionary matching PDFDocumentInput.
            workflow_id: Optional associated workflow ID.

        Returns:
            PDFGenerationResult object.
        """
        if isinstance(payload, PDFDocumentInput):
            input_data = payload
        else:
            input_data = PDFDocumentInput.model_validate(payload)

        if workflow_id and not input_data.workflow_id:
            input_data.workflow_id = workflow_id

        return self.generator.generate(input_data)


def register_pdf_tool(registry: ToolRegistry) -> Tool:
    """
    Registers the PDF Generator tool with the provided ToolRegistry.

    Args:
        registry: The application ToolRegistry instance.

    Returns:
        The registered Tool contract object.
    """
    pdf_tool = Tool(
        name="pdf_generator",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.pdf.tool.PDFToolAdapter",
        dependencies=["reportlab"],
        required_permissions=[PermissionType.FILE_SYSTEM.value],
    )
    registry.register(pdf_tool)
    logger.info("Successfully registered 'pdf_generator' tool in ToolRegistry.")
    return pdf_tool
