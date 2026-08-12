from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PermissionType(str, Enum):
    BROWSER_ACCESS = "BROWSER_ACCESS"
    FILE_READ = "FILE_READ"
    FILE_WRITE = "FILE_WRITE"
    FILE_DELETE = "FILE_DELETE"
    TERMINAL_EXECUTE = "TERMINAL_EXECUTE"
    POWERSHELL_EXECUTE = "POWERSHELL_EXECUTE"
    REGISTRY_EDIT = "REGISTRY_EDIT"
    NETWORK_ACCESS = "NETWORK_ACCESS"
    ADMIN_PRIVILEGE = "ADMIN_PRIVILEGE"


class ExecutionMode(str, Enum):
    SAFE = "SAFE"
    ASSISTED = "ASSISTED"
    AUTONOMOUS = "AUTONOMOUS"


class PermissionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PermissionRequest(BaseModel):
    request_id: str
    workflow_id: str
    task_id: str
    permission_type: PermissionType
    reason: str
    context: Dict[str, Any] = Field(default_factory=dict)
    status: PermissionStatus = Field(default=PermissionStatus.PENDING)


class PermissionResponse(BaseModel):
    request_id: str
    status: PermissionStatus
    message: Optional[str] = None
