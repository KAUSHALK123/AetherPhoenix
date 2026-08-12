from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PermissionType(str, Enum):
    """Types of system permissions requested by agents."""

    ADMINISTRATOR = "ADMINISTRATOR"
    BROWSER_ACCESS = "BROWSER_ACCESS"
    FILE_SYSTEM = "FILE_SYSTEM"
    TERMINAL = "TERMINAL"
    POWERSHELL = "POWERSHELL"
    INTERNET = "INTERNET"
    REGISTRY = "REGISTRY"
    CLIPBOARD = "CLIPBOARD"
    DOWNLOADS = "DOWNLOADS"
    CAMERA = "CAMERA"
    MICROPHONE = "MICROPHONE"


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
    task_id: Optional[UUID] = None
    permission_type: PermissionType
    reason: str
    risk_level: RiskLevel
    status: PermissionStatus = PermissionStatus.PENDING
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
