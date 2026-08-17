from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
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
    ESCALATED = "ESCALATED"


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
    changed_files: List[str] = Field(default_factory=list)
    changed_registry: List[str] = Field(default_factory=list)
    changed_variables: Dict[str, str] = Field(default_factory=dict)
    previous_values: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """Task contract representing an atomic executable unit of work."""

    task_id: UUID = Field(default_factory=uuid4)
    parent_task_id: Optional[UUID] = None
    workflow_id: UUID
    task_name: str
    description: str
    task_type: TaskType = TaskType.LEAF
    assigned_agent: str = "WorkerAgent"
    required_tool: str
    category: TaskCategory
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[UUID] = Field(default_factory=list)
    preconditions: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"
    expected_output: str
    artifact_location: Optional[str] = None
    success_criteria: List[str] = Field(default_factory=list)
    failure_criteria: List[str] = Field(default_factory=list)
    estimated_duration_seconds: Optional[int] = None
    status: TaskStatus = TaskStatus.CREATED
    retry_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    rollback_info: Optional[RollbackInfo] = None
    execution_logs: List[str] = Field(default_factory=list)
    artifacts_produced: List[str] = Field(default_factory=list)
