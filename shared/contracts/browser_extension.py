from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class BrowserExtensionAction(str, Enum):
    """Supported browser extension actions."""

    DETECT_ACTIVE_TAB = "detect_active_tab"
    READ_PAGE_INFO = "read_page_info"
    NAVIGATE = "navigate"
    OPEN_NEW_TAB = "open_new_tab"
    INTERACT = "interact"
    EXTRACT_CONTENT = "extract_content"
    HEARTBEAT = "heartbeat"


class BrowserExtensionCommand(BaseModel):
    """Command sent from AetherPhoenix backend to Browser Extension."""

    command_id: str = Field(..., description="Unique identifier for the command")
    action: str = Field(..., description="Action to perform in browser")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )
    task_id: Optional[str] = Field(
        None, description="Workflow task ID requesting the action"
    )
    workflow_id: Optional[str] = Field(
        None, description="Workflow ID requesting the action"
    )
    timestamp: float = Field(..., description="Timestamp when command was dispatched")


class BrowserExtensionResponse(BaseModel):
    """Response returned from Browser Extension to AetherPhoenix backend."""

    command_id: str = Field(..., description="Identifier of matching command")
    success: bool = Field(..., description="Whether the operation succeeded")
    data: Optional[Dict[str, Any]] = Field(
        None, description="Structured result data from operation"
    )
    error: Optional[str] = Field(
        None, description="Error details if operation failed"
    )
    timestamp: float = Field(..., description="Timestamp when response was sent")


class ExtensionConnectionStatus(BaseModel):
    """Status model for the connected browser extension."""

    connected: bool = Field(
        ..., description="Whether an extension is currently connected"
    )
    client_id: Optional[str] = Field(
        None, description="Unique client connection ID"
    )
    active_tab_url: Optional[str] = Field(
        None, description="Current active tab URL"
    )
    active_tab_title: Optional[str] = Field(
        None, description="Current active tab title"
    )
    last_heartbeat: Optional[float] = Field(
        None, description="Timestamp of last heartbeat"
    )
