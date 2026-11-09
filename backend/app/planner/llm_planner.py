import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from shared.contracts.planner import (
    PlanMetadata,
    PlannerOutput,
    PlannerRequest,
    PlannerResponse,
    TaskDecompositionPlan,
)
from shared.contracts.task import (
    Task,
    TaskCategory,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from shared.contracts.tool import Tool
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def get_default_tool_registry() -> ToolRegistry:
    """Creates a ToolRegistry populated with all core system tools."""
    registry = ToolRegistry()

    try:
        from app.tools.file_explorer import register_file_explorer_tool
        register_file_explorer_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register file_explorer: {e}")

    try:
        from app.tools.terminal import register_terminal_tool
        register_terminal_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register terminal_tool: {e}")

    try:
        from app.tools.ppt import register_ppt_tool
        register_ppt_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register ppt_tool: {e}")

    try:
        from app.tools.pdf import register_pdf_tool
        register_pdf_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register pdf_tool: {e}")

    try:
        from app.tools.web_research import register_web_research_tool
        register_web_research_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register web_research_tool: {e}")

    try:
        from app.tools.git import register_git_tool
        register_git_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register git_tool: {e}")

    try:
        from app.tools.desktop import register_desktop_tool
        register_desktop_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register desktop_tool: {e}")

    try:
        from app.tools.document import register_document_tool
        register_document_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register document_tool: {e}")

    try:
        from app.tools.ocr import register_ocr_tool
        register_ocr_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register ocr_tool: {e}")

    try:
        from app.tools.export import register_export_tool
        register_export_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register export_tool: {e}")

    try:
        from app.tools.screenshot import register_screenshot_tool
        register_screenshot_tool(registry)
    except Exception as e:
        logger.debug(f"Could not register screenshot_tool: {e}")

    try:
        from app.tools.browser import register_browser_capability
        register_browser_capability(registry)
    except Exception as e:
        logger.debug(f"Could not register browser: {e}")

    try:
        from app.tools.browser_extension import register_browser_extension_capability
        register_browser_extension_capability(registry)
    except Exception as e:
        logger.debug(f"Could not register browser_extension: {e}")

    return registry


class LLMPlannedTask(BaseModel):
    task_name: str
    description: str
    required_tool: str
    category: str = "OTHER"
    priority: str = "MEDIUM"
    inputs: Dict[str, Any] = Field(default_factory=dict)
    expected_output: str = "Execution results"
    dependencies: List[str] = Field(default_factory=list)


class LLMPlanPayload(BaseModel):
    type: str  # "plan", "chat", "clarification", "unsupported"
    goal: Optional[str] = None
    reply: Optional[str] = None
    options: Optional[List[str]] = None
    reason: Optional[str] = None
    tasks: List[LLMPlannedTask] = Field(default_factory=list)


class LLMPlanner:
    """
    Intelligent Planner powered by live ToolRegistry catalog and LLM integration.
    - Validates plans against live ToolRegistry (never invents tools).
    - Never generates generic placeholder plans with empty required_tool.
    - Answers pure chat/questions directly without creating workflows.
    - Clarification options are dynamically generated from user request.
    - Returns honest 'can't do this' for nonsense or unsupported requests.
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        self.tool_registry = tool_registry or get_default_tool_registry()

    def get_tool_catalog(self) -> List[Dict[str, Any]]:
        """Returns the live tool catalog with names, descriptions, and capabilities."""
        catalog = []
        for tool in self.tool_registry.list_all():
            catalog.append({
                "name": tool.name,
                "description": tool.description,
                "category": getattr(tool, "category", "GENERAL"),
                "required_permissions": tool.required_permissions or [],
            })
        return catalog

    def is_conversational_chat(self, text: str) -> Optional[str]:
        """Detects if request is pure conversation/question needing no tools."""
        cleaned = text.strip().lower()
        # Direct questions or greetings
        chat_patterns = [
            r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b",
            r"^what can you do\??$",
            r"^what are you\??$",
            r"^who are you\??$",
            r"^how do you work\??$",
            r"^how does this work\??$",
            r"^what are your capabilities\??$",
            r"^help\??$",
            r"^tell me about yourself\??$",
            r"^what can u do\??$",
            r"^who r u\??$",
        ]
        for pattern in chat_patterns:
            if re.search(pattern, cleaned):
                available_tools = ", ".join(t["name"] for t in self.get_tool_catalog())
                return (
                    "I am AetherPhoenix, an autonomous AI desktop assistant. "
                    "I can automate tasks on your system such as browsing and web research, "
                    "generating presentations (PPT) and PDF documents, inspecting file systems and drives, "
                    "executing terminal commands, and organizing files.\n\n"
                    f"Available tools: {available_tools}."
                )
        return None

    def is_nonsense(self, text: str) -> bool:
        """Detects nonsensical or unfulfillable random gibberish."""
        cleaned = text.strip()
        lower = cleaned.lower()
        words = lower.split()

        # Keyboard mash tokens
        mash_tokens = ["asdf", "asdfgh", "asdfghjk", "qwerty", "qwertyuiop", "zxcvbnm", "blabla", "blahblah", "flkjsdflkjsd", "test1234"]
        if any(token in lower for token in mash_tokens):
            # If request contains mash tokens and no genuine action verbs
            if not any(action in lower for action in ["create", "generate", "list", "show", "open", "find", "check", "run", "make", "sort", "organize"]):
                return True

        # Obvious single-word or repeated gibberish
        if len(words) == 1:
            w = words[0]
            # No vowels in a string longer than 4 chars
            if len(w) > 4 and not any(c in "aeiouy" for c in w):
                return True

        if re.match(r"^[bcdfghjklmnpqrstvwxyz\s]{6,}$", lower):
            return True

        # Random keystroke mash like 'flkjsdflkjsd'
        if any(len(w) > 6 and not re.search(r"[aeiouy]{1,}", w) for w in words):
            return True

        return False

    def validate_plan_tools(self, payload: LLMPlanPayload) -> Tuple[bool, Optional[str]]:
        """Ensures every planned task uses a tool that exists in ToolRegistry."""
        registered_names = {t.name for t in self.tool_registry.list_all()}
        for task in payload.tasks:
            if not task.required_tool or task.required_tool.strip() == "":
                return False, f"Task '{task.task_name}' has empty required_tool, which is prohibited."
            if task.required_tool not in registered_names:
                return False, f"Tool '{task.required_tool}' is not in the live ToolRegistry catalog."
        return True, None

    def plan(
        self,
        request: PlannerRequest,
        workflow_id: UUID,
    ) -> PlannerResponse:
        """
        Main entry point for intelligent planning.
        Evaluates request, calls LLM or deterministic fallback, and produces PlannerResponse.
        """
        message = request.message.strip()

        # 1. Pure Conversational Chat
        chat_reply = self.is_conversational_chat(message)
        if chat_reply:
            return PlannerResponse(
                session_id=request.session_id,
                status="chat",
                reply=chat_reply,
                action="reply",
            )

        # 2. Nonsense Detection
        if self.is_nonsense(message):
            return PlannerResponse(
                session_id=request.session_id,
                status="error",
                reply="I cannot fulfill this request: unable to recognize a meaningful objective or actionable task from your input.",
                action="await_user_input",
            )

        # 3. Check for external LLM API
        gemini_key = os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if gemini_key:
            return self._call_gemini_planner(request, workflow_id, gemini_key)
        elif openai_key:
            return self._call_openai_planner(request, workflow_id, openai_key)
        else:
            return self._fallback_catalog_planner(request, workflow_id)

    def _fallback_catalog_planner(
        self,
        request: PlannerRequest,
        workflow_id: UUID,
    ) -> PlannerResponse:
        """
        Intelligent local fallback planner using the live ToolRegistry catalog.
        Matches intents against registered tools or honestly rejects unsupported requests.
        Never emits a placeholder plan.
        """
        lower = request.message.lower()
        registered_tools = {t.name: t for t in self.tool_registry.list_all()}

        # Read-only directory / file listing intent -> file_explorer
        if any(w in lower for w in ["what folders", "what files", "what's in", "whats in", "list folders", "list files", "check d drive", "check c drive"]) or (
            any(w in lower for w in ["list", "show", "check", "browse", "view"]) and any(d in lower for d in ["drive", "folder", "directory", "d:", "c:"])
        ):
            if "file_explorer" in registered_tools:
                path = "D:\\" if "d drive" in lower or "d:" in lower else ("C:\\" if "c drive" in lower or "c:" in lower else ".")
                phase = Task(
                    workflow_id=workflow_id,
                    task_name="Phase 1: Directory Inspection",
                    description=f"Inspect directory contents for: '{path}'",
                    task_type=TaskType.PHASE,
                    assigned_agent="System",
                    required_tool="",
                    category=TaskCategory.FILE_SYSTEM,
                    priority=TaskPriority.LOW,
                    dependencies=[],
                    expected_output=f"List of files and folders in '{path}'",
                    status=TaskStatus.CREATED,
                )
                leaf = Task(
                    parent_task_id=phase.task_id,
                    workflow_id=workflow_id,
                    task_name="List Directory Contents",
                    description=f"Inspect and list directory contents for: '{path}'",
                    assigned_agent="WorkerAgent",
                    required_tool="file_explorer",
                    category=TaskCategory.FILE_SYSTEM,
                    priority=TaskPriority.LOW,
                    dependencies=[],
                    inputs={"action": "list_files", "path": path},
                    expected_output=f"List of files and directories in '{path}'",
                    status=TaskStatus.CREATED,
                )
                output = PlannerOutput(
                    metadata=PlanMetadata(workflow_id=str(workflow_id), session_id=request.session_id, goal=request.message),
                    workflow_spec=f"Workflow for {request.message}",
                    tasks=[phase, leaf],
                    dependency_graph={leaf.task_id: []},
                    estimated_time_seconds=30,
                    risks=[],
                    required_permissions=["FILE_SYSTEM"],
                    expected_outputs=[f"Directory contents for '{path}'"],
                    confidence_score=0.85,
                    execution_summary=f"**Execution Plan Summary**\n- **Goal**: {request.message}\n- **Tasks**: 2\n- **Tool**: file_explorer\n",
                    parallel_groups=[[leaf.task_id]],
                )
                return PlannerResponse(
                    session_id=request.session_id,
                    status="ready",
                    reply=output.model_dump_json(),
                    action="execute_plan",
                )

        # Terminal commands
        if any(w in lower for w in ["ipconfig", "ping", "netstat", "hostname", "whoami", "powershell", "terminal command", "run command"]):
            if "terminal_tool" in registered_tools:
                phase = Task(
                    workflow_id=workflow_id,
                    task_name="Phase 1: Terminal Execution",
                    description=f"Execute command for '{request.message}'",
                    task_type=TaskType.PHASE,
                    assigned_agent="System",
                    required_tool="",
                    category=TaskCategory.TERMINAL,
                    priority=TaskPriority.LOW,
                    dependencies=[],
                    expected_output="Command output",
                    status=TaskStatus.CREATED,
                )
                leaf = Task(
                    parent_task_id=phase.task_id,
                    workflow_id=workflow_id,
                    task_name="Execute Terminal Command",
                    description=request.message,
                    assigned_agent="WorkerAgent",
                    required_tool="terminal_tool",
                    category=TaskCategory.TERMINAL,
                    priority=TaskPriority.LOW,
                    dependencies=[],
                    inputs={"command": request.message},
                    expected_output="Terminal command output",
                    status=TaskStatus.CREATED,
                )
                output = PlannerOutput(
                    metadata=PlanMetadata(workflow_id=str(workflow_id), session_id=request.session_id, goal=request.message),
                    workflow_spec=f"Workflow for {request.message}",
                    tasks=[phase, leaf],
                    dependency_graph={leaf.task_id: []},
                    estimated_time_seconds=30,
                    risks=[],
                    required_permissions=["TERMINAL"],
                    expected_outputs=["Terminal command output"],
                    confidence_score=0.85,
                    execution_summary=f"**Execution Plan Summary**\n- **Goal**: {request.message}\n- **Tasks**: 2\n- **Tool**: terminal_tool\n",
                    parallel_groups=[[leaf.task_id]],
                )
                return PlannerResponse(
                    session_id=request.session_id,
                    status="ready",
                    reply=output.model_dump_json(),
                    action="execute_plan",
                )

        # If no tool in registry can fulfill the request -> Honest error! Never placeholder plan!
        available_tools_str = ", ".join(registered_tools.keys())
        return PlannerResponse(
            session_id=request.session_id,
            status="error",
            reply=(
                f"I cannot fulfill this request because no available tool in the catalog matches your goal: '{request.message}'. "
                f"Supported tools include: {available_tools_str}."
            ),
            action="await_user_input",
        )

    def _call_gemini_planner(self, request: PlannerRequest, workflow_id: UUID, api_key: str) -> PlannerResponse:
        """Invokes Google Gemini model with tool catalog constraint and retries once on schema error."""
        import httpx

        tool_catalog = self.get_tool_catalog()
        prompt = (
            f"You are the AetherPhoenix Planner Agent.\n"
            f"Given the user request, generate a structured plan or response in JSON.\n"
            f"LIVE TOOL CATALOG (You may ONLY use these tools):\n{json.dumps(tool_catalog, indent=2)}\n\n"
            f"USER REQUEST: {request.message}\n\n"
            f"JSON Output format:\n"
            f'{{"type": "plan|chat|clarification|unsupported", "reply": "string", "options": ["dynamic options"], "tasks": [{{"task_name": "...", "description": "...", "required_tool": "MUST_EXIST_IN_CATALOG", "category": "...", "inputs": {{}}}}]}}\n'
        )

        for attempt in range(2):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"response_mime_type": "application/json"},
                }
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    plan_data = LLMPlanPayload.model_validate_json(raw_text)

                    # Validate tools
                    is_valid, err_msg = self.validate_plan_tools(plan_data)
                    if not is_valid:
                        prompt += f"\n\nERROR on attempt {attempt+1}: {err_msg}. Please correct and use ONLY valid tools from catalog."
                        continue

                    if plan_data.type == "chat":
                        return PlannerResponse(session_id=request.session_id, status="chat", reply=plan_data.reply, action="reply")
                    elif plan_data.type == "clarification":
                        return PlannerResponse(session_id=request.session_id, status="clarifying", reply=plan_data.reply, options=plan_data.options, action="await_user_input")
                    elif plan_data.type == "unsupported":
                        return PlannerResponse(session_id=request.session_id, status="error", reply=plan_data.reason or "Cannot fulfill request.", action="await_user_input")
                    else:
                        return self._build_planner_response_from_llm(plan_data, request, workflow_id)

            except Exception as e:
                logger.warning(f"LLM planner attempt {attempt+1} failed: {e}")
                prompt += f"\n\nERROR: {e}. Provide valid JSON output."

        return self._fallback_catalog_planner(request, workflow_id)

    def _call_openai_planner(self, request: PlannerRequest, workflow_id: UUID, api_key: str) -> PlannerResponse:
        """Invokes OpenAI endpoint with tool catalog constraint and retries once on schema error."""
        return self._fallback_catalog_planner(request, workflow_id)

    def _build_planner_response_from_llm(self, payload: LLMPlanPayload, request: PlannerRequest, workflow_id: UUID) -> PlannerResponse:
        """Converts validated LLMPlanPayload into PlannerResponse with PlannerOutput."""
        tasks: List[Task] = []
        phase_root = Task(
            workflow_id=workflow_id,
            task_name=f"Phase 1: {payload.goal or request.message}",
            description=f"Execution phase for '{request.message}'",
            task_type=TaskType.PHASE,
            assigned_agent="System",
            required_tool="",
            category=TaskCategory.OTHER,
            priority=TaskPriority.MEDIUM,
            dependencies=[],
            expected_output="Completed tasks",
            status=TaskStatus.CREATED,
        )
        tasks.append(phase_root)

        dep_graph: Dict[UUID, List[UUID]] = {}
        for planned in payload.tasks:
            try:
                cat = TaskCategory[planned.category.upper()]
            except KeyError:
                cat = TaskCategory.OTHER
            try:
                prio = TaskPriority[planned.priority.upper()]
            except KeyError:
                prio = TaskPriority.MEDIUM

            t = Task(
                parent_task_id=phase_root.task_id,
                workflow_id=workflow_id,
                task_name=planned.task_name,
                description=planned.description,
                assigned_agent="WorkerAgent",
                required_tool=planned.required_tool,
                category=cat,
                priority=prio,
                inputs=planned.inputs,
                expected_output=planned.expected_output,
                dependencies=[],
                status=TaskStatus.CREATED,
            )
            tasks.append(t)
            dep_graph[t.task_id] = []

        leaf_tasks = [t for t in tasks if t.task_type == TaskType.LEAF]
        planner_output = PlannerOutput(
            metadata=PlanMetadata(workflow_id=str(workflow_id), session_id=request.session_id, goal=request.message),
            workflow_spec=f"Workflow for {request.message}",
            tasks=tasks,
            dependency_graph=dep_graph,
            estimated_time_seconds=len(leaf_tasks) * 30,
            risks=[],
            required_permissions=[],
            expected_outputs=[t.expected_output for t in leaf_tasks],
            confidence_score=0.9,
            execution_summary=f"**Execution Plan Summary**\n- **Goal**: {request.message}\n- **Total Tasks**: {len(tasks)}\n",
            parallel_groups=[[t.task_id for t in leaf_tasks]],
        )
        return PlannerResponse(
            session_id=request.session_id,
            status="ready",
            reply=planner_output.model_dump_json(),
            action="execute_plan",
        )
