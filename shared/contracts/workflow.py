from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from shared.contracts.artifact import Artifact
from shared.contracts.event import RuntimeEvent
from shared.contracts.execution import HealingResult, SupervisorValidation
from shared.contracts.feedback import PlannerFeedback
from shared.contracts.permission import PermissionRequest
from shared.contracts.planner import PlannerOutput
from shared.contracts.task import Task


class WorkflowStatus(str, Enum):
    """Workflow status states."""

    CREATED = "CREATED"
    PLANNING = "PLANNING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionMode(str, Enum):
    """Workflow execution mode controls permission behavior."""

    SAFE = "SAFE"
    ASSISTED = "ASSISTED"
    AUTONOMOUS = "AUTONOMOUS"


class WorkflowMetadata(BaseModel):
    """Top-level workflow identification and lifecycle metadata."""

    workflow_id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID | None = None
    user_id: str | None = None
    goal: str
    execution_mode: ExecutionMode = ExecutionMode.ASSISTED
    status: WorkflowStatus = WorkflowStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_duration_seconds: int | None = None


class ProgressState(BaseModel):
    """Real-time progress calculation for UI and monitoring."""

    total_tasks: int = Field(default=0, ge=0)
    completed_tasks: int = Field(default=0, ge=0)
    running_tasks: int = Field(default=0, ge=0)
    failed_tasks: int = Field(default=0, ge=0)
    pending_tasks: int = Field(default=0, ge=0)
    blocked_tasks: int = Field(default=0, ge=0)
    overall_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    execution_duration_seconds: float = Field(default=0.0, ge=0.0)
    estimated_remaining_time_seconds: int | None = None


class SharedWorkflowState(BaseModel):
    """Centralized Shared Workflow State (SWS) runtime object.

    Serves as the single source of truth for all agents and components.
    """

    metadata: WorkflowMetadata
    planner_output: PlannerOutput | None = None
    tasks: dict[UUID, Task] = Field(default_factory=dict)
    execution_queue: list[UUID] = Field(default_factory=list)
    running_tasks: list[UUID] = Field(default_factory=list)
    completed_tasks: list[UUID] = Field(default_factory=list)
    failed_tasks: list[UUID] = Field(default_factory=list)
    progress: ProgressState = Field(default_factory=ProgressState)
    permissions: list[PermissionRequest] = Field(default_factory=list)
    validations: dict[UUID, SupervisorValidation] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    logs: list[dict[str, Any]] = Field(default_factory=list)
    healing_history: list[HealingResult] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    events: list[RuntimeEvent] = Field(default_factory=list)
    feedback: PlannerFeedback | None = Field(
        None,
        description="Execution/healing structured feedback generated during workflow failures.",
    )
