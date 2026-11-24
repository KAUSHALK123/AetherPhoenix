from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BrowserState(str, Enum):
    """Lifecycle states of a Browser Session."""

    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    ACTING = "acting"
    VERIFYING = "verifying"
    ERROR = "error"
    CLOSED = "closed"


class BrowserSession(BaseModel):
    """Model representing an active browser session."""

    session_id: str = Field(..., description="Unique identifier for the session")
    current_url: str | None = Field(
        None, description="The URL currently loaded in the browser"
    )
    page_title: str | None = Field(
        None, description="The title of the active webpage"
    )
    state: BrowserState = Field(
        default=BrowserState.IDLE, description="Current state of the browser"
    )
    start_time: float = Field(..., description="Timestamp when the session was created")
    tab_count: int = Field(default=1, description="Number of open tabs")
    active_tab_index: int = Field(default=0, description="Index of currently active tab")
    tabs: list[dict[str, Any]] = Field(
        default_factory=list, description="Metadata for open tabs"
    )


class BrowserResult(BaseModel):
    """Structured execution result for browser operations."""

    success: bool = Field(..., description="Whether the operation succeeded")
    data: dict[str, Any] | None = Field(
        None, description="Data extracted or returned by the operation"
    )
    error: str | None = Field(None, description="Error message if the operation failed")
