from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BrowserState(str, Enum):
    """Lifecycle states of a Browser Session."""
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    CLOSED = "closed"

class BrowserSession(BaseModel):
    """Model representing an active browser session."""
    session_id: str = Field(..., description="Unique identifier for the session")
    current_url: Optional[str] = Field(
        None, description="The URL currently loaded in the browser"
    )
    state: BrowserState = Field(
        default=BrowserState.IDLE, description="Current state of the browser"
    )
    start_time: float = Field(..., description="Timestamp when the session was created")
    
class BrowserResult(BaseModel):
    """Structured execution result for browser operations."""
    success: bool = Field(..., description="Whether the operation succeeded")
    data: Optional[Dict[str, Any]] = Field(
        None, description="Data extracted or returned by the operation"
    )
    error: Optional[str] = Field(
        None, description="Error message if the operation failed"
    )
