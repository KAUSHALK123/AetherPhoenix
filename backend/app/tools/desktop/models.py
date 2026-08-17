from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WindowBounds(BaseModel):
    """Coordinates and dimensions of a desktop window."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


class WindowInfo(BaseModel):
    """Detailed information describing an OS desktop window."""

    handle: int | str
    title: str
    process_id: Optional[int] = None
    process_name: Optional[str] = None
    is_visible: bool = True
    is_active: bool = False
    bounds: Optional[WindowBounds] = None
    class_name: Optional[str] = None


class ApplicationInfo(BaseModel):
    """Metadata and execution state of a desktop application process."""

    process_id: int
    name: str
    path: Optional[str] = None
    title: Optional[str] = None
    status: str = "running"
    launched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None


class ScreenResolution(BaseModel):
    """Display resolution dimensions."""

    width: int
    height: int


class DesktopSessionConfig(BaseModel):
    """Configuration governing desktop session boundaries and security."""

    session_timeout_seconds: float = Field(default=300.0, ge=0.0)
    idle_timeout_seconds: float = Field(default=120.0, ge=0.0)
    max_applications: int = Field(default=10, ge=1)
    allowed_applications: Optional[List[str]] = None


class DesktopSessionInfo(BaseModel):
    """Summary contract for an active or recorded desktop session."""

    session_id: UUID = Field(default_factory=uuid4)
    workflow_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    is_active: bool = True
    active_applications: List[int] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DesktopState(BaseModel):
    """Complete snapshot of the user's desktop environment."""

    screen_resolution: ScreenResolution
    active_window: Optional[WindowInfo] = None
    open_windows: List[WindowInfo] = Field(default_factory=list)
    running_applications: List[ApplicationInfo] = Field(default_factory=list)
    session: Optional[DesktopSessionInfo] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DesktopActionResult(BaseModel):
    """Standardized result returned by desktop automation operations."""

    action: str
    success: bool
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
