from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    """Supported output document formats."""

    MARKDOWN = "markdown"
    TEXT = "txt"
    HTML = "html"
    JSON = "json"
    CSV = "csv"


class DocumentElementType(str, Enum):
    """Supported document element types."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    CODE_BLOCK = "code_block"
    KEY_VALUE = "key_value"


class DocumentElement(BaseModel):
    """Represents a single structured document element."""

    element_type: DocumentElementType
    text: str | None = None
    level: int | None = Field(default=1, ge=1, le=6)
    items: list[str] | None = None
    headers: list[str] | None = None
    rows: list[list[str]] | None = None
    data: dict[str, Any] | None = None
    code: str | None = None
    language: str | None = "text"
    is_numbered: bool = False
    bold: bool = False


class DocumentSection(BaseModel):
    """Represents a logical section within a document."""

    title: str | None = None
    level: int = Field(default=1, ge=1, le=6)
    content: str | None = None
    elements: list[DocumentElement] = Field(default_factory=list)


class StructuredDocumentInput(BaseModel):
    """Structured input payload for document generation."""

    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    format: DocumentFormat = DocumentFormat.MARKDOWN
    content: str | None = None
    elements: list[DocumentElement] = Field(default_factory=list)
    sections: list[DocumentSection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    output_path: str
    overwrite: bool = False
    workflow_id: UUID | None = None
    task_id: UUID | None = None


class DocumentGenerationResult(BaseModel):
    """Result and metadata of a completed document generation operation."""

    status: str = "SUCCESS"
    filepath: str
    file_name: str
    file_size_bytes: int = Field(ge=0)
    format: DocumentFormat
    checksum_sha256: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    word_count: int = Field(ge=0)
    line_count: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    workflow_id: UUID | None = None
    task_id: UUID | None = None
