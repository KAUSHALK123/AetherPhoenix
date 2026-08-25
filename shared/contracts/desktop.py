from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MouseActionType(str, Enum):
    """Types of supported mouse actions."""

    GET_POSITION = "get_position"
    MOVE = "move"
    CLICK = "click"
    RIGHT_CLICK = "right_click"
    DOUBLE_CLICK = "double_click"
    SCROLL = "scroll"


class MouseButton(str, Enum):
    """Supported mouse buttons."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class MousePosition(BaseModel):
    """Representation of 2D screen coordinates."""

    x: int = Field(..., description="X-coordinate (horizontal)")
    y: int = Field(..., description="Y-coordinate (vertical)")


class ScreenResolution(BaseModel):
    """Resolution of the primary desktop display."""

    width: int = Field(..., gt=0, description="Display width in pixels")
    height: int = Field(..., gt=0, description="Display height in pixels")


class MouseActionRequest(BaseModel):
    """Contract for requesting controlled mouse interactions."""

    action: MouseActionType = Field(..., description="The type of mouse action")
    x: int | None = Field(
        default=None, description="Target X coordinate on the desktop screen"
    )
    y: int | None = Field(
        default=None, description="Target Y coordinate on the desktop screen"
    )
    button: MouseButton = Field(
        default=MouseButton.LEFT, description="Mouse button for click actions"
    )
    clicks: int = Field(
        default=1, description="Number of clicks or scroll clicks count"
    )
    duration: float = Field(
        default=0.5,
        ge=0.0,
        le=30.0,
        description="Duration in seconds for the mouse action",
    )
    interval: float = Field(
        default=0.1,
        ge=0.0,
        le=5.0,
        description="Interval between multi-click operations",
    )
    timeout: float = Field(
        default=10.0,
        gt=0.0,
        le=60.0,
        description="Execution timeout in seconds",
    )
    workflow_id: UUID | None = Field(default=None, description="Associated workflow ID")
    task_id: UUID | None = Field(default=None, description="Associated task ID")


class MouseActionResult(BaseModel):
    """Structured execution output for a mouse interaction."""

    action: MouseActionType = Field(..., description="Executed mouse action type")
    success: bool = Field(
        default=True, description="Indicates whether the action succeeded"
    )
    position: MousePosition | None = Field(
        default=None, description="Mouse cursor coordinates after action"
    )
    execution_time_ms: float = Field(
        default=0.0, ge=0.0, description="Execution duration in milliseconds"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional action-specific details"
    )
    error: str | None = Field(
        default=None, description="Error message if execution failed"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the execution result",
    )
