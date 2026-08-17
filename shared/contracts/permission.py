from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PermissionType(str, Enum):
    """Types of system permissions requested by agents."""

    ADMINISTRATOR = "ADMINISTRATOR"
    BROWSER_ACCESS = "BROWSER_ACCESS"
    FILE_SYSTEM = "FILE_SYSTEM"
    FILE_SYSTEM_WRITE = "FILE_SYSTEM_WRITE"
    FILE_WRITE = "FILE_WRITE"
    TERMINAL = "TERMINAL"
    POWERSHELL = "POWERSHELL"
    INTERNET = "INTERNET"
    REGISTRY = "REGISTRY"
    CLIPBOARD = "CLIPBOARD"
    DOWNLOADS = "DOWNLOADS"
    CAMERA = "CAMERA"
    MICROPHONE = "MICROPHONE"
    DESKTOP_AUTOMATION = "DESKTOP_AUTOMATION"


class PermissionStatus(str, Enum):
    """Approval status of a permission request."""

    PENDING = "PENDING"
    GRANTED = "GRANTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RiskLevel(str, Enum):
    """Assessed risk level for requested operations."""

    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PermissionRequest(BaseModel):
    """Permission contract representing security requests and approval state."""

    permission_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    task_id: UUID | None = None
    permission_type: PermissionType
    reason: str
    risk_level: RiskLevel
    status: PermissionStatus = PermissionStatus.PENDING
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: datetime | None = None
    expires_at: datetime | None = None
