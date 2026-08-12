from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Status lifecycle of a worker task execution event."""

    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    TOOL_FAILED = "TOOL_FAILED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionPhase(str, Enum):
    """Granular execution phase within a worker task lifecycle."""

    TASK_START = "TASK_START"
    TOOL_SELECTION = "TOOL_SELECTION"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    OUTPUT_COLLECTION = "OUTPUT_COLLECTION"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAILED = "TASK_FAILED"


class WorkerExecutionLog(BaseModel):
    """
    Structured execution log event contract for Worker Agent operations.
    Captured per execution step for auditability and runtime observability.
    """

    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique execution run identifier for this specific task attempt",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Cross-cutting trace or session identifier for request tracking",
    )
    workflow_id: UUID = Field(..., description="ID of the parent workflow")
    task_id: UUID = Field(..., description="ID of the executed task")
    task_name: str = Field(..., description="Name of the executed task")
    tool_name: str = Field(..., description="Name of the resolved tool")
    phase: ExecutionPhase = Field(..., description="Granular task execution phase")
    status: ExecutionStatus = Field(
        ..., description="Current status of execution phase"
    )
    duration_ms: float = Field(
        default=0.0, ge=0.0, description="Elapsed execution duration in milliseconds"
    )
    inputs: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized task or tool input payload"
    )
    outputs: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized task or tool output result"
    )
    error_code: str | None = Field(
        default=None, description="Standardized error code if phase or task failed"
    )
    error_message: str | None = Field(
        default=None, description="Human-readable error description"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the execution log event",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Supplementary contextual metadata"
    )
