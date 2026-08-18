from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class CaptureSource(str, Enum):
    """Source environment for screenshot capture."""

    DESKTOP = "DESKTOP"
    BROWSER = "BROWSER"
    REGION = "REGION"


class ImageFormat(str, Enum):
    """Supported output image formats for screenshots."""

    PNG = "PNG"
    JPEG = "JPEG"
    WEBP = "WEBP"


class CaptureRegion(BaseModel):
    """
    Defines a bounding box for region-based screenshot capture.
    """

    x: int = Field(..., ge=0, description="X coordinate of top-left corner")
    y: int = Field(..., ge=0, description="Y coordinate of top-left corner")
    width: int = Field(..., gt=0, description="Width of the capture region in pixels")
    height: int = Field(..., gt=0, description="Height of the capture region in pixels")

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Returns tuple representation: (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    def to_bbox(self) -> Tuple[int, int, int, int]:
        """Returns bounding box tuple: (left, top, right, bottom)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


class ScreenshotRequest(BaseModel):
    """
    Input request model for screenshot capture operations.
    """

    source: CaptureSource = Field(
        default=CaptureSource.DESKTOP,
        description="Target capture source (DESKTOP, BROWSER, REGION)",
    )
    region: Optional[CaptureRegion] = Field(
        default=None,
        description="Optional specific coordinate region to capture",
    )
    format: ImageFormat = Field(
        default=ImageFormat.PNG,
        description="Desired image format for output file",
    )
    quality: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Compression quality (1-100) for JPEG/WEBP",
    )
    output_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional custom destination path; if omitted, managed temp storage is used"
        ),
    )
    full_page: bool = Field(
        default=False,
        description="For browser capture: capture entire scrollable page when True",
    )
    workflow_id: Optional[UUID] = Field(
        default=None,
        description="Associated workflow ID",
    )
    task_id: Optional[UUID] = Field(
        default=None,
        description="Associated task ID",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional contextual metadata attached to request",
    )

    @field_validator("format", mode="before")
    @classmethod
    def normalize_format(cls, v: Any) -> ImageFormat:
        if isinstance(v, str):
            v = v.upper()
            if v in ("JPG", "JPEG"):
                return ImageFormat.JPEG
        return v


class ScreenshotResult(BaseModel):
    """
    Output metadata contract for captured screenshots.
    """

    screenshot_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the captured screenshot",
    )
    filepath: str = Field(
        ...,
        description="Absolute path to the screenshot image file",
    )
    file_name: str = Field(
        ...,
        description="File name of the captured screenshot",
    )
    source: CaptureSource = Field(
        ...,
        description="Source environment from which the screenshot was taken",
    )
    format: ImageFormat = Field(
        ...,
        description="Image encoding format (PNG, JPEG, WEBP)",
    )
    width: int = Field(
        ...,
        ge=1,
        description="Image width in pixels",
    )
    height: int = Field(
        ...,
        ge=1,
        description="Image height in pixels",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="File size in bytes",
    )
    checksum: str = Field(
        ...,
        description="SHA-256 hash of the screenshot image content",
    )
    captured_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the screenshot was captured",
    )
    status: str = Field(
        default="SUCCESS",
        description="Status of the capture operation (SUCCESS / FAILED)",
    )
    is_temporary: bool = Field(
        default=True,
        description="Flag indicating if the file resides in managed temporary storage",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if the capture failed",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metrics and additional metadata",
    )
