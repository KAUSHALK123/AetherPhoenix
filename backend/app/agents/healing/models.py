"""
AetherPhoenix — Healing Agent & Error Parser Data Models
==========================================================
Normalized error representation and error classification models for the Healing Agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ErrorSource(str, Enum):
    """Identifies the architectural layer or component where an error originated."""

    WORKER = "WORKER"
    TOOL = "TOOL"
    FILESYSTEM = "FILESYSTEM"
    BROWSER = "BROWSER"
    POWERSHELL = "POWERSHELL"
    NETWORK = "NETWORK"
    PERMISSION = "PERMISSION"
    WORKFLOW = "WORKFLOW"
    SYSTEM = "SYSTEM"
    UNKNOWN = "UNKNOWN"


class ErrorCategory(str, Enum):
    """Categorizes the nature of an execution failure for recovery analysis."""

    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    NETWORK_ERROR = "NETWORK_ERROR"
    INVALID_ARTIFACT = "INVALID_ARTIFACT"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    UNKNOWN = "UNKNOWN"


class ErrorSeverity(str, Enum):
    """Defines the impact and severity of an error."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NormalizedError(BaseModel):
    """
    Normalized, structured representation of an execution failure.

    This model serves as the single source of truth for the Healing Agent
    when analyzing failures across Worker, Tool, Supervisor, Permission,
    Filesystem, Network, Browser, PowerShell, and System layers.

    Attributes
    ----------
    error_id:
        Unique identifier for this normalized error event.
    source:
        The originating source/component of the error.
    category:
        The failure category (e.g. TIMEOUT, PERMISSION_DENIED).
    severity:
        The assigned severity level of the error.
    is_retryable:
        Whether the error is classified as potentially retryable.
    message:
        Human-readable normalized error message.
    code:
        Namespaced error code identifier (e.g. ``"TIMEOUT_ERROR"``).
    context:
        Extracted supplementary details (e.g. task_id, tool_name, exit_code).
    original_error:
        Original raw error representation preserved intact.
    timestamp:
        UTC timestamp of when the error was normalized.
    """

    error_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the normalized error instance.",
    )
    source: ErrorSource = Field(
        default=ErrorSource.UNKNOWN,
        description="Architectural layer or component where the error originated.",
    )
    category: ErrorCategory = Field(
        default=ErrorCategory.UNKNOWN,
        description="Classification category of the error.",
    )
    severity: ErrorSeverity = Field(
        default=ErrorSeverity.HIGH,
        description="Severity level assigned to the error.",
    )
    is_retryable: bool = Field(
        default=False,
        description="Whether this error is potentially retryable by Healing Agent.",
    )
    message: str = Field(
        ...,
        description="Normalized human-readable error description.",
    )
    code: str = Field(
        default="UNKNOWN_ERROR",
        description="Namespaced error code string.",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted runtime context metadata.",
    )
    original_error: Any = Field(
        default=None,
        description="Original raw error object or string preserved intact.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of error normalization.",
    )

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
    }

    @property
    def normalized_code(self) -> str:
        return self.code

    @property
    def raw_message(self) -> str:
        return self.message

    @property
    def is_transient(self) -> bool:
        return self.is_retryable


__all__ = [
    "ErrorSource",
    "ErrorCategory",
    "ErrorSeverity",
    "NormalizedError",
]
