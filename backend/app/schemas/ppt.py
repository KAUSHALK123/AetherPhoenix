from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SlideType(str, Enum):
    """Supported types of presentation slides."""

    TITLE = "title"
    CONTENT = "content"
    SECTION_HEADER = "section_header"
    TWO_COLUMN = "two_column"
    METRICS = "metrics"
    CHART = "chart"
    IMAGE = "image"
    TABLE = "table"
    REFERENCES = "references"


class SlideContent(BaseModel):
    """Represents the structured content of a single slide."""

    slide_type: SlideType = Field(
        default=SlideType.CONTENT,
        description="The type of the slide (title, content, metrics, chart, image, etc.)",
    )
    title: str = Field(
        ...,
        description="The main title of the slide",
        min_length=1,
    )
    subtitle: Optional[str] = Field(
        None,
        description="Optional subtitle or section header text",
    )
    section_header: Optional[str] = Field(
        None,
        description="Optional high-level section or category name",
    )
    bullets: List[str] = Field(
        default_factory=list,
        description="List of bullet points for the slide content (ideally 3-5 concise items)",
    )
    callout: Optional[str] = Field(
        None,
        description="Optional key metric, highlight takeaway, or quote",
    )
    speaker_notes: Optional[str] = Field(
        None,
        description="Optional presenter notes including talking points and verified citations",
    )
    sources: List[str] = Field(
        default_factory=list,
        description="List of verifiable source URLs or citations supporting the slide content",
    )
    image_path: Optional[str] = Field(
        None,
        description="Path or URL to an embedded image or diagram",
    )
    chart_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured data for rendering a chart (type, categories, series)",
    )
    table_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured data for a table (headers: List[str], rows: List[List[str]])",
    )


class PresentationSchema(BaseModel):
    """Represents structured presentation data to be generated."""

    title: str = Field(
        ...,
        description="The main title of the presentation",
        min_length=1,
    )
    subtitle: Optional[str] = Field(
        None,
        description="The main subtitle of the presentation",
    )
    audience: Optional[str] = Field(
        None,
        description="Target audience (e.g. executive, technical, academic, general)",
    )
    design_style: Optional[str] = Field(
        default="modern_tech",
        description="Visual design style theme (modern_tech, executive, academic, minimal)",
    )
    slide_count: Optional[int] = Field(
        None,
        description="Target number of slides in presentation",
    )
    slides: List[SlideContent] = Field(
        ...,
        description="The list of slides in the presentation",
    )
    references: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Master list of verified references (title, url, date)",
    )


class PPTGenerationResult(BaseModel):
    """Output metadata returned after successful presentation generation."""

    success: bool = Field(
        default=True,
        description="Whether the presentation generation was successful",
    )
    file_path: str = Field(
        ...,
        description="The absolute file path where the PPTX file is saved",
    )
    file_size: int = Field(
        ...,
        description="The size of the generated PPTX file in bytes",
    )
    slide_count: int = Field(
        ...,
        description="The total number of slides generated (including title slide)",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of when the presentation was generated",
    )
    pdf_path: Optional[str] = Field(
        default=None,
        description="The absolute file path of the corresponding exported PDF document",
    )
    pdf_size: Optional[int] = Field(
        default=None,
        description="Size of the exported PDF file in bytes",
    )
