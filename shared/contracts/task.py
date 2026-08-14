from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Distinguishes between container/phase tasks and executable leaf tasks."""

    PHASE = "PHASE"
    LEAF = "LEAF"


class TaskStatus(str, Enum):
    """Execution status of an individual task."""

    CREATED = "CREATED"
    READY = "READY"
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    HEALING = "HEALING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class TaskPriority(str, Enum):
    """Priority level for task scheduling."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskCategory(str, Enum):
    """Functional categories for worker tasks."""

    BROWSER = "BROWSER"
    DESKTOP = "DESKTOP"
    FILE_SYSTEM = "FILE_SYSTEM"
    WEB_RESEARCH = "WEB_RESEARCH"
    WEB_SCRAPING = "WEB_SCRAPING"
    OCR = "OCR"
    VISION = "VISION"
    GIT = "GIT"
    POWERSHELL = "POWERSHELL"
    PYTHON = "PYTHON"
    PPT_GENERATION = "PPT_GENERATION"
    PDF_GENERATION = "PDF_GENERATION"
    CODE_GENERATION = "CODE_GENERATION"
    FILE_COMPRESSION = "FILE_COMPRESSION"
    SEARCH = "SEARCH"
    OTHER = "OTHER"


class DependencyType(str, Enum):
    """Graph dependency execution relationship."""

    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"


class TaskDependency(BaseModel):
    """Dependency relationship between tasks in the workflow graph."""

    parent_task_id: UUID
    child_task_id: UUID
    dependency_type: DependencyType = DependencyType.SEQUENTIAL


class RollbackInfo(BaseModel):
    """Rollback instructions for destructive task operations."""

    rollback_point: str
    changed_files: list[str] = Field(default_factory=list)
    changed_registry: list[str] = Field(default_factory=list)
    changed_variables: dict[str, str] = Field(default_factory=dict)
    previous_values: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """Task contract representing an atomic executable unit of work."""

    task_id: UUID = Field(default_factory=uuid4)
    parent_task_id: UUID | None = None
    workflow_id: UUID
    task_name: str
    description: str
    task_type: TaskType = TaskType.LEAF
    assigned_agent: str = "WorkerAgent"
    required_tool: str
    category: TaskCategory
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[UUID] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    risk_level: str = "LOW"
    expected_output: str
    artifact_location: str | None = None
    success_criteria: list[str] = Field(default_factory=list)
    failure_criteria: list[str] = Field(default_factory=list)
    estimated_duration_seconds: int | None = None
    status: TaskStatus = TaskStatus.CREATED
    retry_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    rollback_info: RollbackInfo | None = None
    execution_logs: list[str] = Field(default_factory=list)
    artifacts_produced: list[str] = Field(default_factory=list)
    current_attempt_id: UUID | None = None
    attempt_history: list[dict[str, Any]] = Field(default_factory=list)
