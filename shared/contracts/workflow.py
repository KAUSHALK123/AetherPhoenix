from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from shared.contracts.artifact import Artifact
from shared.contracts.event import RuntimeEvent
from shared.contracts.execution import HealingResult
from shared.contracts.permission import PermissionRequest
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
    conversation_id: Optional[UUID] = None
    user_id: Optional[str] = None
    goal: str
    execution_mode: ExecutionMode = ExecutionMode.ASSISTED
    status: WorkflowStatus = WorkflowStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration_seconds: Optional[int] = None


class PlannerOutput(BaseModel):
    """Structured plan output produced by the Planner Agent."""

    workflow_spec: str
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict)
    estimated_time_seconds: int = Field(default=0, ge=0)
    risks: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    expected_outputs: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class ProgressState(BaseModel):
    """Real-time progress calculation for UI and monitoring."""

    total_tasks: int = Field(default=0, ge=0)
    completed_tasks: int = Field(default=0, ge=0)
    running_tasks: int = Field(default=0, ge=0)
    failed_tasks: int = Field(default=0, ge=0)
    pending_tasks: int = Field(default=0, ge=0)
    overall_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    estimated_remaining_time_seconds: Optional[int] = None


class SharedWorkflowState(BaseModel):
    """Centralized Shared Workflow State (SWS) runtime object.

    Serves as the single source of truth for all agents and components.
    """

    metadata: WorkflowMetadata
    planner_output: Optional[PlannerOutput] = None
    tasks: Dict[UUID, Task] = Field(default_factory=dict)
    execution_queue: List[UUID] = Field(default_factory=list)
    running_tasks: List[UUID] = Field(default_factory=list)
    completed_tasks: List[UUID] = Field(default_factory=list)
    failed_tasks: List[UUID] = Field(default_factory=list)
    progress: ProgressState = Field(default_factory=ProgressState)
    permissions: List[PermissionRequest] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    healing_history: List[HealingResult] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    events: List[RuntimeEvent] = Field(default_factory=list)
