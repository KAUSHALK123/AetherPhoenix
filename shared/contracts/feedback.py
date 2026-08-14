from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from shared.contracts.execution import FailureType


class FailureSummary(BaseModel):
    """Summarizes a specific task failure for the Planner."""

    task_id: UUID
    task_name: str
    tool_used: str
    failure_type: FailureType
    error_message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealingSummary(BaseModel):
    """Summarizes healing attempts and outcomes for a task failure."""

    recovery_id: UUID = Field(default_factory=uuid4)
    attempts: int = Field(default=0, ge=0)
    strategies_attempted: list[str] = Field(default_factory=list)
    successful_strategy: str | None = None
    outcome: str  # "SUCCESS", "FAILED", "UNRECOVERABLE"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CapabilityFailureInfo(BaseModel):
    """Defines tool or capability failures useful for planning."""

    tool_name: str
    category: str
    is_permanent: bool = False
    details: str


class ReplanningContext(BaseModel):
    """Trigger details and contextual clues for replanning."""

    trigger_reason: str
    original_goal: str
    suggested_alternative_tools: list[str] = Field(default_factory=list)
    suggested_alternative_capabilities: list[str] = Field(default_factory=list)
    blocked_tasks: list[UUID] = Field(default_factory=list)


class PlannerFeedback(BaseModel):
    """
    Structured feedback package containing execution failure, healing,
    and capability failure summaries, providing context for the Planner to adapt.
    """

    feedback_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    failure_summary: FailureSummary | None = None
    healing_summary: HealingSummary | None = None
    capability_failure: CapabilityFailureInfo | None = None
    replanning_context: ReplanningContext | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_feedback_structure(self) -> "PlannerFeedback":
        """Ensures that the feedback package is meaningful and validated."""
        if (
            not self.failure_summary
            and not self.healing_summary
            and not self.capability_failure
        ):
            raise ValueError(
                "Feedback must contain at least a failure summary, healing summary, or capability failure info."
            )
        return self
