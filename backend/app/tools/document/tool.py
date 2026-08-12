from typing import Any, Dict, Optional
from uuid import UUID

from shared.contracts.document import DocumentGenerationResult, StructuredDocumentInput
from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.logging import get_logger
from app.core.permissions import PermissionManager
from app.tools.document.generator import DocumentGenerator
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class DocumentToolAdapter:
    """
    Tool Adapter wrapping DocumentGenerator for Worker Agent tool execution.
    """

    def __init__(self, permission_manager: Optional[PermissionManager] = None) -> None:
        self.generator = DocumentGenerator(permission_manager=permission_manager)

    def execute(
        self,
        payload: Dict[str, Any] | StructuredDocumentInput,
        workflow_id: Optional[UUID] = None,
    ) -> DocumentGenerationResult:
        """
        Executes document generation from a raw dictionary payload or
        StructuredDocumentInput.

        Args:
            payload: Input parameter dictionary matching StructuredDocumentInput.
            workflow_id: Optional associated workflow ID.

        Returns:
            DocumentGenerationResult object.
        """
        if isinstance(payload, StructuredDocumentInput):
            input_data = payload
        else:
            input_data = StructuredDocumentInput.model_validate(payload)

        if workflow_id and not input_data.workflow_id:
            input_data.workflow_id = workflow_id

        return self.generator.generate(input_data)


def register_document_tool(registry: ToolRegistry) -> Tool:
    """
    Registers the Document Generator tool with the provided ToolRegistry.

    Args:
        registry: The application ToolRegistry instance.

    Returns:
        The registered Tool contract object.
    """
    doc_tool = Tool(
        name="document_generator",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.document.tool.DocumentToolAdapter",
        dependencies=[],
        required_permissions=[PermissionType.FILE_SYSTEM.value],
    )
    registry.register(doc_tool)
    logger.info("Successfully registered 'document_generator' tool in ToolRegistry.")
    return doc_tool
