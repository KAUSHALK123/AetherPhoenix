import logging
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.root_cause_analyzer import RootCauseAnalysis, RootCauseCategory

logger = logging.getLogger(__name__)


class RecoveryStrategy(str, Enum):
    """Available strategies for recovering from a task failure."""

    RETRY = "RETRY"
    RESTART_TOOL = "RESTART_TOOL"
    WAIT = "WAIT"
    ALTERNATIVE_TOOL = "ALTERNATIVE_TOOL"
    ALTERNATIVE_WEBSITE = "ALTERNATIVE_WEBSITE"
    ALTERNATIVE_API = "ALTERNATIVE_API"
    REQUEST_PERMISSION_AGAIN = "REQUEST_PERMISSION_AGAIN"
    ESCALATE_USER = "ESCALATE_USER"
    CANCEL_WORKFLOW = "CANCEL_WORKFLOW"


class RecoveryPlan(BaseModel):
    """Executable recovery strategy specification produced by RecoveryPlanner."""

    plan_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    workflow_id: UUID
    strategy: RecoveryStrategy = Field(default=RecoveryStrategy.RETRY)
    description: str
    replacement_tasks: List[Task] = Field(default_factory=list)
    delay_seconds: float = Field(default=0.0, ge=0.0)
    requires_permission: bool = Field(default=False)
    is_executable: bool = Field(default=True)


class RecoveryPlanner:
    """Recovery Planner component responsible for selecting recovery strategy."""

    def plan(
        self,
        root_cause: RootCauseAnalysis,
        task: Task,
        state: SharedWorkflowState,
        max_healing_attempts: int = 5,
    ) -> RecoveryPlan:
        """Formulates a RecoveryPlan based on root cause analysis."""
        logger.info(
            f"RecoveryPlanner generating plan for task {task.task_id} "
            f"using strategy candidate '{root_cause.recommended_strategy}'"
        )

        strategy_str = root_cause.recommended_strategy
        replacement_tasks: List[Task] = []
        delay_seconds = 0.0
        requires_permission = False
        is_executable = True
        description = ""

        # Enforce non-recoverable escalation
        if not root_cause.is_recoverable:
            strategy = (
                RecoveryStrategy.REQUEST_PERMISSION_AGAIN
                if root_cause.category == RootCauseCategory.PERMISSION
                else (
                    RecoveryStrategy.CANCEL_WORKFLOW
                    if root_cause.category == RootCauseCategory.WORKFLOW
                    else RecoveryStrategy.ESCALATE_USER
                )
            )
            is_executable = False
            description = (
                f"Non-recoverable failure ({root_cause.summary}). "
                "Escalating recovery to system user."
            )
            return RecoveryPlan(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                strategy=strategy,
                description=description,
                replacement_tasks=[],
                delay_seconds=0.0,
                requires_permission=(
                    strategy == RecoveryStrategy.REQUEST_PERMISSION_AGAIN
                ),
                is_executable=is_executable,
            )

        try:
            strategy = RecoveryStrategy(strategy_str.upper())
        except ValueError:
            strategy = RecoveryStrategy.RETRY

        if strategy == RecoveryStrategy.RETRY:
            description = (
                f"Retrying task '{task.task_name}' directly with exponential backoff."
            )
            delay_seconds = min(5.0 * (2**task.retry_count), 60.0)

        elif strategy == RecoveryStrategy.RESTART_TOOL:
            description = (
                f"Restarting tool context for '{task.required_tool}' before retry."
            )
            delay_seconds = 2.0
            reset_task = Task(
                task_id=uuid4(),
                workflow_id=task.workflow_id,
                task_name=f"Reset Tool: {task.required_tool}",
                description=f"Automated tool context reset for {task.required_tool}",
                required_tool="system_tool",
                category=TaskCategory.OTHER,
                expected_output="tool_reset_completed",
                status=TaskStatus.READY,
                retry_count=0,
            )
            replacement_tasks.append(reset_task)

        elif strategy == RecoveryStrategy.ALTERNATIVE_TOOL:
            description = (
                f"Attempting task '{task.task_name}' with alternative tool."
            )
            alt_tool = self._get_alternative_tool(task.required_tool)
            if alt_tool:
                alt_task = Task(
                    task_id=uuid4(),
                    workflow_id=task.workflow_id,
                    task_name=f"{task.task_name} (Fallback)",
                    description=f"Alternative execution path using {alt_tool}",
                    required_tool=alt_tool,
                    category=task.category,
                    expected_output=task.expected_output,
                    status=TaskStatus.READY,
                    retry_count=0,
                    dependencies=list(task.dependencies),
                )
                replacement_tasks.append(alt_task)
            else:
                strategy = RecoveryStrategy.ESCALATE_USER
                is_executable = False
                description = (
                    f"No alternative tool available for '{task.required_tool}'."
                )

        elif strategy == RecoveryStrategy.WAIT:
            delay_seconds = 10.0
            description = (
                f"Waiting {delay_seconds} seconds before attempting task retry."
            )

        elif strategy == RecoveryStrategy.REQUEST_PERMISSION_AGAIN:
            requires_permission = True
            is_executable = False
            description = "Task requires explicit permission re-grant from user."

        else:
            strategy = RecoveryStrategy.ESCALATE_USER
            is_executable = False
            description = f"Unhandled recovery strategy for task {task.task_id}."

        validated_replacement_tasks = self._validate_replacement_tasks(
            replacement_tasks, state
        )

        plan = RecoveryPlan(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            strategy=strategy,
            description=description,
            replacement_tasks=validated_replacement_tasks,
            delay_seconds=delay_seconds,
            requires_permission=requires_permission,
            is_executable=is_executable,
        )

        logger.info(
            f"RecoveryPlan formulated: strategy={plan.strategy.value}, "
            f"executable={plan.is_executable}, "
            f"replacement_tasks={len(plan.replacement_tasks)}"
        )
        return plan

    def _get_alternative_tool(self, current_tool: str) -> Optional[str]:
        """Maps default tool names to alternative fallbacks if available."""
        fallbacks = {
            "browser_tool": "web_research_tool",
            "web_research_tool": "browser_tool",
            "pdf_generator": "document_generator",
            "pyautogui": "pywinauto",
        }
        return fallbacks.get(current_tool)

    def _validate_replacement_tasks(
        self, tasks: List[Task], state: SharedWorkflowState
    ) -> List[Task]:
        """Ensures replacement tasks conform to safety standards."""
        valid_tasks = []
        for t in tasks:
            if not t.task_name or not t.required_tool:
                logger.warning(f"Discarding invalid replacement task: {t}")
                continue
            valid_tasks.append(t)
        return valid_tasks
