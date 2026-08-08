import logging

from shared.contracts.planner import PlannerRequest, PlannerResponse
from shared.contracts.workflow import PlannerOutput

from app.agents.planner.engines import (
    GoalExtractionEngine,
    PermissionDetectionEngine,
    RiskAnalysisEngine,
    TaskDecompositionEngine,
)
from app.agents.planner.priority_engine import PriorityAssignmentEngine
from app.planner.analyzer import RequirementAnalyzer
from app.planner.clarifier import ClarificationEngine

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    End-to-End Orchestrator for the Planning Pipeline.
    Integrates modules from Sprint 2 to transform user requests into execution plans.
    """

    def __init__(self):
        self.requirement_analyzer = RequirementAnalyzer()
        self.clarification_engine = ClarificationEngine()

        self.goal_engine = GoalExtractionEngine()
        self.task_engine = TaskDecompositionEngine()
        self.priority_engine = PriorityAssignmentEngine()
        self.risk_engine = RiskAnalysisEngine()
        self.permission_engine = PermissionDetectionEngine()

    def process_request(self, request: PlannerRequest) -> PlannerResponse:
        """
        Main pipeline entry point.
        Returns a clarification response if incomplete, otherwise returns the JSON plan.
        """
        logger.info(
            "PlannerAgent processing request for session: %s", request.session_id
        )

        # Stage 1 & 2: User Requirement Analysis
        user_req = self.requirement_analyzer.analyze_request(request)

        # Stage 3: Clarification
        clarification = self.clarification_engine.evaluate_requirement(user_req)
        if clarification.needs_clarification:
            return PlannerResponse(
                session_id=request.session_id,
                status="clarifying",
                reply=clarification.question,
                action="await_user_input",
            )

        # Stage 4: Goal Extraction
        goal = self.goal_engine.extract_goal(user_req)

        # Stage 5: Task Decomposition
        tasks = self.task_engine.decompose(goal)

        # Stage 6: Priority Assignment
        tasks = self.priority_engine.assign_priorities(tasks)

        # Stage 7 & 8: Risk and Permissions
        risks = self.risk_engine.analyze_risks(tasks)
        permissions = self.permission_engine.detect_permissions(tasks)

        # Stage 9: Generate Planner Output Contract
        planner_output = PlannerOutput(
            workflow_spec=f"Workflow for {goal}",
            dependency_graph={},
            estimated_time_seconds=60,
            risks=risks,
            required_permissions=permissions,
            expected_outputs=[f"Completed: {goal}"],
            confidence_score=0.9,
        )

        # Serialize to JSON as per requirements
        plan_json = planner_output.model_dump_json()

        return PlannerResponse(
            session_id=request.session_id,
            status="ready",
            reply=plan_json,
            action="execute_plan",
        )
