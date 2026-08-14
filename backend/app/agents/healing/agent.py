from typing import Any, Dict, Optional, Tuple

from backend.app.agents.healing.error_parser import ErrorParser
from backend.app.agents.healing.recovery_planner import RecoveryPlanner
from backend.app.agents.healing.root_cause_analyzer import RootCauseAnalyzer
from backend.app.agents.healing.validator import validate_recovery_plan
from shared.contracts.execution import HealingResult, TaskFailureReport
from shared.contracts.recovery_plan import (
    ErrorParserOutput,
    RecoveryPlan,
    RootCauseAnalysis,
)


class HealingAgent:
    """
    Healing Agent Core.
    Orchestrates ErrorParser, RootCauseAnalyzer, and RecoveryPlanner to handle
    task failures.
    Crucially: The Healing Agent generates and validates structured recovery
    plans, but DOES NOT execute recovery actions directly.
    """

    def __init__(self):
        self.error_parser = ErrorParser()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.recovery_planner = RecoveryPlanner()

    def plan_recovery(
        self,
        failure_report: TaskFailureReport,
        task_context: Optional[Dict[str, Any]] = None,
    ) -> RecoveryPlan:
        """
        Consumes a failure report and returns a validated RecoveryPlan.
        """
        parsed_error: ErrorParserOutput = self.error_parser.parse(
            failure_report, task_context
        )
        root_cause: RootCauseAnalysis = self.root_cause_analyzer.analyze(
            parsed_error, task_context
        )
        plan: RecoveryPlan = self.recovery_planner.plan(
            parsed_error, root_cause, task_context
        )

        # Ensure validation check
        validate_recovery_plan(plan)
        return plan

    def handle_failure(
        self,
        failure_report: TaskFailureReport,
        task_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[HealingResult, RecoveryPlan]:
        """
        Processes a failure report into a HealingResult and RecoveryPlan without
        executing recovery actions.
        """
        plan = self.plan_recovery(failure_report, task_context)

        healing_result = HealingResult(
            recovery_id=plan.plan_id,
            task_id=failure_report.task_id,
            workflow_id=failure_report.workflow_id,
            root_cause=plan.root_cause,
            recovery_strategy=plan.strategy_name,
            replacement_tasks=[],
            attempt_number=1,
            success=plan.is_viable and plan.validation_status == "VALID",
        )

        return healing_result, plan
