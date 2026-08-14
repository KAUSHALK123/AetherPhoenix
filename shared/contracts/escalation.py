from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from shared.contracts.execution import HealingResult
from shared.contracts.permission import RiskLevel


class EscalationReason(str, Enum):
    """Classification of failure reasons triggering escalation."""

    PERMISSION_DENIED = "PERMISSION_DENIED"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
    MAX_HEALING_ATTEMPTS_EXCEEDED = "MAX_HEALING_ATTEMPTS_EXCEEDED"
    HIGH_RISK_OPERATION = "HIGH_RISK_OPERATION"
    UNKNOWN_CRITICAL_FAILURE = "UNKNOWN_CRITICAL_FAILURE"
    UNSUPPORTED_ERROR = "UNSUPPORTED_ERROR"
    USER_INTERVENTION_REQUIRED = "USER_INTERVENTION_REQUIRED"
    HARDWARE_FAILURE = "HARDWARE_FAILURE"
    DUPLICATE_ESCALATION = "DUPLICATE_ESCALATION"


class EscalationSeverity(str, Enum):
    """Severity levels for escalated failures."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EscalationRequest(BaseModel):
    """Payload requested when handing off an unrecoverable failure to the Escalation Handler."""

    request_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    task_id: UUID
    reason: EscalationReason
    details: str
    failure_context: Dict[str, Any] = Field(default_factory=dict)
    healing_history: List[HealingResult] = Field(default_factory=list)
    attempt_number: int = Field(default=1, ge=1)
    risk_level: Optional[RiskLevel] = None


class EscalationResult(BaseModel):
    """Structured result produced by Escalation Handler."""

    escalation_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    task_id: UUID
    reason: EscalationReason
    severity: EscalationSeverity
    requires_user_intervention: bool
    user_action_required: Optional[str] = None
    failure_context: Dict[str, Any] = Field(default_factory=dict)
    healing_history: List[HealingResult] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
