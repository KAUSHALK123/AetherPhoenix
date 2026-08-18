from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from shared.contracts.execution import TaskError
from shared.contracts.task import TaskCategory, TaskStatus


class TaskHistoryRecord(BaseModel):
    """
    Historical snapshot record of an individual task execution attempt or lifecycle status change.
    """

    history_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this history record entry",
    )
    task_id: UUID = Field(..., description="ID of the task being recorded")
    workflow_id: UUID = Field(..., description="ID of the parent workflow")
    parent_task_id: UUID | None = Field(
        default=None, description="Optional parent task ID in workflow graph"
    )
    task_name: str = Field(..., description="Human-readable task name")
    task_category: TaskCategory | str = Field(
        ..., description="Functional category of the task"
    )
    assigned_agent: str = Field(
        default="WorkerAgent", description="Agent responsible for execution"
    )
    required_tool: str | None = Field(
        default=None, description="Required tool name for task execution"
    )
    status: TaskStatus = Field(
        default=TaskStatus.CREATED, description="Execution status recorded"
    )
    retry_count: int = Field(
        default=0, ge=0, description="Total retries performed for task"
    )
    attempt_number: int = Field(
        default=1, ge=1, description="Specific attempt number of this execution"
    )
    inputs: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized inputs passed to task"
    )
    outputs: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized outputs produced by task"
    )
    error: TaskError | None = Field(
        default=None, description="Error details if execution failed"
    )
    execution_time_ms: float = Field(
        default=0.0, ge=0.0, description="Execution duration in milliseconds"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp",
    )
    started_at: datetime | None = Field(
        default=None, description="Task execution start timestamp"
    )
    completed_at: datetime | None = Field(
        default=None, description="Task execution completion timestamp"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional contextual metadata"
    )


class WorkflowHistoryRecord(BaseModel):
    """
    Historical summary record of a workflow lifecycle and its associated tasks.
    """

    workflow_id: UUID = Field(..., description="Unique workflow identifier")
    conversation_id: UUID | None = Field(
        default=None, description="Associated conversation identifier"
    )
    user_id: str | None = Field(default=None, description="Associated user identifier")
    goal: str = Field(..., description="Overall goal prompt of the workflow")
    status: str = Field(default="CREATED", description="Workflow lifecycle status")
    total_tasks: int = Field(default=0, ge=0, description="Total number of tasks")
    completed_tasks: int = Field(
        default=0, ge=0, description="Number of completed tasks"
    )
    failed_tasks: int = Field(default=0, ge=0, description="Number of failed tasks")
    tasks_history: list[TaskHistoryRecord] = Field(
        default_factory=list, description="Chronological history of workflow tasks"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Workflow creation timestamp",
    )
    started_at: datetime | None = Field(
        default=None, description="Workflow start timestamp"
    )
    completed_at: datetime | None = Field(
        default=None, description="Workflow completion timestamp"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Supplementary workflow metadata"
    )
