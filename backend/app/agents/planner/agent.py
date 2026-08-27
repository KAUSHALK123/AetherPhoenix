import logging
from typing import Any, Dict, Optional

from shared.contracts.feedback import PlannerFeedback
from shared.contracts.planner import (
    PlanMetadata,
    PlannerOutput,
    PlannerRequest,
    PlannerResponse,
)

from app.agents.planner.capability_engine import CapabilityDiscoveryEngine
from app.agents.planner.parallel_engine import ParallelTaskAnalyzer
from app.agents.planner.permission_engine import PermissionDetectionEngine
from app.agents.planner.priority_engine import PriorityAssignmentEngine
from app.agents.planner.risk_analysis import RiskAnalysisEngine
from app.planner.analyzer import RequirementAnalyzer
from app.planner.clarifier import ClarificationEngine
from app.planner.decomposer import TaskDecompositionEngine
from app.planner.goal_engine import GoalExtractionEngine

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    End-to-End Orchestrator for the Planning Pipeline.
    Integrates modules from Sprint 2 to transform user requests into execution plans.
    """

    def __init__(self, event_bus: Optional[Any] = None):
        self.requirement_analyzer = RequirementAnalyzer()
        self.clarification_engine = ClarificationEngine()

        self.goal_engine = GoalExtractionEngine()
        self.task_engine = TaskDecompositionEngine()
        self.priority_engine = PriorityAssignmentEngine()
        self.risk_engine = RiskAnalysisEngine()
        self.permission_engine = PermissionDetectionEngine()
        self.permission_engine = PermissionDetectionEngine()

        # Initialize CapabilityRegistry with mock defaults for Planner V1 testing
        from shared.contracts.capability import Capability
        from shared.contracts.task import TaskCategory

        from app.engine.registry import CapabilityRegistry

        cap_reg = CapabilityRegistry()
        cap_reg.register(
            Capability(
                name="file_explorer",
                description=(
                    "Interacts with OS File Explorer to open folders/files, "
                    "reveal artifacts, create directories, detect existence, "
                    "and retrieve metadata."
                ),
                category=TaskCategory.FILE_SYSTEM,
                required_tools=["file_explorer"],
            )
        )
        cap_reg.register(
            Capability(
                name="local_file_manager",
                description="Manages local files and folders",
                category=TaskCategory.FILE_SYSTEM,
                required_tools=["file_manager_tool"],
            )
        )
        cap_reg.register(
            Capability(
                name="web_searcher",
                description="Searches the web for information",
                category=TaskCategory.WEB_RESEARCH,
                required_tools=["web_search_tool"],
            )
        )
        cap_reg.register(
            Capability(
                name="content_generator",
                description="Generates content like presentations and reports",
                category=TaskCategory.OTHER,
                required_tools=["content_tool"],
            )
        )
        cap_reg.register(
            Capability(
                name="ppt_generator",
                description="Generates PPT presentations",
                category=TaskCategory.PPT_GENERATION,
                required_tools=["ppt_tool"],
            )
        )
        cap_reg.register(
            Capability(
                name="pdf_generator",
                description="Generates PDF presentations",
                category=TaskCategory.PDF_GENERATION,
                required_tools=["pdf_tool"],
            )
        )
        cap_reg.register(
            Capability(
                name="powershell_executor",
                description="Executes powershell commands",
                category=TaskCategory.POWERSHELL,
                required_tools=["powershell"],
            )
        )
        cap_reg.register(
            Capability(
                name="code_generator",
                description="Generates code",
                category=TaskCategory.CODE_GENERATION,
                required_tools=["coder"],
            )
        )
        cap_reg.register(
            Capability(
                name="browser_automation",
                description="Controls web browser navigation, interaction and scraping",
                category=TaskCategory.BROWSER,
                required_tools=["browser_automation"],
            )
        )
        cap_reg.register(
            Capability(
                name="desktop_automation",
                description=(
                    "Controls desktop applications, mouse, keyboard, and windows"
                ),
                category=TaskCategory.DESKTOP,
                required_tools=["desktop_automation"],
            )
        )

        self.capability_engine = CapabilityDiscoveryEngine(registry=cap_reg)
        self.parallel_engine = ParallelTaskAnalyzer()
        self.active_sessions: dict[str, str] = {}
        self.latest_replanning_responses: Dict[str, PlannerResponse] = {}

        # Subscribe to EventBus replanning events
        from app.core.events.bus import get_event_bus
        from app.core.events.models import EventType as ModelEventType

        self.event_bus = event_bus or get_event_bus()
        if self.event_bus:
            self.event_bus.subscribe(
                ModelEventType.REPLANNING_TRIGGERED,
                self.handle_replanning_event,
            )
            self.event_bus.subscribe(
                "ReplanningTriggered",
                self.handle_replanning_event,
            )
            self.event_bus.subscribe(
                "REPLANNING_TRIGGERED",
                self.handle_replanning_event,
            )

    async def handle_replanning_event(self, event: Any) -> Optional[PlannerResponse]:
        """
        Handles REPLANNING_TRIGGERED events from the EventBus,
        reconstructs planning context and generates an updated plan.
        """
        logger.info(
            "PlannerAgent received REPLANNING_TRIGGERED event: %s",
            getattr(event, "id", event),
        )
        payload = getattr(event, "payload", {}) or {}
        workflow_id = getattr(event, "workflow_id", None) or payload.get("workflow_id")
        session_id = payload.get("session_id") or (
            str(workflow_id) if workflow_id else "replanning-session"
        )
        goal = (
            payload.get("goal")
            or payload.get("trigger_reason")
            or "Replanning execution"
        )

        feedback_data = payload.get("feedback")
        feedback = None
        if feedback_data and isinstance(feedback_data, dict):
            try:
                feedback = PlannerFeedback.model_validate(feedback_data)
            except Exception as e:
                logger.warning(f"Failed to parse feedback in replanning event: {e}")

        # Build conversation context if session exists
        from app.planner.session import get_session_manager

        session = get_session_manager().get_session(session_id)
        conversation_history = session.get_history_dicts() if session else []

        request = PlannerRequest(
            session_id=session_id,
            message=goal,
            context={
                "workflow_id": str(workflow_id) if workflow_id else None,
                "conversation_history": conversation_history,
                "is_replanning": True,
                "trigger_reason": payload.get("trigger_reason"),
            },
            feedback=feedback,
        )

        response = self.process_request(request)
        logger.info(
            "PlannerAgent successfully generated replanning response: status=%s",
            response.status,
        )

        if workflow_id:
            self.latest_replanning_responses[str(workflow_id)] = response

        return response

    def process_request(self, request: PlannerRequest) -> PlannerResponse:
        """
        Main pipeline entry point.
        Returns a clarification response if incomplete, otherwise returns the JSON plan.
        """
        logger.info(
            "PlannerAgent processing request for session: %s", request.session_id
        )

        # Check for circular feedback loops
        if request.feedback and request.feedback.replanning_context:
            session_id = request.session_id
            if not hasattr(self, "replanning_cycles"):
                self.replanning_cycles = {}
            cycles = self.replanning_cycles.get(session_id, 0)
            if cycles >= 3:
                logger.error(
                    "Circular planning loop detected for session %s. Terminating.",
                    session_id,
                )
                self.replanning_cycles.pop(session_id, None)
                self.active_sessions.pop(session_id, None)
                return PlannerResponse(
                    session_id=session_id,
                    status="error",
                    reply=(
                        "Circular planning loop detected. "
                        "Execution fails repeatedly without recovery."
                    ),
                    action="terminate",
                )
            self.replanning_cycles[session_id] = cycles + 1

        # Extract unavailable tools from feedback
        unavailable_tools = []
        if request.feedback:
            if (
                request.feedback.capability_failure
                and request.feedback.capability_failure.is_permanent
            ):
                unavailable_tools.append(request.feedback.capability_failure.tool_name)
            if request.feedback.failure_summary:
                if (
                    request.feedback.healing_summary
                    and request.feedback.healing_summary.outcome == "UNRECOVERABLE"
                ):
                    unavailable_tools.append(request.feedback.failure_summary.tool_used)

        # Restore session context if this is a clarification answer
        if request.session_id in self.active_sessions:
            original_goal = self.active_sessions[request.session_id]
            # Combine original goal with clarification answer
            combined_message = f"{original_goal} (Clarification provided: {request.message})"  # noqa: E501
            request.message = combined_message
        else:
            combined_message = request.message

        # Stage 1 & 2: User Requirement Analysis
        user_req = self.requirement_analyzer.analyze_request(request)

        # Stage 3: Clarification
        clarification = self.clarification_engine.evaluate_requirement(user_req)
        if clarification.needs_clarification:
            self.active_sessions[request.session_id] = combined_message
            return PlannerResponse(
                session_id=request.session_id,
                status="clarifying",
                reply=clarification.question,
                action="await_user_input",
            )

        # Stage 4: Goal Extraction
        goal_result = self.goal_engine.extract_goals(request)
        if not goal_result.primary_goal:
            # Fallback if validation totally fails
            self.active_sessions.pop(request.session_id, None)
            return PlannerResponse(
                session_id=request.session_id,
                status="error",
                reply="Could not extract a valid goal from the request.",
                action="await_user_input",
            )

        if goal_result.confidence_score < 0.6:
            self.active_sessions[request.session_id] = combined_message
            return PlannerResponse(
                session_id=request.session_id,
                status="clarifying",
                reply="Your request is a bit too vague. Could you provide more specific details?",  # noqa: E501
                action="await_user_input",
            )

        goal_title = goal_result.primary_goal.title

        # Stage 5: Task Decomposition
        # workflow_id will be derived from session_id if possible, or we can just parse it  # noqa: E501
        import uuid

        try:
            workflow_id = uuid.UUID(request.session_id)
        except ValueError:
            workflow_id = uuid.uuid4()

        decomposition_plan = self.task_engine.decompose_goal(
            goal=goal_title,
            workflow_id=workflow_id,
            context=request.context,
        )
        tasks = decomposition_plan.tasks

        # Capability Discovery
        tasks, unsupported_caps = self.capability_engine.discover_capabilities(
            tasks, unavailable_tools=unavailable_tools
        )
        if unsupported_caps:
            decomposition_plan.unsupported_capabilities = unsupported_caps
            self.active_sessions.pop(request.session_id, None)
            return PlannerResponse(
                session_id=request.session_id,
                status="error",
                reply=(
                    f"Unsupported capabilities detected: "
                    f"{', '.join(unsupported_caps)}. Cannot execute this goal."
                ),
                action="await_user_input",
            )

        # Stage 6: Priority Assignment
        tasks = self.priority_engine.assign_priorities(tasks)

        # Stage 7 & 8: Risk and Permissions
        # Need to detect permissions first to update task risk levels appropriately
        tasks, permission_requests = self.permission_engine.detect_permissions(tasks)
        risk_result = self.risk_engine.analyze_tasks(tasks)

        # Parallel Task Analysis
        # We need to pass the dependency graph formatted with UUIDs, but decomposition_plan  # noqa: E501
        # stores it as string -> list[str]. Let's parse it back.
        import uuid

        parsed_dep_graph = {}
        for k, v in decomposition_plan.dependency_graph.items():
            parsed_dep_graph[uuid.UUID(k)] = [uuid.UUID(dep) for dep in v]

        parallel_groups = self.parallel_engine.analyze_parallel_groups(
            tasks, parsed_dep_graph
        )

        dedup = set([p.permission_type.value for p in permission_requests])
        deduplicated_permissions = list(dedup)

        # Compute dynamic confidence score
        from shared.contracts.task import TaskType

        total_leaf_tasks = sum(1 for t in tasks if t.task_type == TaskType.LEAF)
        resolved_tools = sum(
            1 for t in tasks if t.task_type == TaskType.LEAF and t.required_tool
        )

        plan_confidence = goal_result.confidence_score

        # Tool Resolution Penalty
        if total_leaf_tasks > 0:
            tool_resolution_ratio = resolved_tools / total_leaf_tasks
            if tool_resolution_ratio < 1.0:
                plan_confidence -= 0.2 * (1.0 - tool_resolution_ratio)

        # Clarification Bonus
        if "Clarification provided:" in combined_message:
            plan_confidence += 0.1

        # Invalid Dependencies Penalty
        task_ids = {t.task_id for t in tasks}
        invalid_deps = sum(
            1 for t in tasks for dep in t.dependencies if dep not in task_ids
        )
        if invalid_deps > 0:
            plan_confidence -= 0.2

        final_confidence = min(1.0, max(0.0, round(plan_confidence, 2)))

        # Generate Execution Summary
        perms_str = (
            ", ".join(deduplicated_permissions) if deduplicated_permissions else "None"
        )
        dur = decomposition_plan.estimated_total_duration_seconds or 60
        execution_summary = (
            f"**Execution Plan Summary**\n"
            f"- **Goal**: {goal_title}\n"
            f"- **Total Tasks**: {len(tasks)}\n"
            f"- **Estimated Duration**: {dur} seconds\n"
            f"- **Overall Risk**: {risk_result.overall_risk_level.value}\n"
            f"- **Required Permissions**: {perms_str}\n"
            f"- **Parallel Execution**: {len(parallel_groups)} execution phases identified.\n"  # noqa: E501
            f"- **Overall Confidence**: {final_confidence * 100:.1f}%\n"
        )

        # Stage 9: Generate Planner Output Contract
        planner_output = PlannerOutput(
            metadata=PlanMetadata(
                workflow_id=str(workflow_id),
                session_id=request.session_id,
                goal=goal_title,
            ),
            workflow_spec=f"Workflow for {goal_title}",
            tasks=tasks,
            dependency_graph=parsed_dep_graph,
            estimated_time_seconds=decomposition_plan.estimated_total_duration_seconds
            or 60,
            risks=[
                a.reasoning
                for a in risk_result.assessments
                if a.risk_level.value != "SAFE"
            ],
            required_permissions=deduplicated_permissions,
            expected_outputs=goal_result.primary_goal.expected_outcomes,
            confidence_score=final_confidence,
            execution_summary=execution_summary,
            parallel_groups=parallel_groups,
        )

        # Serialize to JSON as per requirements
        plan_json = planner_output.model_dump_json()

        self.active_sessions.pop(request.session_id, None)

        return PlannerResponse(
            session_id=request.session_id,
            status="ready",
            reply=plan_json,
            action="execute_plan",
        )
