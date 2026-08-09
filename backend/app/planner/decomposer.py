import logging
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional
from uuid import UUID

from shared.contracts.planner import TaskDecompositionPlan
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus

logger = logging.getLogger(__name__)


class TaskDecompositionEngine:
    """
    Task Decomposition Engine responsible for converting extracted goals into
    an ordered sequence of executable tasks.

    Maintains task hierarchy, dependency mapping, and topological execution ordering.
    Follows constraints:
      - Does NOT execute tasks.
      - Does NOT assign tools (required_tool remains unassigned).
      - Generates structured task plan output.
    """

    def decompose_goal(
        self,
        goal: str,
        workflow_id: UUID,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskDecompositionPlan:
        """
        Decomposes a user goal into structured hierarchical tasks.
        """
        logger.info(f"Decomposing goal for workflow {workflow_id}: '{goal}'")
        context = context or {}

        # Generate hierarchical tasks based on goal analysis
        tasks = self._generate_tasks(
            goal=goal, workflow_id=workflow_id, context=context
        )

        # Validate DAG (ensure no circular dependencies)
        self.validate_dag(tasks)

        # Build dependency graph mapping (task_id_str -> prerequisite task_id_strs)
        dep_graph_str = self.build_dependency_graph_str(tasks)

        # Build task hierarchy mapping (parent_id_str -> list of child_id_strs)
        hierarchy_str = self.build_task_hierarchy_str(tasks)

        # Generate ordered execution plan via topological sort
        ordered_tasks = self.get_ordered_execution_plan(tasks)
        execution_order = [t.task_id for t in ordered_tasks]

        total_duration = sum(
            t.estimated_duration_seconds for t in tasks if t.estimated_duration_seconds
        )

        return TaskDecompositionPlan(
            workflow_id=workflow_id,
            goal=goal,
            tasks=tasks,
            dependency_graph=dep_graph_str,
            task_hierarchy=hierarchy_str,
            execution_order=execution_order,
            estimated_total_duration_seconds=total_duration
            if total_duration > 0
            else None,
        )

    def _generate_tasks(
        self,
        goal: str,
        workflow_id: UUID,
        context: Dict[str, Any],
    ) -> List[Task]:
        """
        Decomposes the goal string into root phase tasks and atomic child tasks.
        """
        lower_goal = goal.lower()

        # Categorize goal to apply tailored decomposition template
        if any(w in lower_goal for w in ["ppt", "presentation", "slides"]):
            return self._decompose_presentation_goal(goal, workflow_id)
        elif any(
            w in lower_goal for w in ["research", "search", "investigate", "find"]
        ):
            return self._decompose_research_goal(goal, workflow_id)
        elif any(
            w in lower_goal for w in ["code", "build", "develop", "implement", "app"]
        ):
            return self._decompose_coding_goal(goal, workflow_id)
        elif any(
            w in lower_goal for w in ["system", "fix", "repair", "driver", "config"]
        ):
            return self._decompose_system_goal(goal, workflow_id)
        else:
            return self._decompose_generic_goal(goal, workflow_id)

    def _decompose_presentation_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a presentation/PPT generation goal into a task hierarchy."""
        # Phase 1: Research & Outline (Root task 1)
        phase1 = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Research & Outline",
            description="Gather topics and create outline for presentation",
            assigned_agent="PlannerAgent",
            required_tool="",
            category=TaskCategory.WEB_RESEARCH,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Topic outline and reference materials",
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        subtask_research = Task(
            parent_task_id=phase1.task_id,
            workflow_id=workflow_id,
            task_name="Collect Topic Information",
            description=f"Gather detailed facts and data for '{goal}'",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.WEB_RESEARCH,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Raw topic notes",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        subtask_outline = Task(
            parent_task_id=phase1.task_id,
            workflow_id=workflow_id,
            task_name="Draft Slide Outline",
            description="Structure content into slide titles and bullet points",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.PPT_GENERATION,
            priority=TaskPriority.MEDIUM,
            dependencies=[subtask_research.task_id],
            expected_output="Structured slide outline",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        # Phase 2: Generation & Export (Root task 2)
        phase2 = Task(
            workflow_id=workflow_id,
            task_name="Phase 2: Presentation Generation",
            description="Generate PPT slides and export deliverables",
            assigned_agent="PlannerAgent",
            required_tool="",
            category=TaskCategory.PPT_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=[phase1.task_id],
            expected_output="Final presentation file",
            estimated_duration_seconds=180,
            status=TaskStatus.CREATED,
        )

        subtask_generate_ppt = Task(
            parent_task_id=phase2.task_id,
            workflow_id=workflow_id,
            task_name="Build PPTX Deck",
            description="Create presentation slides with formatting and visuals",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.PPT_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=[subtask_outline.task_id],
            expected_output="Presentation deck (.pptx)",
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        subtask_export_pdf = Task(
            parent_task_id=phase2.task_id,
            workflow_id=workflow_id,
            task_name="Export PDF Handout",
            description="Convert PowerPoint deck to PDF format",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.PDF_GENERATION,
            priority=TaskPriority.LOW,
            dependencies=[subtask_generate_ppt.task_id],
            expected_output="PDF handout (.pdf)",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        return [
            phase1,
            subtask_research,
            subtask_outline,
            phase2,
            subtask_generate_ppt,
            subtask_export_pdf,
        ]

    def _decompose_research_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a research/information retrieval goal."""
        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Research Execution",
            description=f"Conduct research for goal: '{goal}'",
            assigned_agent="PlannerAgent",
            required_tool="",
            category=TaskCategory.WEB_RESEARCH,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Comprehensive research summary",
            estimated_duration_seconds=180,
            status=TaskStatus.CREATED,
        )

        task_search = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Execute Web Search",
            description=f"Query search engines for topics in '{goal}'",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.SEARCH,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Search result links and snippets",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        task_extract = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Extract Content Details",
            description="Browse search results and extract key findings",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.MEDIUM,
            dependencies=[task_search.task_id],
            expected_output="Extracted text and notes",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        task_synthesize = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Synthesize Research Report",
            description="Compile findings into a structured summary report",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.OTHER,
            priority=TaskPriority.MEDIUM,
            dependencies=[task_extract.task_id],
            expected_output="Summary research report",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_search, task_extract, task_synthesize]

    def _decompose_coding_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a software/coding goal into task hierarchy."""
        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Code Implementation",
            description=f"Implement software solution for: '{goal}'",
            assigned_agent="PlannerAgent",
            required_tool="",
            category=TaskCategory.CODE_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Verified software code",
            estimated_duration_seconds=300,
            status=TaskStatus.CREATED,
        )

        task_design = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Architect Code Solution",
            description="Define component structure and data interfaces",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.CODE_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Technical spec and file list",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        task_code = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Write Source Code",
            description="Generate clean source code implementing requirements",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.CODE_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=[task_design.task_id],
            expected_output="Generated source code files",
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        task_verify = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Execute Code Verification",
            description="Run unit tests and lint checks",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.PYTHON,
            priority=TaskPriority.MEDIUM,
            dependencies=[task_code.task_id],
            expected_output="Passing test execution results",
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_design, task_code, task_verify]

    def _decompose_system_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a system modification/repair goal."""
        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: System Operation",
            description=f"System operation for: '{goal}'",
            assigned_agent="PlannerAgent",
            required_tool="",
            category=TaskCategory.POWERSHELL,
            priority=TaskPriority.HIGH,
            risk_level="MEDIUM",
            dependencies=[],
            expected_output="Completed system modification",
            estimated_duration_seconds=180,
            status=TaskStatus.CREATED,
        )

        task_inspect = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Inspect System Status",
            description="Gather environment details and system status",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.POWERSHELL,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="System status logs",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        task_execute = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Execute System Modification",
            description="Apply necessary system or configuration updates",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.POWERSHELL,
            priority=TaskPriority.HIGH,
            risk_level="MEDIUM",
            dependencies=[task_inspect.task_id],
            expected_output="Modification execution output",
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_inspect, task_execute]

    def _decompose_generic_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Generic fallback goal decomposition logic."""
        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Goal Execution",
            description=f"Overall goal execution phase for: '{goal}'",
            assigned_agent="PlannerAgent",
            required_tool="",
            category=TaskCategory.OTHER,
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            expected_output="Completed goal deliverables",
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        subtask_analyze = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Analyze Requirements",
            description=f"Analyze requirements for '{goal}'",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.OTHER,
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            expected_output="Parsed task requirements",
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        subtask_run = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Execute Actions",
            description=f"Perform core actions for '{goal}'",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.OTHER,
            priority=TaskPriority.MEDIUM,
            dependencies=[subtask_analyze.task_id],
            expected_output="Action execution output",
            estimated_duration_seconds=90,
            status=TaskStatus.CREATED,
        )

        return [phase_root, subtask_analyze, subtask_run]

    def build_dependency_graph(self, tasks: List[Task]) -> Dict[UUID, List[UUID]]:
        """
        Builds a mapping from task_id to its list of prerequisite task_ids.
        """
        graph: Dict[UUID, List[UUID]] = {}
        for task in tasks:
            graph[task.task_id] = list(task.dependencies)
        return graph

    def build_dependency_graph_str(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Builds string-keyed dependency graph (task_id -> prerequisites).
        """
        graph: Dict[str, List[str]] = {}
        for task in tasks:
            graph[str(task.task_id)] = [str(dep) for dep in task.dependencies]
        return graph

    def build_task_hierarchy(
        self, tasks: List[Task]
    ) -> Dict[Optional[UUID], List[Task]]:
        """
        Groups tasks by parent_task_id.
        Key None contains root tasks.
        """
        hierarchy: Dict[Optional[UUID], List[Task]] = defaultdict(list)
        for task in tasks:
            hierarchy[task.parent_task_id].append(task)
        return dict(hierarchy)

    def build_task_hierarchy_str(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Builds string-keyed hierarchy (parent_task_id or 'root' -> child_task_ids).
        """
        hierarchy: Dict[str, List[str]] = defaultdict(list)
        for task in tasks:
            key = str(task.parent_task_id) if task.parent_task_id else "root"
            hierarchy[key].append(str(task.task_id))
        return dict(hierarchy)

    def validate_dag(self, tasks: List[Task]) -> bool:
        """
        Validates that the task graph contains no circular dependencies.
        Raises ValueError if a cycle is detected.
        """
        task_ids = {task.task_id for task in tasks}
        in_degree: Dict[UUID, int] = {t_id: 0 for t_id in task_ids}
        adj_list: Dict[UUID, List[UUID]] = defaultdict(list)

        for task in tasks:
            for dep in task.dependencies:
                if dep in task_ids:
                    adj_list[dep].append(task.task_id)
                    in_degree[task.task_id] += 1
                else:
                    logger.warning(
                        f"Task {task.task_id} specifies unknown dependency {dep}"
                    )

        # Kahn's algorithm for cycle detection
        queue = deque([t_id for t_id, count in in_degree.items() if count == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1

            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(task_ids):
            raise ValueError("Circular dependency detected in task graph")

        return True

    def get_ordered_execution_plan(self, tasks: List[Task]) -> List[Task]:
        """
        Performs a topological sort on the tasks based on their dependencies.
        Returns tasks in an ordered list satisfying prerequisite constraints.
        """
        task_map = {task.task_id: task for task in tasks}
        task_ids = set(task_map.keys())

        in_degree: Dict[UUID, int] = {t_id: 0 for t_id in task_ids}
        adj_list: Dict[UUID, List[UUID]] = defaultdict(list)

        for task in tasks:
            for dep in task.dependencies:
                if dep in task_ids:
                    adj_list[dep].append(task.task_id)
                    in_degree[task.task_id] += 1

        queue = deque([t_id for t_id, count in in_degree.items() if count == 0])
        ordered: List[Task] = []

        while queue:
            node = queue.popleft()
            ordered.append(task_map[node])

            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) != len(tasks):
            raise ValueError("Circular dependency detected during topological sort")

        return ordered
