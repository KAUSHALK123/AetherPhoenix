from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SlideType(str, Enum):
    """Supported types of slides."""

    TITLE = "title"
    CONTENT = "content"


class SlideContent(BaseModel):
    """Represents the structured content of a single slide."""

    slide_type: SlideType = Field(
        default=SlideType.CONTENT,
        description="The type of the slide (title or content)",
    )
    title: str = Field(
        ...,
        description="The main title of the slide",
        min_length=1,
    )
    subtitle: Optional[str] = Field(
        None,
        description="The subtitle of the slide (applicable for title slides)",
    )
    bullets: List[str] = Field(
        default_factory=list,
        description=(
            "List of bullet points for the slide content "
            "(applicable for content slides)"
        ),
    )
    speaker_notes: Optional[str] = Field(
        None,
        description="Optional presenter notes for this slide",
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
    slides: List[SlideContent] = Field(
        ...,
        description="The list of slides in the presentation",
    )


class PPTGenerationResult(BaseModel):
    """Output metadata returned after successful presentation generation."""

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
