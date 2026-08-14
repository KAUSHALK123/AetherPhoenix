from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Lifecycle events emitted across the system."""

    WORKFLOW_CREATED = "WORKFLOW_CREATED"
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_PAUSED = "WORKFLOW_PAUSED"
    WORKFLOW_RESUMED = "WORKFLOW_RESUMED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"

    PLANNING_STARTED = "PLANNING_STARTED"
    PLANNING_COMPLETED = "PLANNING_COMPLETED"

    COMPILATION_STARTED = "COMPILATION_STARTED"
    COMPILATION_COMPLETED = "COMPILATION_COMPLETED"

    TASK_QUEUED = "TASK_QUEUED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_RETRIED = "TASK_RETRIED"

    PERMISSION_REQUESTED = "PERMISSION_REQUESTED"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PERMISSION_REJECTED = "PERMISSION_REJECTED"

    SUPERVISION_STARTED = "SUPERVISION_STARTED"
    SUPERVISION_COMPLETED = "SUPERVISION_COMPLETED"
    SUPERVISION_FAILED = "SUPERVISION_FAILED"

    HEALING_STARTED = "HEALING_STARTED"
    HEALING_COMPLETED = "HEALING_COMPLETED"
    HEALING_FAILED = "HEALING_FAILED"

    ARTIFACT_CREATED = "ARTIFACT_CREATED"
    ARTIFACT_DELETED = "ARTIFACT_DELETED"

    TOOL_LOADED = "TOOL_LOADED"
    TOOL_FAILED = "TOOL_FAILED"

    FEEDBACK_GENERATED = "FEEDBACK_GENERATED"
    REPLANNING_TRIGGERED = "REPLANNING_TRIGGERED"


class EventSource(str, Enum):
    """Component sources that emit or consume events."""

    PLANNER = "PLANNER"
    WORKER = "WORKER"
    SUPERVISOR = "SUPERVISOR"
    HEALING = "HEALING"
    EXECUTION_ENGINE = "EXECUTION_ENGINE"
    PERMISSION_MANAGER = "PERMISSION_MANAGER"
    TOOL_REGISTRY = "TOOL_REGISTRY"
    ARTIFACT_MANAGER = "ARTIFACT_MANAGER"
    RUNTIME_KERNEL = "RUNTIME_KERNEL"
    FRONTEND = "FRONTEND"


class RuntimeEvent(BaseModel):
    """Event contract representing asynchronous messages on the Event Bus."""

    event_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    task_id: UUID | None = None
    event_type: EventType
    source_component: EventSource
    target_component: EventSource | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
