from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    # Workflow
    WORKFLOW_CREATED = "WorkflowCreated"
    WORKFLOW_STARTED = "WorkflowStarted"
    WORKFLOW_PAUSED = "WorkflowPaused"
    WORKFLOW_RESUMED = "WorkflowResumed"
    WORKFLOW_CANCELLED = "WorkflowCancelled"
    WORKFLOW_COMPLETED = "WorkflowCompleted"
    WORKFLOW_FAILED = "WorkflowFailed"
    WORKFLOW_PERMANENTLY_FAILED = "WorkflowPermanentlyFailed"

    # Planning
    PLANNING_STARTED = "PlanningStarted"
    PLANNING_COMPLETED = "PlanningCompleted"

    # Compilation
    COMPILATION_STARTED = "CompilationStarted"
    COMPILATION_COMPLETED = "CompilationCompleted"

    # Task
    TASK_QUEUED = "TaskQueued"
    TASK_STARTED = "TaskStarted"
    TASK_COMPLETED = "TaskCompleted"
    TASK_FAILED = "TaskFailed"
    TASK_RETRIED = "TaskRetried"

    # Permission
    PERMISSION_REQUESTED = "PermissionRequested"
    PERMISSION_GRANTED = "PermissionGranted"
    PERMISSION_REJECTED = "PermissionRejected"

    # Healing
    HEALING_STARTED = "HealingStarted"
    HEALING_COMPLETED = "HealingCompleted"
    HEALING_FAILED = "HealingFailed"
    HEALING_ESCALATED = "HealingEscalated"
    ESCALATION_REQUESTED = "EscalationRequested"

    # Worker Re-execution
    WORKER_REEXECUTION_STARTED = "WorkerReexecutionStarted"
    WORKER_REEXECUTION_COMPLETED = "WorkerReexecutionCompleted"
    WORKER_REEXECUTION_FAILED = "WorkerReexecutionFailed"

    # Artifact
    ARTIFACT_CREATED = "ArtifactCreated"
    ARTIFACT_DELETED = "ArtifactDeleted"

    # Tool
    TOOL_LOADED = "ToolLoaded"
    TOOL_FAILED = "ToolFailed"

    # Feedback
    FEEDBACK_GENERATED = "FeedbackGenerated"
    REPLANNING_TRIGGERED = "ReplanningTriggered"


class NotificationCategory(str, Enum):
    WORKFLOW = "WORKFLOW"
    PERMISSION = "PERMISSION"
    TASK = "TASK"
    ARTIFACT = "ARTIFACT"
    HEALING = "HEALING"


class NotificationSeverity(str, Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(BaseModel):
    """
    Event model for the Event Bus.
    Represents a single event in the lightweight Pub/Sub architecture.
    """

    id: UUID = Field(default_factory=uuid4)
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    event_type: EventType | str
    timestamp: datetime = Field(default_factory=utc_now)
    source_component: str
    target_component: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class Notification(BaseModel):
    """
    User-facing notification data model created from EventBus events.
    """

    id: UUID = Field(default_factory=uuid4)
    event_id: Optional[str] = None
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    event_type: str
    title: str
    message: str
    category: NotificationCategory = NotificationCategory.WORKFLOW
    severity: NotificationSeverity = NotificationSeverity.INFO
    timestamp: datetime = Field(default_factory=utc_now)
    read: bool = False
    payload: Dict[str, Any] = Field(default_factory=dict)
