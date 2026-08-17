from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ToolState(str, Enum):
    """Lifecycle states of a Tool."""

    INSTALLED = "installed"
    READY = "ready"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"
    UPDATING = "updating"
    DISABLED = "disabled"


class ToolHealth(str, Enum):
    """Health status of a Tool."""

    HEALTHY = "healthy"
    WARNING = "warning"
    FAILED = "failed"
    UNKNOWN = "unknown"


class Tool(BaseModel):
    """
    Tool contract defining a concrete implementation of a capability.
    """

    tool_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Unique string identifier for the tool")
    version: str = Field(default="1.0.0")
    status: ToolState = Field(default=ToolState.INSTALLED)
    health: ToolHealth = Field(default=ToolHealth.UNKNOWN)
    adapter: str = Field(
        ..., description="The adapter implementation that runs this tool"
    )
    dependencies: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
