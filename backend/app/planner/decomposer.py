import logging
import re
import urllib.parse
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional
from uuid import UUID

from shared.contracts.planner import TaskDecompositionPlan
from shared.contracts.task import (
    Task,
    TaskCategory,
    TaskPriority,
    TaskStatus,
    TaskType,
)

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
            estimated_total_duration_seconds=(
                total_duration if total_duration > 0 else None
            ),
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
        if any(
            w in lower_goal
            for w in [
                "github",
                "gitlab",
                "create issue",
                "open issue",
                "new issue",
                "pull request",
                "post issue",
                "submit issue",
            ]
        ) or ("issue" in lower_goal and ("repo" in lower_goal or "git" in lower_goal)):
            return self._decompose_github_goal(goal, workflow_id)
        elif any(
            w in lower_goal
            for w in ["ppt", "presentation", "powerpoint", "slides", "deck"]
        ):
            return self._decompose_presentation_goal(goal, workflow_id)
        elif any(
            w in lower_goal
            for w in [
                "http://",
                "https://",
                "www.",
                ".com",
                ".org",
                ".io",
                ".net",
                ".dev",
                ".ai",
                ".app",
                "youtube",
                "utube",
                "google",
                "website",
                "browser",
                "webpage",
                "navigate to",
                "open url",
                "scrape",
                "open youtube",
                "search on youtube",
                "search youtube",
                "search for",
                "search on",
                "web search",
            ]
        ):
            return self._decompose_browser_goal(goal, workflow_id)
        elif any(
            w in lower_goal
            for w in [
                "desktop automation",
                "text editor",
                "notepad",
                "gui window",
                "mouse click",
                "keyboard type",
                "type text",
                "launch app",
                "open notepad",
                "open vs code",
                "open code",
                "vscode",
                "vs code",
                "calculator",
                "calc",
            ]
        ):
            return self._decompose_desktop_goal(goal, workflow_id)
        elif re.search(
            r"\b(ipconfig|powershell|terminal|cmd|ping|netstat|whoami|hostname|systeminfo|run command|exec|shell|uptime|disk|process|memory|ram|port|ports|env)\b",
            lower_goal,
        ) or any(
            w in lower_goal
            for w in [
                "chk my ip",
                "check my ip",
                "my ip",
                "ip address",
                "ipaddress",
                "disk space",
                "free space",
                "running process",
                "process list",
                "memory usage",
                "ram usage",
                "open port",
                "listening port",
                "large file",
                "system info",
                "system uptime",
            ]
        ):
            return self._decompose_system_goal(goal, workflow_id)
        elif any(
            w in lower_goal for w in ["research", "investigate", "find info"]
        ):
            return self._decompose_research_goal(goal, workflow_id)
        elif any(
            w in lower_goal for w in ["code", "build", "develop", "implement", "app"]
        ):
            return self._decompose_coding_goal(goal, workflow_id)
        elif any(
            w in lower_goal for w in ["system", "repair", "driver", "config"]
        ):
            return self._decompose_system_goal(goal, workflow_id)
        elif any(
            w in lower_goal
            for w in [
                "ocr",
                "screenshot",
                "scanned",
                "picture",
                "read image",
                "extract text",
                "extract the text",
                "uploaded image",
                "image text",
                "visual text",
            ]
        ):
            return self._decompose_ocr_goal(goal, workflow_id)
        elif any(
            w in lower_goal
            for w in [
                "organize",
                "move",
                "copy",
                "delete",
                "folder",
                "directory",
                "downloads",
                "open folder",
                "file explorer",
            ]
        ) or ("file" in lower_goal and "create" not in lower_goal and "code" not in lower_goal):
            return self._decompose_filesystem_goal(goal, workflow_id)
        else:
            return self._decompose_generic_goal(goal, workflow_id)

    def _decompose_presentation_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a presentation/PPT generation goal into a task hierarchy."""
        # Phase 1: Research & Outline (Root task 1)
        phase1 = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Research & Outline",
            description="Gather topics and create outline for presentation",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.WEB_RESEARCH,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Topic outline and reference materials",
            artifact_location=None,
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
            artifact_location=None,
            success_criteria=["Research notes are collected and documented"],
            failure_criteria=["Unable to find information online"],
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
            artifact_location=None,
            success_criteria=["Slide titles and bullets are logically organized"],
            failure_criteria=["Missing outline structure"],
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        # Phase 2: Generation & Export (Root task 2)
        phase2 = Task(
            workflow_id=workflow_id,
            task_name="Phase 2: Presentation Generation",
            description="Generate PPT slides and export deliverables",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.PPT_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=[phase1.task_id],
            expected_output="Final presentation file",
            artifact_location=None,
            estimated_duration_seconds=180,
            status=TaskStatus.CREATED,
        )

        subtask_generate_ppt = Task(
            parent_task_id=phase2.task_id,
            workflow_id=workflow_id,
            task_name="Build PPTX Deck",
            description="Create presentation slides with formatting and visuals",
            assigned_agent="WorkerAgent",
            required_tool="ppt_tool",
            category=TaskCategory.PPT_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=[subtask_outline.task_id],
            expected_output="Presentation deck (.pptx)",
            artifact_location=None,
            success_criteria=["PPTX file is created and readable"],
            failure_criteria=["Failed to generate valid PPTX"],
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        subtask_export_pdf = Task(
            parent_task_id=phase2.task_id,
            workflow_id=workflow_id,
            task_name="Export PDF Handout",
            description="Convert PowerPoint deck to PDF format",
            assigned_agent="WorkerAgent",
            required_tool="export",
            category=TaskCategory.PDF_GENERATION,
            priority=TaskPriority.LOW,
            dependencies=[subtask_generate_ppt.task_id],
            expected_output="PDF handout (.pdf)",
            artifact_location=None,
            success_criteria=["PDF file is created"],
            failure_criteria=["PDF generation failed"],
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
            inputs={"target_format": "pdf"},
        )

        subtask_generate_ppt.artifact_location = (
            f"{workflow_id}/{subtask_generate_ppt.task_id}/presentation.pptx"
        )
        subtask_export_pdf.artifact_location = (
            f"{workflow_id}/{subtask_export_pdf.task_id}/handout.pdf"
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
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
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
            success_criteria=["Relevant URLs are found"],
            failure_criteria=["No search results returned"],
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
            success_criteria=["Text content is extracted from URLs"],
            failure_criteria=["Failed to scrape pages"],
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
            success_criteria=["A cohesive summary is generated"],
            failure_criteria=["Unable to synthesize extracted data"],
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
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
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
            success_criteria=["Architecture spec is detailed"],
            failure_criteria=["Missing design elements"],
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
            success_criteria=["Code is written and syntactically valid"],
            failure_criteria=["Syntax errors in code"],
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
            success_criteria=["Tests pass successfully"],
            failure_criteria=["Test failures encountered"],
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_design, task_code, task_verify]

    def _decompose_system_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a system command / repair goal into resolved terminal tasks."""
        from app.tools.terminal.command_resolver import CommandResolverEngine

        resolver = CommandResolverEngine()
        resolved = resolver.resolve(goal)

        phase_root = Task(
            workflow_id=workflow_id,
            task_name=f"Phase 1: System Operation ({resolved.display_name})",
            description=f"System operation for: '{goal}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.POWERSHELL,
            priority=TaskPriority.HIGH,
            risk_level=resolved.risk_level,
            dependencies=[],
            expected_output=f"Completed execution of '{resolved.command}'",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        task_inspect = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Inspect Environment Details",
            description=f"Verify shell environment for command: {resolved.command}",
            assigned_agent="WorkerAgent",
            required_tool="terminal_tool",
            category=TaskCategory.POWERSHELL,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Environment details log",
            success_criteria=["Environment details inspected"],
            failure_criteria=["Inspection failed"],
            inputs={"command": resolved.command, "raw_query": goal, "display_name": resolved.display_name},
            estimated_duration_seconds=15,
            status=TaskStatus.CREATED,
        )

        task_execute = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name=f"Execute: {resolved.command}",
            description=f"Run '{resolved.command}' ({resolved.description})",
            assigned_agent="WorkerAgent",
            required_tool="terminal_tool",
            category=TaskCategory.POWERSHELL,
            priority=TaskPriority.HIGH,
            risk_level=resolved.risk_level,
            dependencies=[task_inspect.task_id],
            expected_output=f"Output from: {resolved.command}",
            success_criteria=["Terminal command executed successfully"],
            failure_criteria=["Command execution returned non-zero exit code"],
            inputs={
                "command": resolved.command,
                "raw_query": goal,
                "display_name": resolved.display_name,
                "category": resolved.category,
                "description": resolved.description,
            },
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_inspect, task_execute]

    def _decompose_filesystem_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a file system management goal into tasks."""
        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Filesystem Management",
            description=f"Manage files and directories for: '{goal}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            expected_output="Filesystem operations completed",
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        task_inspect = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Inspect Target Directory",
            description="List and categorize existing files",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            expected_output="List of files and their metadata",
            success_criteria=["File list retrieved successfully"],
            failure_criteria=["Target directory not found or inaccessible"],
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        task_determine = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Determine Organization Strategy",
            description="Define how files should be categorized or moved",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            category=TaskCategory.OTHER,
            priority=TaskPriority.MEDIUM,
            dependencies=[task_inspect.task_id],
            expected_output="Mapping of source files to target destinations",
            success_criteria=["Strategy defines mapping for all required files"],
            failure_criteria=["Unable to determine file categories"],
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        task_execute = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Execute File Operations",
            description="Move or copy files based on the strategy",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.MEDIUM,
            dependencies=[task_determine.task_id],
            expected_output="Operations log detailing moved files",
            success_criteria=["All mapped operations succeeded"],
            failure_criteria=["One or more file operations failed"],
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_inspect, task_determine, task_execute]

    def _decompose_github_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a GitHub repository, issue creation, or PR goal into structured browser tasks."""
        lower_goal = goal.lower()

        # Handle direct submit button click follow-ups
        is_direct_submit = any(w in lower_goal for w in ["press submit", "click submit", "submit the issue", "submit new issue", "submit issue", "press the submit", "click the submit"])
        if is_direct_submit:
            phase_root = Task(
                workflow_id=workflow_id,
                task_name="Phase 1: GitHub Issue Submission",
                description=f"Submit GitHub issue form for: '{goal}'",
                task_type=TaskType.PHASE,
                assigned_agent="System",
                success_criteria=["All child leaf tasks completed successfully"],
                failure_criteria=["One or more child tasks failed"],
                required_tool="",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[],
                expected_output="GitHub issue submitted",
                estimated_duration_seconds=30,
                status=TaskStatus.CREATED,
            )

            task_submit = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name="Click 'Submit new issue' Button",
                description="Trigger submit action on active GitHub tab via browser extension",
                assigned_agent="WorkerAgent",
                required_tool="browser_extension",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[],
                expected_output="Issue submitted successfully",
                success_criteria=["Submit button clicked"],
                failure_criteria=["Submit button not found"],
                inputs={
                    "action": "interact",
                    "interaction_action": "click",
                    "selector": "button.btn-primary[type='submit'], button:has-text('Submit new issue')",
                },
                estimated_duration_seconds=15,
                status=TaskStatus.CREATED,
            )

            task_verify = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name="Verify Published Issue URL",
                description="Detect active tab URL and confirm published issue",
                assigned_agent="WorkerAgent",
                required_tool="browser_extension",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.MEDIUM,
                dependencies=[task_submit.task_id],
                expected_output="Published issue URL",
                success_criteria=["Active issue URL confirmed"],
                failure_criteria=["Navigation failed"],
                inputs={"action": "detect_active_tab"},
                estimated_duration_seconds=15,
                status=TaskStatus.CREATED,
            )
            return [phase_root, task_submit, task_verify]

        # 1. Extract repository owner/name
        repo_match = re.search(r"([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)", goal)
        if repo_match:
            repo = repo_match.group(1)
        elif "aetherphoenix" in lower_goal or "aether" in lower_goal:
            repo = "KAUSHALK123/AetherPhoenix"
        else:
            repo = "KAUSHALK123/AetherPhoenix"

        # 2. Extract title if creating an issue
        title = ""
        title_match = re.search(r"(?:titled|title|named)\s+['\"]([^'\"]+)['\"]", goal, re.IGNORECASE)
        if not title_match:
            title_match = re.search(r"(?:titled|title)\s+([^,]+?)(?:\s+with\s+description|\s+and\s+description|\s+description|\s+and\s+body|\s+with\s+body|\s+and\s+post|$)", goal, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = "New Issue Report"

        # 3. Extract description / body
        body = ""
        body_match = re.search(r"(?:description|body)\s+['\"]([^'\"]+)['\"]", goal, re.IGNORECASE)
        if not body_match:
            body_match = re.search(r"(?:with\s+description|and\s+description|description|with\s+body|and\s+body)\s+['\"]?([^'\".,]+)['\"]?", goal, re.IGNORECASE)
        if body_match:
            body = body_match.group(1).strip()
        else:
            body = f"Automated issue reported via AetherPhoenix for: {goal}"

        # 4. Construct Target URL
        is_issue = any(w in lower_goal for w in ["issue", "bug", "feature", "ticket", "post issue", "create issue", "submit issue"])
        if is_issue:
            query_params = urllib.parse.urlencode({"title": title, "body": body})
            target_url = f"https://github.com/{repo}/issues/new?{query_params}"
        elif "pull" in lower_goal or "pr" in lower_goal:
            target_url = f"https://github.com/{repo}/pulls"
        else:
            target_url = f"https://github.com/{repo}"

        phase_root = Task(
            workflow_id=workflow_id,
            task_name=f"Phase 1: GitHub Operation ({repo})",
            description=f"Automate GitHub actions for: '{goal}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output=f"GitHub operation completed on {target_url}",
            estimated_duration_seconds=120,
            status=TaskStatus.CREATED,
        )

        task_nav = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name=f"Navigate to GitHub ({repo})" + (" - New Issue Form" if is_issue else ""),
            description=f"Open active browser tab to {target_url}",
            assigned_agent="WorkerAgent",
            required_tool="browser_extension",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output=f"GitHub page loaded: {target_url}",
            success_criteria=["Page loaded successfully in browser"],
            failure_criteria=["Navigation failed or timed out"],
            inputs={
                "action": "navigate",
                "url": target_url,
                "repo": repo,
                "issue_title": title if is_issue else "",
                "issue_body": body if is_issue else "",
            },
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        tasks = [phase_root, task_nav]

        if is_issue:
            task_fill = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name=f"Populate Issue Fields ('{title}')",
                description="Fill title and markdown description on GitHub issue form",
                assigned_agent="WorkerAgent",
                required_tool="browser_extension",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[task_nav.task_id],
                expected_output="Issue form fields populated with title and description",
                success_criteria=["Title and body fields populated"],
                failure_criteria=["Form elements not found"],
                inputs={
                    "action": "interact",
                    "title_selector": "input[name='issue[title]'], #issue_title",
                    "title_value": title,
                    "body_selector": "textarea[name='issue[body]'], #issue_body",
                    "body_value": body,
                },
                estimated_duration_seconds=30,
                status=TaskStatus.CREATED,
            )

            task_submit = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name="Submit Issue & Confirm Creation",
                description="Click 'Submit new issue' button and verify issue URL in active browser",
                assigned_agent="WorkerAgent",
                required_tool="browser_extension",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[task_fill.task_id],
                expected_output="New GitHub issue created and published",
                success_criteria=["Issue submitted and created"],
                failure_criteria=["Submission button failed"],
                inputs={
                    "action": "interact",
                    "interaction_action": "click",
                    "selector": "button.btn-primary[type='submit']",
                },
                estimated_duration_seconds=30,
                status=TaskStatus.CREATED,
            )
            tasks.extend([task_fill, task_submit])

        return tasks

    def _decompose_browser_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a browser automation / navigation / search goal into tasks."""
        lower_goal = goal.lower()

        target_url = "https://www.google.com"
        site_name = "Web Browser"
        query = ""

        # 1. Direct URL detection
        url_match = re.search(
            r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.(?:com|org|io|net|edu|dev|gov|ai|app)[^\s]*)",
            goal,
        )
        if url_match:
            raw_url = url_match.group(1).rstrip(",.;!?)")
            target_url = raw_url if raw_url.startswith("http") else f"https://{raw_url}"
            site_name = target_url
        elif "youtube" in lower_goal or "utube" in lower_goal:
            site_name = "YouTube"
            target_url = "https://www.youtube.com"
            match = re.search(
                r"(?:search\s+(?:for\s+)?|query\s+|find\s+|watch\s+|lookup\s+)(.+)",
                goal,
                re.IGNORECASE,
            )
            if match:
                query = match.group(1).strip()
                query = re.sub(r"[.?!]+$", "", query).strip()
                encoded_q = urllib.parse.quote_plus(query)
                target_url = f"https://www.youtube.com/results?search_query={encoded_q}"
        elif "google" in lower_goal:
            site_name = "Google"
            target_url = "https://www.google.com"
            match = re.search(
                r"(?:search\s+(?:for\s+|google\s+for\s+)?|query\s+|find\s+|lookup\s+)(.+)",
                goal,
                re.IGNORECASE,
            )
            if match:
                query = match.group(1).strip()
                query = re.sub(r"[.?!]+$", "", query).strip()
                encoded_q = urllib.parse.quote_plus(query)
                target_url = f"https://www.google.com/search?q={encoded_q}"
        elif "navigate to" in lower_goal or "open" in lower_goal or "go to" in lower_goal:
            nav_match = re.search(
                r"(?:navigate\s+to|go\s+to|open\s+browser\s+and\s+navigate\s+to|open\s+browser\s+and\s+go\s+to|open)\s+(.+)",
                goal,
                re.IGNORECASE,
            )
            if nav_match:
                dest = nav_match.group(1).strip()
                dest = re.sub(r"[.?!]+$", "", dest).strip()
                dest_clean = re.sub(
                    r"^(?:browser\s+and\s+navigate\s+to\s+|browser\s+and\s+go\s+to\s+|browser\s+to\s+|browser\s+and\s+open\s+|browser\s+)",
                    "",
                    dest,
                    flags=re.IGNORECASE,
                ).strip()
                query = dest_clean
                encoded_q = urllib.parse.quote_plus(dest_clean)
                target_url = f"https://www.google.com/search?q={encoded_q}"
                site_name = dest_clean.title()
        else:
            match = re.search(
                r"(?:search\s+(?:for\s+)?|query\s+|find\s+|lookup\s+)(.+)",
                goal,
                re.IGNORECASE,
            )
            if match:
                query = match.group(1).strip()
                query = re.sub(r"[.?!]+$", "", query).strip()
                encoded_q = urllib.parse.quote_plus(query)
                target_url = f"https://www.google.com/search?q={encoded_q}"
                site_name = "Web Search"

        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Browser Automation & Interaction",
            description=f"Automate browser actions for: '{goal}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output=f"Navigated to {site_name} and executed requested search",
            estimated_duration_seconds=90,
            status=TaskStatus.CREATED,
        )

        task_nav = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name=(
                f"Navigate to {site_name}"
                + (f" and Search for '{query}'" if query else "")
            ),
            description=f"Open active browser window and navigate to {target_url}",
            assigned_agent="WorkerAgent",
            required_tool="browser_extension",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output=f"Browser tab opened and navigated to {target_url}",
            success_criteria=["Page loaded successfully in browser"],
            failure_criteria=["Navigation failed or timed out"],
            inputs={"action": "navigate", "url": target_url},
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        task_extract = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Verify & Extract Search Results",
            description=f"Inspect page content and verify results for '{query or goal}'",
            assigned_agent="WorkerAgent",
            required_tool="browser_extension",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.MEDIUM,
            dependencies=[task_nav.task_id],
            expected_output="Extracted search results list",
            success_criteria=["Results extracted from active page"],
            failure_criteria=["Failed to extract content"],
            inputs={"action": "extract_content", "include_html": False},
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_nav, task_extract]

    def _decompose_desktop_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a desktop application launch or GUI automation goal."""
        lower_goal = goal.lower()
        app_name = "Application"
        if (
            "vs code" in lower_goal
            or "vscode" in lower_goal
            or "open code" in lower_goal
        ):
            app_name = "Visual Studio Code"
        elif "notepad" in lower_goal:
            app_name = "Notepad"
        elif "calc" in lower_goal:
            app_name = "Calculator"

        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Desktop Application Control",
            description=f"Launch and interact with {app_name}",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.DESKTOP,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output=f"{app_name} launched and active on desktop",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        task_launch = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name=f"Launch {app_name}",
            description=f"Open {app_name} process on the host operating system",
            assigned_agent="WorkerAgent",
            required_tool="desktop_automation",
            category=TaskCategory.DESKTOP,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output=f"{app_name} launched with active PID",
            success_criteria=[f"{app_name} process is running"],
            failure_criteria=[f"Failed to launch {app_name}"],
            inputs={"app_name": app_name},
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_launch]

    def _decompose_ocr_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes an OCR / text extraction from image goal."""
        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Visual Text Extraction (OCR)",
            description=f"Extract readable text from image for: '{goal}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.OCR,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Extracted text transcript",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        task_ocr = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Perform OCR Extraction",
            description="Process image and extract visual textual content",
            assigned_agent="WorkerAgent",
            required_tool="ocr",
            category=TaskCategory.OCR,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Plaintext extracted from image",
            success_criteria=["Text extracted with high confidence"],
            failure_criteria=["Unable to detect readable text in image"],
            inputs={"image_path": "uploaded_image.png"},
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_ocr]

    def _decompose_generic_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Generic fallback goal decomposition logic."""
        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Goal Execution",
            description=f"Overall goal execution phase for: '{goal}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
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
            task_name="Evaluate Goal Context",
            description=f"Review context and requirements for '{goal}'",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.OTHER,
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            expected_output="Contextual analysis document",
            success_criteria=["Context accurately captured"],
            failure_criteria=["Insufficient context available"],
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        subtask_run = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Execute Primary Action",
            description=f"Perform the core operation for '{goal}'",
            assigned_agent="WorkerAgent",
            required_tool="",
            category=TaskCategory.OTHER,
            priority=TaskPriority.MEDIUM,
            dependencies=[subtask_analyze.task_id],
            expected_output="Operation results",
            success_criteria=["Operation completes and satisfies goal"],
            failure_criteria=["Operation fails or returns errors"],
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

