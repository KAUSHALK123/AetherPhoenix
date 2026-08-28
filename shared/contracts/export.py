from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    """Supported target export formats for workflow artifacts."""

    PPTX = "pptx"
    PDF = "pdf"
    MARKDOWN = "markdown"
    DOCX = "docx"
    HTML = "html"
    TXT = "txt"
    JSON = "json"
    CSV = "csv"
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


class ExportRequest(BaseModel):
    """Request contract defining parameters for artifact conversion/export."""

    workflow_id: UUID
    target_format: ExportFormat
    source_artifact_id: UUID | str | None = None
    source_filepath: str | None = None
    output_path: str | None = None
    task_id: UUID | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExportResult(BaseModel):
    """Result contract returned after exporting/converting an artifact."""

    artifact_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    task_id: UUID | None = None
    name: str
    filepath: str
    download_url: str
    format: ExportFormat
    size_bytes: int = Field(default=0, ge=0)
    checksum: str
    source_artifact_id: UUID | str | None = None
    source_filepath: str | None = None
    status: str = "SUCCESS"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
