from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OCRBoundingBox(BaseModel):
    """Bounding box coordinates for an extracted text segment."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


class OCRTextSegment(BaseModel):
    """Detailed segment information for extracted text."""

    text: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    bounding_box: OCRBoundingBox | None = None
    page_number: int = 1


class OCRRequest(BaseModel):
    """Input parameters for an OCR text extraction task."""

    filepath: str
    language: str = "eng"
    extract_boxes: bool = False
    workflow_id: UUID | None = None
    task_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OCRResult(BaseModel):
    """Structured output result from OCR text extraction."""

    extracted_text: str
    source_artifact: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    segments: list[OCRTextSegment] = Field(default_factory=list)
    image_info: dict[str, Any] = Field(default_factory=dict)
    artifact_id: UUID | None = None
    status: str = "SUCCESS"
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
