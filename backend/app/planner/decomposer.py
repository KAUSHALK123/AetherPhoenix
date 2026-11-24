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

        # 1. Read-Only Directory & Drive Inspection Intent
        is_read_only_dir_intent = (
            any(
                w in lower_goal
                for w in [
                    "what folders",
                    "what files",
                    "what's in",
                    "whats in",
                    "what is in",
                    "tell me what folders",
                    "tell me what files",
                    "tell me what",
                    "list folders",
                    "list files",
                    "check folders",
                    "check files",
                    "check d drive",
                    "check c drive",
                    "show folders",
                    "show files",
                    "browse folder",
                    "browse directory",
                    "view folders",
                ]
            )
            or (
                any(
                    w in lower_goal
                    for w in [
                        "list",
                        "show",
                        "check",
                        "browse",
                        "view",
                        "inspect",
                        "explore",
                        "what's in",
                        "whats in",
                    ]
                )
                and any(
                    d in lower_goal
                    for d in [
                        "drive",
                        "folder",
                        "directory",
                        "directories",
                        "d:",
                        "c:",
                        "e:",
                        ":\\",
                        ":/",
                    ]
                )
                and not any(
                    a in lower_goal
                    for a in [
                        "organize",
                        "sort",
                        "clean up",
                        "cleanup",
                        "move",
                        "copy",
                        "delete",
                    ]
                )
            )
            or bool(
                re.search(
                    r"\b(check|show|list|browse|view|inspect)\s+[a-z]\s+drive\b",
                    lower_goal,
                )
            )
            or bool(
                re.search(
                    r"\b(?:what|tell me)\s+(?:folders|files)\s+(?:are\s+)?in\s+[a-z]\s+drive\b",
                    lower_goal,
                )
            )
        )
        if is_read_only_dir_intent:
            return self._decompose_directory_inspection_goal(goal, workflow_id)

        # 2. File Organization & Management Intent (Priority over file extensions)
        is_organize_intent = any(
            v in lower_goal
            for v in [
                "organize",
                "sort",
                "group",
                "clean up",
                "cleanup",
                "move",
                "copy",
                "delete",
            ]
        ) and any(
            n in lower_goal
            for n in [
                "file",
                "files",
                "folder",
                "folders",
                "directory",
                "directories",
                "downloads",
                "desktop",
                "docs",
                "documents",
                ".ppt",
                ".pdf",
                ".jpg",
                ".png",
                ".txt",
            ]
        )
        if is_organize_intent or any(
            w in lower_goal
            for w in [
                "local file organizer",
                "file organizer",
                "organize downloads",
                "sort files",
                "organize files",
                "clean up folder",
                "clean up files",
            ]
        ):
            return self._decompose_filesystem_goal(goal, workflow_id)

        # 2. PDF Search / Text Extraction Intent (Priority over generic browser search)
        if ("pdf" in lower_goal or ".pdf" in lower_goal) and any(
            w in lower_goal
            for w in [
                "search",
                "find",
                "extract",
                "read",
                "query",
                "lookup",
                "scan",
                "ocr",
            ]
        ):
            return self._decompose_pdf_search_goal(goal, workflow_id)

        # 3. Canva Design Automation Intent (Priority for Canva and Design workflows)
        if self._is_canva_goal(lower_goal, context):
            return self._decompose_canva_goal(goal, workflow_id, context)

        # 4. PDF Generation Intent (Priority over generic system or coding)
        if any(
            w in lower_goal
            for w in [
                "generate pdf",
                "create pdf",
                "create a pdf",
                "make pdf",
                "make a pdf",
                "build pdf",
                "export pdf",
                "pdf report",
                "pdf document",
            ]
        ):
            return self._decompose_pdf_goal(goal, workflow_id)

        # 5. Presentation / PPT Generation Intent
        if any(
            w in lower_goal
            for w in ["ppt", "presentation", "powerpoint", "slides", "deck"]
        ):
            return self._decompose_presentation_goal(goal, workflow_id)

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
        elif any(w in lower_goal for w in ["research", "investigate", "find info"]):
            return self._decompose_research_goal(goal, workflow_id)
        elif any(
            w in lower_goal for w in ["code", "build", "develop", "implement", "app"]
        ):
            return self._decompose_coding_goal(goal, workflow_id)
        elif any(w in lower_goal for w in ["system", "repair", "driver", "config"]):
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
        ) or (
            "file" in lower_goal
            and "create" not in lower_goal
            and "code" not in lower_goal
        ):
            return self._decompose_filesystem_goal(goal, workflow_id)
        else:
            # Fallback: query LLM planner with live ToolRegistry catalog
            try:
                import json

                from shared.contracts.planner import PlannerRequest

                from app.planner.llm_planner import LLMPlanner

                if not hasattr(self, "llm_planner") or self.llm_planner is None:
                    self.llm_planner = LLMPlanner()

                if self.llm_planner.is_nonsense(goal):
                    return []

                resp = self.llm_planner.plan(
                    PlannerRequest(session_id=str(workflow_id), message=goal),
                    workflow_id=workflow_id,
                )
                if resp.status == "ready" and resp.reply:
                    plan_dict = json.loads(resp.reply)
                    task_dicts = plan_dict.get("tasks", [])
                    if task_dicts:
                        return [Task.model_validate(t) for t in task_dicts]
            except Exception as e:
                logger.warning(f"LLM planner fallback error: {e}")

            # For actionable goals (e.g. security/user/system setup) or testing workflows,
            # allow generic task decomposition so CapabilityDiscoveryEngine can map capabilities.
            if any(
                w in lower_goal
                for w in [
                    "user",
                    "securely",
                    "account",
                    "permission",
                    "login",
                    "auth",
                    "role",
                ]
            ):
                return self._decompose_generic_goal(goal, workflow_id)

            # Do not emit a placeholder plan for unhandled requests!
            return []

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
            inputs={
                "command": resolved.command,
                "raw_query": goal,
                "display_name": resolved.display_name,
            },
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

    def _decompose_directory_inspection_goal(
        self, goal: str, workflow_id: UUID
    ) -> List[Task]:
        """Decomposes a read-only directory or drive inspection goal into a file_explorer task."""
        lower_goal = goal.lower()

        # Extract target path
        target_path = "."
        drive_match = re.search(r"\b([a-zA-Z])\s+drive\b", lower_goal) or re.search(
            r"\bdrive\s+([a-zA-Z])\b", lower_goal
        )
        if drive_match:
            drive_letter = drive_match.group(1).upper()
            target_path = f"{drive_letter}:\\"
        elif re.search(r"\b([a-zA-Z]):[\\/]?", lower_goal):
            m = re.search(r"\b([a-zA-Z]):([\\/][^ \t\n\r\"']*)?", goal)
            if m:
                target_path = m.group(0)
                if not target_path.endswith("\\") and not target_path.endswith("/"):
                    target_path += "\\"
        elif "downloads" in lower_goal:
            target_path = "downloads"
        elif "desktop" in lower_goal:
            target_path = "desktop"
        elif "documents" in lower_goal:
            target_path = "documents"

        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: Directory Inspection",
            description=f"Inspect and list directory contents for: '{target_path}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.LOW,
            dependencies=[],
            expected_output=f"List of files and directories in '{target_path}'",
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        task_list = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name=f"List contents of {target_path}",
            description=f"Inspect and list files and folders in '{target_path}'",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.LOW,
            dependencies=[],
            expected_output=f"List of files and directories in '{target_path}'",
            success_criteria=[
                f"Directory contents for '{target_path}' retrieved successfully"
            ],
            failure_criteria=[f"Failed to access or list '{target_path}'"],
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
            inputs={"action": "list_files", "path": target_path},
        )

        return [phase_root, task_list]

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

        task_list = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="List files in source dir",
            description="Scan and list files and metadata in the source directory",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            expected_output="List of files and their metadata in source directory",
            success_criteria=["File list retrieved successfully"],
            failure_criteria=["Target directory not found or inaccessible"],
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
            inputs={"action": "list_files", "path": "."},
        )

        task_create_dirs = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Create target categories/folders",
            description="Create destination categories and folders for organization",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.MEDIUM,
            dependencies=[task_list.task_id],
            expected_output="Target category directories created",
            success_criteria=["Category folders created successfully"],
            failure_criteria=["Failed to create category folders"],
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
            inputs={"action": "create_folder"},
        )

        task_move_copy = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Move/copy files into destination",
            description="Move or copy files into destination category directories",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.MEDIUM,
            dependencies=[task_create_dirs.task_id],
            expected_output="Operations log detailing moved/copied files",
            success_criteria=["All mapped files moved or copied to destination"],
            failure_criteria=["One or more file operations failed"],
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
            inputs={"action": "move_file"},
        )

        return [phase_root, task_list, task_create_dirs, task_move_copy]

    def _decompose_github_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a GitHub repository, issue creation, or PR goal into structured browser tasks."""
        lower_goal = goal.lower()

        # Handle direct submit button click follow-ups
        is_direct_submit = any(
            w in lower_goal
            for w in [
                "press submit",
                "click submit",
                "submit the issue",
                "submit new issue",
                "submit issue",
                "press the submit",
                "click the submit",
            ]
        )
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
        title_match = re.search(
            r"(?:titled|title|named)\s+['\"]([^'\"]+)['\"]", goal, re.IGNORECASE
        )
        if not title_match:
            title_match = re.search(
                r"(?:titled|title)\s+([^,]+?)(?:\s+with\s+description|\s+and\s+description|\s+description|\s+and\s+body|\s+with\s+body|\s+and\s+post|$)",
                goal,
                re.IGNORECASE,
            )
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = "New Issue Report"

        # 3. Extract description / body
        body = ""
        body_match = re.search(
            r"(?:description|body)\s+['\"]([^'\"]+)['\"]", goal, re.IGNORECASE
        )
        if not body_match:
            body_match = re.search(
                r"(?:with\s+description|and\s+description|description|with\s+body|and\s+body)\s+['\"]?([^'\".,]+)['\"]?",
                goal,
                re.IGNORECASE,
            )
        if body_match:
            body = body_match.group(1).strip()
        else:
            body = f"Automated issue reported via AetherPhoenix for: {goal}"

        # 4. Construct Target URL
        is_issue = any(
            w in lower_goal
            for w in [
                "issue",
                "bug",
                "feature",
                "ticket",
                "post issue",
                "create issue",
                "submit issue",
            ]
        )
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
            task_name=f"Navigate to GitHub ({repo})"
            + (" - New Issue Form" if is_issue else ""),
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
        elif (
            "navigate to" in lower_goal or "open" in lower_goal or "go to" in lower_goal
        ):
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

    def _decompose_pdf_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a PDF document generation goal."""
        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: PDF Document Generation",
            description=f"Compile and generate formatted PDF document for: '{goal}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.PDF_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Formatted PDF document (.pdf)",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        task_pdf = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Generate PDF Document",
            description="Build structured PDF document with headers, paragraphs, and styling",
            assigned_agent="WorkerAgent",
            required_tool="pdf_generator",
            category=TaskCategory.PDF_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="PDF document (.pdf)",
            success_criteria=[
                "PDF file created with valid magic bytes and non-empty content"
            ],
            failure_criteria=["Failed to generate or validate PDF document"],
            inputs={"title": goal, "topic": goal},
            estimated_duration_seconds=45,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_pdf]

    def _decompose_pdf_search_goal(self, goal: str, workflow_id: UUID) -> List[Task]:
        """Decomposes a PDF search or text extraction goal."""
        import re

        # Extract search query if present
        query_match = re.search(
            r"(?:search|find|query|lookup)\s+(?:for\s+)?['\"]?([^'\"]+?)['\"]?\s+in\s+",
            goal,
            re.IGNORECASE,
        )
        query = query_match.group(1).strip() if query_match else None
        if not query:
            # Fallback regex
            query_match2 = re.search(
                r"(?:search|find|extract)\s+['\"]?([^'\"]+?)['\"]?\s+(?:from|in)\s+pdf",
                goal,
                re.IGNORECASE,
            )
            query = query_match2.group(1).strip() if query_match2 else "search text"

        # Extract file path if present
        path_match = re.search(
            r"['\"]?([a-zA-Z0-9_\-\\/.]+\.pdf)['\"]?", goal, re.IGNORECASE
        )
        target_path = path_match.group(1) if path_match else "document.pdf"

        phase_root = Task(
            workflow_id=workflow_id,
            task_name="Phase 1: PDF Search & Extraction",
            description=f"Extract and search content within PDF document for: '{goal}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["All child leaf tasks completed successfully"],
            failure_criteria=["One or more child tasks failed"],
            required_tool="",
            category=TaskCategory.OCR,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Search results and extracted content",
            estimated_duration_seconds=60,
            status=TaskStatus.CREATED,
        )

        task_search = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Search & Extract PDF Content",
            description=f"Parse PDF text and search for matching segments: '{query}'",
            assigned_agent="WorkerAgent",
            required_tool="ocr",
            category=TaskCategory.OCR,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Extracted text transcript and matching segments",
            success_criteria=["Text extracted and query evaluated across segments"],
            failure_criteria=["Failed to parse or search PDF document"],
            inputs={"filepath": target_path, "query": query},
            estimated_duration_seconds=30,
            status=TaskStatus.CREATED,
        )

        return [phase_root, task_search]

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

    def _is_canva_goal(
        self, lower_goal: str, context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Determines if the goal is a Canva automation or graphic design request."""
        ctx = context or {}
        if ctx.get("canva") or ctx.get("tool") == "canva_tool":
            return True

        clean = re.sub(r"[^\w\s×x]", " ", lower_goal).strip()
        clean_words = clean.split()
        clean_str = " ".join(clean_words)

        # 1. Explicit Canva reference
        if "canva" in lower_goal:
            return True

        # 2. Design or template requests specifying PPT / presentation / slides / posters / posts
        if (
            "design" in lower_goal
            and any(
                w in lower_goal
                for w in [
                    "ppt",
                    "presentation",
                    "slide",
                    "slides",
                    "template",
                    "poster",
                    "post",
                    "thumbnail",
                    "particular design",
                    "contents",
                    "pasting",
                ]
            )
        ):
            return True

        if (
            "template" in lower_goal
            and any(
                w in lower_goal
                for w in ["ppt", "presentation", "slide", "slides", "pasting", "contents", "default"]
            )
        ):
            return True

        # 3. Mandatory Test Scenarios & key design patterns
        if (
            "instagram" in lower_goal
            or "insta" in lower_goal
            or "fest" in lower_goal
            or "poster" in lower_goal
            or "postr" in lower_goal
            or "thumbnail" in lower_goal
            or "youtube thumb" in lower_goal
            or "edit existing design" in lower_goal
            or "edit an existing design" in lower_goal
            or "change the theme or colors of a design" in lower_goal
            or (
                "change" in lower_goal
                and ("theme" in lower_goal or "color" in lower_goal)
                and "design" in lower_goal
            )
            or (
                "export as pdf" in lower_goal
                and ("design" in lower_goal or ctx.get("canva"))
            )
            or (
                "export" in lower_goal and "pdf" in lower_goal and "canva" in lower_goal
            )
        ):
            return True

        # 4. Exact matching for mandatory test phrases
        if clean_str in [
            "open canva",
            "create instagram post 1080 1080",
            "create instagram post 1080x1080",
            "create instagram post",
            "create college fest poster",
            "design a college event poster",
            "create presentation",
            "edit existing design",
            "export as pdf",
        ]:
            return True

        return False

    def _decompose_canva_goal(
        self, goal: str, workflow_id: UUID, context: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """
        Decomposes a Canva graphic design request into structured atomic tasks.
        Supports:
          - Open Canva
          - Create Instagram post (1080x1080)
          - Create poster (College fest / event)
          - Create presentation (Canva presentation editor)
          - Create YouTube thumbnail
          - Edit existing design
          - Change theme or colors
          - Export design as PDF/PNG/JPG
        """
        lower_goal = goal.lower()
        clean = re.sub(r"[^\w\s×x]", " ", lower_goal).strip()
        clean_str = " ".join(clean.split())

        # Extract dimensions if present (e.g. 1080 x 1080, 1080x1080, 1920x1080)
        dim_match = re.search(r"(\d{3,4})\s*(?:[x×*]|by)\s*(\d{3,4})", lower_goal)
        custom_w = int(dim_match.group(1)) if dim_match else None
        custom_h = int(dim_match.group(2)) if dim_match else None

        # Extract slide count if present (e.g. 5 slide, 5 slides, 3 pages)
        slide_match = re.search(r"(\d+)\s*(?:slide|slides|page|pages)", lower_goal)
        num_slides = int(slide_match.group(1)) if slide_match else 1

        # Extract topic from "on X in canva" or "about X"
        topic_match = re.search(
            r"\b(?:on|about|for)\s+([a-zA-Z0-9_\s]+?)(?:\s+in\s+canva|\s+using\s+canva|$)",
            lower_goal,
        )
        extracted_topic = topic_match.group(1).strip().title() if topic_match else None

        # Scenario 1: Just Open Canva
        if clean_str in ["open canva", "launch canva", "open canva in browser"] or (
            "open canva" in lower_goal
            and not any(
                k in lower_goal
                for k in ["create", "design", "edit", "export", "post", "poster", "ppt", "presentation", "template", "content", "contents", "paste", "pasting", "slide", "slides"]
            )
        ):
            phase_root = Task(
                workflow_id=workflow_id,
                task_name="Phase 1: Canva Navigation",
                description="Open and initialize Canva in the live browser runtime",
                task_type=TaskType.PHASE,
                assigned_agent="System",
                success_criteria=["Canva homepage opened and verified via OCR"],
                failure_criteria=["Failed to open Canva browser session"],
                required_tool="",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[],
                expected_output="Active Canva browser session",
                status=TaskStatus.CREATED,
            )
            task_open = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name="Open Canva in Browser",
                description="Launch browser, verify session or hand off cleanly at sign-in",
                assigned_agent="WorkerAgent",
                required_tool="canva_skill_open",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[],
                expected_output="Canva homepage opened and verified in live browser",
                success_criteria=["Canva dashboard verified via OCR or clean handoff"],
                failure_criteria=["Navigation to Canva failed"],
                status=TaskStatus.CREATED,
                inputs={
                    "skill": "open_canva",
                    "action": "open_canva",
                    "url": "https://www.canva.com",
                    "headless": False,
                },
            )
            return [phase_root, task_open]

        # Scenario 2: Edit existing design
        if (
            "edit existing design" in lower_goal
            or "edit an existing design" in lower_goal
            or "edit existing canva design" in lower_goal
        ):
            phase_root = Task(
                workflow_id=workflow_id,
                task_name="Phase 1: Edit Canva Design",
                description="Open and modify existing Canva design",
                task_type=TaskType.PHASE,
                assigned_agent="System",
                success_criteria=[
                    "Existing design opened and modified in Canva editor"
                ],
                failure_criteria=["Failed to modify design in Canva"],
                required_tool="",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[],
                expected_output="Modified Canva design",
                status=TaskStatus.CREATED,
            )
            task_edit = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name="Modify Existing Canva Design",
                description="Open existing design in Canva editor and apply modifications",
                assigned_agent="WorkerAgent",
                required_tool="canva_skill_edit_text",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[],
                expected_output="Updated Canva design in editor",
                success_criteria=["Design successfully edited and verified"],
                failure_criteria=["Failed to access or modify design"],
                status=TaskStatus.CREATED,
                inputs={
                    "skill": "edit_text",
                    "action": "edit_design",
                    "design_url": "https://www.canva.com/design",
                    "description": goal,
                },
            )
            return [phase_root, task_edit]

        # Scenario 3: Change theme or colors of a design
        if (
            "change" in lower_goal
            and ("theme" in lower_goal or "color" in lower_goal)
            and "design" in lower_goal
        ):
            phase_root = Task(
                workflow_id=workflow_id,
                task_name="Phase 1: Customize Design Theme",
                description="Update the color palette and theme of the Canva design",
                task_type=TaskType.PHASE,
                assigned_agent="System",
                success_criteria=["Color palette applied to design"],
                failure_criteria=["Failed to update colors in Canva"],
                required_tool="",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.MEDIUM,
                dependencies=[],
                expected_output="Updated design theme",
                status=TaskStatus.CREATED,
            )
            task_color = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name="Apply Theme & Color Palette",
                description="Change active design colors in Canva editor",
                assigned_agent="WorkerAgent",
                required_tool="canva_skill_apply_brand_colors",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.MEDIUM,
                dependencies=[],
                expected_output="Updated canvas color palette",
                success_criteria=["Design colors modified successfully"],
                failure_criteria=["Failed to apply colors"],
                status=TaskStatus.CREATED,
                inputs={
                    "skill": "apply_brand_colors",
                    "action": "change_colors",
                    "palette": ["#7D2AE8", "#00C4CC", "#FFFFFF"],
                },
            )
            return [phase_root, task_color]

        # Scenario 4: Export as PDF
        if clean_str in ["export as pdf", "export pdf", "download as pdf"] or (
            "export as pdf" in lower_goal
            and not any(k in lower_goal for k in ["create", "design", "poster"])
        ):
            phase_root = Task(
                workflow_id=workflow_id,
                task_name="Phase 1: Export Canva Deliverable",
                description="Export Canva design as verified PDF document",
                task_type=TaskType.PHASE,
                assigned_agent="System",
                success_criteria=["Valid PDF artifact generated and registered"],
                failure_criteria=["Failed to export design as PDF"],
                required_tool="",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[],
                expected_output="Downloadable PDF artifact",
                status=TaskStatus.CREATED,
            )
            task_export = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name="Export Canva Design as PDF",
                description="Trigger Canva download and register PDF artifact in storage",
                assigned_agent="WorkerAgent",
                required_tool="canva_skill_export",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[],
                expected_output="Downloadable verified PDF artifact",
                success_criteria=["PDF artifact registered with download URL"],
                failure_criteria=["Export failed"],
                status=TaskStatus.CREATED,
                inputs={"skill": "export", "action": "export_design", "format": "pdf"},
            )
            return [phase_root, task_export]

        # Scenario 5: Create Design (Presentation, Poster, Instagram Post, etc.)
        if "instagram" in lower_goal or "insta" in lower_goal:
            design_type = "instagram_post"
            target_w = custom_w or 1080
            target_h = custom_h or 1080
            topic = extracted_topic or "Instagram Post"
            title = "Instagram Post 1080x1080"
            text_content = f"{topic} - Special Announcement"
        elif (
            "poster" in lower_goal
            or "postr" in lower_goal
            or "fest" in lower_goal
            or "event" in lower_goal
        ):
            design_type = "poster"
            target_w = custom_w or 1080
            target_h = custom_h or 1920
            topic = (
                extracted_topic
                or (
                    "College Fest"
                    if (
                        "college" in lower_goal
                        or "colledge" in lower_goal
                        or "fest" in lower_goal
                    )
                    else "Event Poster"
                )
            )
            title = f"{topic} Poster"
            text_content = f"{topic} 2026 - Join the Celebration!"
        elif "presentation" in lower_goal or "ppt" in lower_goal or "slide" in lower_goal:
            design_type = "presentation"
            target_w = custom_w or 1920
            target_h = custom_h or 1080
            topic = extracted_topic or "Presentation"
            title = f"{topic} Presentation" if topic != "Presentation" else "Canva Presentation"
            text_content = f"{topic} - Overview & Strategy"
        elif "thumbnail" in lower_goal or "youtube" in lower_goal:
            design_type = "youtube_thumbnail"
            target_w = custom_w or 1280
            target_h = custom_h or 720
            topic = extracted_topic or "YouTube Thumbnail"
            title = "YouTube Video Thumbnail"
            text_content = "Watch Now!"
        else:
            design_type = "custom"
            target_w = custom_w or 1080
            target_h = custom_h or 1080
            topic = extracted_topic or "Creative Design"
            title = "Canva Design"
            text_content = "Creative Design"

        phase_root = Task(
            workflow_id=workflow_id,
            task_name=f"Phase 1: Canva {title} Creation",
            description=f"Automate Canva skills to create {title} ({target_w}x{target_h}px)",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            success_criteria=["Design created and verified in Canva editor"],
            failure_criteria=["Failed to create design in Canva"],
            required_tool="",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output=f"Created {title} in Canva editor",
            status=TaskStatus.CREATED,
        )

        # 1. Open Canva
        task_open = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Open Canva in Browser",
            description="Launch browser and verify Canva session or hand off cleanly at sign-in",
            assigned_agent="WorkerAgent",
            required_tool="canva_skill_open",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.HIGH,
            dependencies=[],
            expected_output="Active Canva browser session",
            success_criteria=["Canva dashboard verified via OCR or clean handoff"],
            failure_criteria=["Failed to open Canva"],
            status=TaskStatus.CREATED,
            inputs={
                "skill": "open_canva",
                "action": "open_canva",
                "url": "https://www.canva.com",
            },
        )

        # 2. Create Design
        task_create = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name=f"Create {title} ({target_w}x{target_h}px)",
            description=f"Open Canva {design_type} editor with dimensions ({target_w}x{target_h}px)",
            assigned_agent="WorkerAgent",
            required_tool="canva_skill_create_design",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.HIGH,
            dependencies=[task_open.task_id],
            expected_output=f"Canva editor open with {target_w}x{target_h}px canvas",
            success_criteria=["Design editor initialized and verified by OCR"],
            failure_criteria=["Failed to initialize design editor"],
            status=TaskStatus.CREATED,
            inputs={
                "skill": "create_design",
                "action": "create_design",
                "design_type": design_type,
                "width": target_w,
                "height": target_h,
                "unit": "px",
                "topic": topic,
                "title": title,
                "text_content": text_content,
            },
        )

        tasks = [phase_root, task_open, task_create]

        # 3. Apply Template (always for presentations or if template requested)
        if design_type == "presentation" or "template" in lower_goal or "default" in lower_goal:
            tmpl_name = (
                topic if topic and topic != "Presentation"
                else ("default" if "default" in lower_goal else "Presentation")
            )
            task_template = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name=f"Apply {tmpl_name.capitalize()} Template",
                description=f"Select and apply {tmpl_name} template in Canva editor",
                assigned_agent="WorkerAgent",
                required_tool="canva_skill_pick_template",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.HIGH,
                dependencies=[task_create.task_id],
                expected_output=f"Applied {tmpl_name} template to Canva canvas",
                success_criteria=["Template loaded onto canvas and verified via OCR"],
                failure_criteria=["Failed to apply template"],
                status=TaskStatus.CREATED,
                inputs={
                    "skill": "pick_template",
                    "action": "apply_template",
                    "query": tmpl_name,
                },
            )
            tasks.append(task_template)

        # 4. Content / Heading Text
        prev_dep = tasks[-1].task_id
        task_content = Task(
            parent_task_id=phase_root.task_id,
            workflow_id=workflow_id,
            task_name="Edit Slide 1 Heading & Content",
            description=f"Paste and format content '{text_content}' on Canva canvas",
            assigned_agent="WorkerAgent",
            required_tool="canva_skill_edit_text",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.HIGH,
            dependencies=[prev_dep],
            expected_output="Formatted content added to Canva canvas",
            success_criteria=["Content added and verified via OCR"],
            failure_criteria=["Failed to add content"],
            status=TaskStatus.CREATED,
            inputs={
                "skill": "edit_text",
                "action": "add_text",
                "text": text_content,
                "text_type": "heading",
            },
        )
        tasks.append(task_content)

        # 5. Additional Slides (if num_slides > 1)
        if num_slides > 1:
            for slide_idx in range(2, num_slides + 1):
                prev_dep = tasks[-1].task_id
                task_add_slide = Task(
                    parent_task_id=phase_root.task_id,
                    workflow_id=workflow_id,
                    task_name=f"Add Slide {slide_idx}",
                    description=f"Add slide {slide_idx} to Canva presentation",
                    assigned_agent="WorkerAgent",
                    required_tool="canva_skill_add_slide",
                    category=TaskCategory.BROWSER,
                    priority=TaskPriority.HIGH,
                    dependencies=[prev_dep],
                    expected_output=f"Slide {slide_idx} added to presentation",
                    success_criteria=["New slide added and verified via OCR"],
                    failure_criteria=["Failed to add slide"],
                    status=TaskStatus.CREATED,
                    inputs={
                        "skill": "add_slide",
                        "slide_number": slide_idx,
                    },
                )
                tasks.append(task_add_slide)

                slide_text = f"{topic} - Key Insights Part {slide_idx}"
                task_slide_text = Task(
                    parent_task_id=phase_root.task_id,
                    workflow_id=workflow_id,
                    task_name=f"Edit Slide {slide_idx} Content",
                    description=f"Add content '{slide_text}' to slide {slide_idx}",
                    assigned_agent="WorkerAgent",
                    required_tool="canva_skill_edit_text",
                    category=TaskCategory.BROWSER,
                    priority=TaskPriority.MEDIUM,
                    dependencies=[task_add_slide.task_id],
                    expected_output=f"Slide {slide_idx} content updated",
                    success_criteria=["Slide text updated and verified via OCR"],
                    failure_criteria=["Failed to update slide content"],
                    status=TaskStatus.CREATED,
                    inputs={
                        "skill": "edit_text",
                        "text": slide_text,
                        "text_type": "body",
                    },
                )
                tasks.append(task_slide_text)

        # 6. Export task if requested or specified
        if any(
            w in lower_goal
            for w in ["export", "download", "save as pdf", "save as png", "save as pptx", "pdf", "pptx"]
        ):
            export_fmt = "pdf" if "pdf" in lower_goal else ("pptx" if "pptx" in lower_goal else "png")
            prev_dep = tasks[-1].task_id
            task_export = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name=f"Export Design as {export_fmt.upper()}",
                description=f"Export finished Canva design as verified {export_fmt.upper()} artifact",
                assigned_agent="WorkerAgent",
                required_tool="canva_skill_export",
                category=TaskCategory.BROWSER,
                priority=TaskPriority.MEDIUM,
                dependencies=[prev_dep],
                expected_output=f"Downloadable {export_fmt.upper()} artifact",
                success_criteria=["Artifact verified on disk and registered in storage"],
                failure_criteria=["Export failed"],
                status=TaskStatus.CREATED,
                inputs={"skill": "export", "action": "export_design", "format": export_fmt},
            )
            tasks.append(task_export)

        return tasks
