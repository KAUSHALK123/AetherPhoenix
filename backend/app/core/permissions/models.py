from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PermissionType(str, Enum):
    ADMINISTRATOR = "ADMINISTRATOR"
    BROWSER_ACCESS = "BROWSER_ACCESS"
    FILE_READ = "FILE_READ"
    FILE_WRITE = "FILE_WRITE"
    FILE_DELETE = "FILE_DELETE"
    FILE_SYSTEM = "FILE_SYSTEM"
    FILE_SYSTEM_WRITE = "FILE_SYSTEM_WRITE"
    TERMINAL = "TERMINAL"
    TERMINAL_EXECUTE = "TERMINAL_EXECUTE"
    POWERSHELL = "POWERSHELL"
    POWERSHELL_EXECUTE = "POWERSHELL_EXECUTE"
    INTERNET = "INTERNET"
    REGISTRY = "REGISTRY"
    REGISTRY_EDIT = "REGISTRY_EDIT"
    NETWORK_ACCESS = "NETWORK_ACCESS"
    ADMIN_PRIVILEGE = "ADMIN_PRIVILEGE"
    DESKTOP_AUTOMATION = "DESKTOP_AUTOMATION"
    SCREEN_CAPTURE = "SCREEN_CAPTURE"
    CLIPBOARD = "CLIPBOARD"
    DOWNLOADS = "DOWNLOADS"
    CAMERA = "CAMERA"
    MICROPHONE = "MICROPHONE"


class ExecutionMode(str, Enum):
    SAFE = "SAFE"
    ASSISTED = "ASSISTED"
    AUTONOMOUS = "AUTONOMOUS"


class PermissionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PermissionRequest(BaseModel):
    request_id: str
    workflow_id: str
    task_id: str
    permission_type: PermissionType
    reason: str
    context: Dict[str, Any] = Field(default_factory=dict)
    status: PermissionStatus = Field(default=PermissionStatus.PENDING)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class PermissionResponse(BaseModel):
    request_id: str
    status: PermissionStatus
    message: Optional[str] = None
