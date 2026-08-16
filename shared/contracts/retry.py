from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from shared.contracts.execution import TaskError
from shared.contracts.task import Task


class RetryStatus(str, Enum):
    """Execution status outcomes for a retry request."""

    TRIGGERED = "TRIGGERED"
    REJECTED_MAX_RETRIES = "REJECTED_MAX_RETRIES"
    REJECTED_NON_RETRYABLE = "REJECTED_NON_RETRYABLE"
    REJECTED_PERMISSION_DENIED = "REJECTED_PERMISSION_DENIED"
    REJECTED_INVALID_STATE = "REJECTED_INVALID_STATE"
    REJECTED_DESTRUCTIVE_UNAPPROVED = "REJECTED_DESTRUCTIVE_UNAPPROVED"
    ERROR = "ERROR"


class RecoveryPlan(BaseModel):
    """Recovery plan contract produced by Recovery Planner / Healing Agent."""

    plan_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    workflow_id: UUID
    strategy: str = "RETRY"
    is_retryable: bool = True
    requires_permission: bool = False
    backoff_seconds: float = 0.0
    replacement_tasks: List[Task] = Field(default_factory=list)
    updated_task_params: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RetryRequest(BaseModel):
    """Request contract for executing a task retry through the Retry Engine."""

    retry_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    workflow_id: UUID
    attempt_number: int = Field(default=1, ge=0)
    max_retries: int = Field(default=3, ge=1)
    error: Optional[TaskError] = None
    recovery_plan: Optional[RecoveryPlan] = None
    reason: Optional[str] = None
    delay_seconds: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RetryResult(BaseModel):
    """Result contract returned by the Retry Engine after processing a RetryRequest."""

    retry_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    workflow_id: UUID
    success: bool
    status: RetryStatus
    attempt_number: int = Field(default=0, ge=0)
    delay_seconds: float = 0.0
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
