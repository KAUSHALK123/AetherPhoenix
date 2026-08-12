from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class PDFElementType(str, Enum):
    """Supported structured PDF element types."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    BULLET_LIST = "bullet_list"
    NUMBERED_LIST = "numbered_list"
    TABLE = "table"
    CODE_BLOCK = "code_block"


class HeadingElement(BaseModel):
    """Heading element for PDF documents."""

    element_type: PDFElementType = Field(default=PDFElementType.HEADING)
    text: str = Field(..., description="Text content of the heading")
    level: int = Field(default=1, ge=1, le=3, description="Heading level (1, 2, or 3)")


class ParagraphElement(BaseModel):
    """Paragraph element for PDF documents."""

    element_type: PDFElementType = Field(default=PDFElementType.PARAGRAPH)
    text: str = Field(..., description="Paragraph text content")
    bold: bool = Field(default=False)
    italic: bool = Field(default=False)


class ListElement(BaseModel):
    """List element (bullet or numbered) for PDF documents."""

    element_type: PDFElementType = Field(default=PDFElementType.BULLET_LIST)
    items: List[str] = Field(default_factory=list, description="List items text")
    is_numbered: bool = Field(
        default=False, description="True for numbered list, False for bullets"
    )


class TableElement(BaseModel):
    """Table element for PDF documents."""

    element_type: PDFElementType = Field(default=PDFElementType.TABLE)
    headers: List[str] = Field(
        default_factory=list, description="Table column header titles"
    )
    rows: List[List[str]] = Field(default_factory=list, description="Table data rows")


class CodeBlockElement(BaseModel):
    """Code block element for PDF documents."""

    element_type: PDFElementType = Field(default=PDFElementType.CODE_BLOCK)
    code: str = Field(..., description="Source code text")
    language: Optional[str] = Field(
        default=None, description="Optional programming language name"
    )


PDFElement = Union[
    HeadingElement,
    ParagraphElement,
    ListElement,
    TableElement,
    CodeBlockElement,
]


class PDFDocumentInput(BaseModel):
    """
    Structured input payload for PDF generation.
    """

    title: str = Field(..., description="Title of the PDF document")
    subtitle: Optional[str] = Field(
        default=None, description="Optional document subtitle"
    )
    author: Optional[str] = Field(default=None, description="Optional author name")
    workflow_id: Optional[UUID] = Field(
        default=None, description="Associated workflow ID"
    )
    task_id: Optional[UUID] = Field(default=None, description="Associated task ID")
    elements: List[PDFElement] = Field(
        default_factory=list, description="Ordered structured content elements"
    )
    output_path: str = Field(..., description="Target file path for generated PDF")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional document metadata"
    )


class PDFGenerationResult(BaseModel):
    """
    Metadata output model for generated PDF files.
    """

    filepath: str = Field(..., description="Absolute path to generated PDF file")
    file_name: str = Field(..., description="Filename of generated PDF")
    size_bytes: int = Field(..., ge=0, description="Size of generated PDF in bytes")
    page_count: int = Field(..., ge=1, description="Number of pages in generated PDF")
    checksum: str = Field(..., description="SHA-256 checksum of generated file")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when PDF was generated",
    )
    status: str = Field(default="SUCCESS", description="Execution status")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Execution and document metadata"
    )
