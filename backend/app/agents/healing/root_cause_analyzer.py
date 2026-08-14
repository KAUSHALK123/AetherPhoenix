import logging
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from shared.contracts.task import Task
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.error_parser import ErrorCategory, ParsedError

logger = logging.getLogger(__name__)


class RootCauseCategory(str, Enum):
    """Classification categories for failure root causes."""

    INFRASTRUCTURE = "INFRASTRUCTURE"
    TOOL = "TOOL"
    PERMISSION = "PERMISSION"
    NETWORK = "NETWORK"
    RUNTIME = "RUNTIME"
    USER = "USER"
    WORKFLOW = "WORKFLOW"
    EXTERNAL_API = "EXTERNAL_API"
    UNKNOWN = "UNKNOWN"


class RootCauseAnalysis(BaseModel):
    """Structured root cause diagnostic report."""

    root_cause_id: UUID = Field(default_factory=uuid4)
    category: RootCauseCategory = Field(default=RootCauseCategory.UNKNOWN)
    summary: str
    explanation: str
    is_recoverable: bool = Field(default=True)
    recommended_strategy: str = Field(default="RETRY")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class RootCauseAnalyzer:
    """Root Cause Analyzer component for classifying failures."""

    def analyze(
        self,
        parsed_error: ParsedError,
        task: Task,
        state: SharedWorkflowState,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> RootCauseAnalysis:
        """Analyzes normalized errors to produce a RootCauseAnalysis report."""
        logger.info(
            f"RootCauseAnalyzer evaluating task {task.task_id} "
            f"with error code {parsed_error.normalized_code}"
        )

        category = RootCauseCategory.UNKNOWN
        summary = ""
        explanation = ""
        is_recoverable = True
        recommended_strategy = "RETRY"
        confidence_score = 0.9

        code = parsed_error.normalized_code
        err_cat = parsed_error.category

        # 1. PERMISSION Root Cause
        if err_cat == ErrorCategory.PERMISSIONS or code == "PERMISSION_DENIED":
            category = RootCauseCategory.PERMISSION
            summary = "Execution failed due to missing user permission."
            explanation = (
                f"Task '{task.task_name}' required permissions that were denied: "
                f"{parsed_error.raw_message}"
            )
            is_recoverable = False
            recommended_strategy = "REQUEST_PERMISSION_AGAIN"
            confidence_score = 0.95

        # 2. TOOL Root Cause
        elif (
            err_cat == ErrorCategory.TOOL
            or code in ("TOOL_UNAVAILABLE", "TOOL_NOT_FOUND")
        ):
            category = RootCauseCategory.TOOL
            summary = f"Required tool '{task.required_tool}' is unavailable."
            explanation = (
                f"The tool '{task.required_tool}' requested by task '{task.task_name}' "
                f"could not be loaded: {parsed_error.raw_message}"
            )
            is_recoverable = True
            recommended_strategy = "ALTERNATIVE_TOOL"
            confidence_score = 0.95

        # 3. NETWORK Root Cause
        elif (
            err_cat == ErrorCategory.NETWORK
            or code in ("NETWORK_TIMEOUT", "NETWORK_ERROR")
        ):
            category = RootCauseCategory.NETWORK
            summary = "Transient network timeout or connectivity interruption."
            explanation = (
                "Task execution failed due to network latency: "
                f"{parsed_error.raw_message}"
            )
            is_recoverable = True
            recommended_strategy = "RETRY"
            confidence_score = 0.9

        # 4. BROWSER / RUNTIME Root Cause
        elif err_cat == ErrorCategory.BROWSER or code == "BROWSER_TIMEOUT":
            category = RootCauseCategory.RUNTIME
            summary = "Browser execution context timed out or crashed."
            explanation = (
                "Automation session in Playwright/Browser timed out: "
                f"{parsed_error.raw_message}"
            )
            is_recoverable = True
            recommended_strategy = "RESTART_TOOL"
            confidence_score = 0.85

        # 5. FILESYSTEM Root Cause
        elif err_cat == ErrorCategory.FILESYSTEM:
            category = RootCauseCategory.INFRASTRUCTURE
            summary = "Filesystem path access or file IO error."
            explanation = (
                "Task experienced filesystem IO error: "
                f"{parsed_error.raw_message}"
            )
            is_recoverable = parsed_error.is_transient
            recommended_strategy = "RETRY" if is_recoverable else "ESCALATE_USER"
            confidence_score = 0.85

        # 6. WORKFLOW / DEPENDENCY Root Cause
        elif code in ("DEPENDENCY_FAILED", "WORKFLOW_BLOCKED"):
            category = RootCauseCategory.WORKFLOW
            summary = "Prerequisites failed or workflow state blocked execution."
            explanation = (
                "Task cannot proceed due to failed dependencies: "
                f"{parsed_error.raw_message}"
            )
            is_recoverable = False
            recommended_strategy = "CANCEL_WORKFLOW"
            confidence_score = 0.95

        # 7. Default / RUNTIME Failure
        else:
            category = RootCauseCategory.RUNTIME
            summary = "General runtime execution failure during task processing."
            explanation = (
                f"Task encountered runtime failure: {parsed_error.raw_message}"
            )
            is_recoverable = parsed_error.is_transient or (task.retry_count < 3)
            recommended_strategy = "RETRY" if is_recoverable else "ESCALATE_USER"
            confidence_score = 0.75

        if (
            getattr(task, "risk_level", "LOW") in ("HIGH", "CRITICAL")
            and not parsed_error.is_transient
        ):
            is_recoverable = False
            recommended_strategy = "ESCALATE_USER"
            summary += " (Destructive operation safety block)"

        logger.info(
            f"RootCauseAnalyzer result: category={category.value}, "
            f"recoverable={is_recoverable}, strategy={recommended_strategy}"
        )

        return RootCauseAnalysis(
            category=category,
            summary=summary,
            explanation=explanation,
            is_recoverable=is_recoverable,
            recommended_strategy=recommended_strategy,
            confidence_score=confidence_score,
        )
