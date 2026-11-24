import json
from uuid import uuid4

import pytest
from shared.contracts.planner import PlannerRequest
from shared.contracts.task import Task, TaskCategory, TaskType

from app.agents.planner.agent import PlannerAgent


@pytest.fixture
def planner_agent():
    return PlannerAgent()


# =====================================================================
# 1. THE FOUR CORE EXAMPLE REQUESTS
# =====================================================================


def test_example_1_open_vscode_and_run_project(planner_agent):
    """Example 1: 'Open VS Code and run my project.'

    Expected tools:
      - File/project discovery (file_explorer)
      - VS Code integration (desktop_automation)
      - Terminal integration (terminal_tool)
      - Execution verification (terminal_tool)
    """
    request = PlannerRequest(
        session_id=str(uuid4()),
        message="Open VS Code and run my project.",
        context={},
    )
    response = planner_agent.process_request(request)

    assert response.status == "ready"
    assert response.action == "execute_plan"
    assert response.reply is not None

    plan = json.loads(response.reply)
    tasks = plan.get("tasks", [])
    leaf_tasks = [t for t in tasks if t.get("task_type") == TaskType.LEAF.value]

    tool_names = [t.get("required_tool") for t in leaf_tasks]
    assert "file_explorer" in tool_names, "Expected file/project discovery tool"
    assert "desktop_automation" in tool_names, "Expected VS Code integration tool"
    assert "terminal_tool" in tool_names, "Expected terminal integration tool"

    # Verify task names match expected capabilities
    task_names_lower = [t.get("task_name", "").lower() for t in leaf_tasks]
    assert any("discover" in n or "structure" in n for n in task_names_lower)
    assert any("code" in n or "vscode" in n for n in task_names_lower)
    assert any("terminal" in n or "execute" in n for n in task_names_lower)
    assert any("verify" in n or "status" in n for n in task_names_lower)

    # Verify execution dependencies
    discover_task = next(
        t for t in leaf_tasks if "discover" in t.get("task_name", "").lower()
    )
    vscode_task = next(
        t for t in leaf_tasks if "code" in t.get("task_name", "").lower()
    )
    terminal_task = next(
        t for t in leaf_tasks if "execute" in t.get("task_name", "").lower()
    )
    verify_task = next(
        t for t in leaf_tasks if "verify" in t.get("task_name", "").lower()
    )

    assert discover_task["task_id"] in vscode_task["dependencies"]
    assert vscode_task["task_id"] in terminal_task["dependencies"]
    assert terminal_task["task_id"] in verify_task["dependencies"]


def test_example_2_find_pdfs_in_downloads_and_organize(planner_agent):
    """Example 2: 'Find all PDFs in Downloads and organize them.'

    Expected tools:
      - File Explorer integration (file_explorer)
      - File filtering/search (file_explorer)
      - File organization/move operations (file_explorer)
    """
    request = PlannerRequest(
        session_id=str(uuid4()),
        message="Find all PDFs in Downloads and organize them.",
        context={},
    )
    response = planner_agent.process_request(request)

    assert response.status == "ready"
    plan = json.loads(response.reply)
    tasks = plan.get("tasks", [])
    leaf_tasks = [t for t in tasks if t.get("task_type") == TaskType.LEAF.value]

    # All filesystem tasks use file_explorer
    for t in leaf_tasks:
        assert t.get("required_tool") == "file_explorer"
        assert t.get("category") == TaskCategory.FILE_SYSTEM.value

    # Verify search/filtering and move actions are present
    task_names_lower = [t.get("task_name", "").lower() for t in leaf_tasks]
    assert any("filter" in n or "scan" in n or "list" in n for n in task_names_lower)
    assert any(
        "create" in n or "target" in n or "directory" in n for n in task_names_lower
    )
    assert any("organize" in n or "move" in n for n in task_names_lower)

    # Verify parameters: path contains Downloads, filter targets PDF
    scan_task = next(
        t
        for t in leaf_tasks
        if "scan" in t.get("task_name", "").lower()
        or "filter" in t.get("task_name", "").lower()
    )
    assert "downloads" in scan_task.get("inputs", {}).get("path", "").lower()
    assert "pdf" in scan_task.get("inputs", {}).get("filter", "").lower()


def test_example_3_research_ai_frameworks_and_presentation(planner_agent):
    """Example 3: 'Research the latest AI agent frameworks and prepare a presentation.'

    Expected tools:
      - Web research (web_research_tool)
      - Information extraction (web_research_tool / ppt_tool)
      - PPT generation (ppt_tool)
      - Artifact storage (export)
    """
    request = PlannerRequest(
        session_id=str(uuid4()),
        message="Research the latest AI agent frameworks and prepare a presentation.",
        context={},
    )
    response = planner_agent.process_request(request)

    assert response.status == "ready"
    plan = json.loads(response.reply)
    tasks = plan.get("tasks", [])
    leaf_tasks = [t for t in tasks if t.get("task_type") == TaskType.LEAF.value]

    tool_names = [t.get("required_tool") for t in leaf_tasks]
    assert "web_research_tool" in tool_names, "Expected web research tool"
    assert "ppt_tool" in tool_names, "Expected PPT generation tool"
    assert "export" in tool_names, "Expected artifact storage export tool"

    # Verify dependency chain: research -> outline -> build pptx -> export/store
    research_task = next(
        t for t in leaf_tasks if t.get("required_tool") == "web_research_tool"
    )
    ppt_tasks = [t for t in leaf_tasks if t.get("required_tool") == "ppt_tool"]
    export_task = next(t for t in leaf_tasks if t.get("required_tool") == "export")

    # Outline depends on research
    outline_task = next(
        t for t in ppt_tasks if "outline" in t.get("task_name", "").lower()
    )
    assert research_task["task_id"] in outline_task["dependencies"]

    # Build deck depends on outline
    build_task = next(
        t
        for t in ppt_tasks
        if "build" in t.get("task_name", "").lower()
        or "deck" in t.get("task_name", "").lower()
    )
    assert outline_task["task_id"] in build_task["dependencies"]

    # Export depends on build deck
    assert build_task["task_id"] in export_task["dependencies"]


def test_example_4_open_github_repo_and_inspect_changes(planner_agent):
    """Example 4: 'Open my GitHub repository and inspect the latest changes.'

    Expected tools:
      - GitHub integration (git_tool)
      - Repository inspection (git_tool)
      - Commit/branch history (git_tool)
      - Diff inspection (git_tool)
    """
    request = PlannerRequest(
        session_id=str(uuid4()),
        message="Open my GitHub repository and inspect the latest changes.",
        context={"repository": "KAUSHALK123/AetherPhoenix"},
    )
    response = planner_agent.process_request(request)

    assert response.status == "ready"
    plan = json.loads(response.reply)
    tasks = plan.get("tasks", [])
    leaf_tasks = [t for t in tasks if t.get("task_type") == TaskType.LEAF.value]

    for t in leaf_tasks:
        assert t.get("required_tool") == "git_tool"
        assert t.get("category") == TaskCategory.GIT.value

    task_names_lower = [t.get("task_name", "").lower() for t in leaf_tasks]
    assert any(
        "status" in n or "structure" in n for n in task_names_lower
    ), "Expected repository inspection"
    assert any(
        "commit" in n or "history" in n for n in task_names_lower
    ), "Expected commit/branch history"
    assert any(
        "diff" in n or "modification" in n for n in task_names_lower
    ), "Expected diff inspection"


# =====================================================================
# 2. TERMINAL COMMAND ISOLATION (NO ACCIDENTAL PDF GENERATION)
# =====================================================================


def test_ipconfig_terminal_command_isolation(planner_agent):
    """A user requesting ipconfig must trigger a terminal command, never a PDF."""
    for query in ["ipconfig", "run ipconfig", "whats my ipconfig", "ipconfig /all"]:
        request = PlannerRequest(session_id=str(uuid4()), message=query)
        response = planner_agent.process_request(request)

        assert (
            response.status == "ready"
        ), f"Query '{query}' should be ready, got: {response.status}"
        plan = json.loads(response.reply)
        tasks = plan.get("tasks", [])
        leaf_tasks = [t for t in tasks if t.get("task_type") == TaskType.LEAF.value]

        # Ensure terminal_tool is assigned
        assert any(t.get("required_tool") == "terminal_tool" for t in leaf_tasks)

        # Strictly ensure NO PDF or presentation generation tasks were accidentally generated
        for t in tasks:
            assert t.get("category") != TaskCategory.PDF_GENERATION.value
            assert t.get("category") != TaskCategory.PPT_GENERATION.value
            assert "pdf" not in t.get("required_tool", "").lower()
            assert "ppt" not in t.get("required_tool", "").lower()


def test_diagnostic_commands_routing(planner_agent):
    """Diagnostic commands like whoami, hostname, ping must select terminal."""
    for cmd in ["whoami", "hostname", "ping 127.0.0.1", "netstat -an"]:
        request = PlannerRequest(session_id=str(uuid4()), message=cmd)
        response = planner_agent.process_request(request)

        assert response.status == "ready"
        plan = json.loads(response.reply)
        leaf_tasks = [
            t
            for t in plan.get("tasks", [])
            if t.get("task_type") == TaskType.LEAF.value
        ]
        assert any(t.get("required_tool") == "terminal_tool" for t in leaf_tasks)


# =====================================================================
# 3. MISSPELLED REQUESTS & TYPO TOLERANCE
# =====================================================================


def test_misspelled_requests(planner_agent):
    """Planner must understand misspelled sentences and select correct tools."""
    # Misspelled Example 1
    r1 = planner_agent.process_request(
        PlannerRequest(session_id=str(uuid4()), message="opn vs code nd run my prject")
    )
    assert r1.status == "ready"
    plan1 = json.loads(r1.reply)
    tools1 = [
        t.get("required_tool")
        for t in plan1.get("tasks", [])
        if t.get("task_type") == TaskType.LEAF.value
    ]
    assert "desktop_automation" in tools1
    assert "terminal_tool" in tools1

    # Misspelled Example 2
    r2 = planner_agent.process_request(
        PlannerRequest(
            session_id=str(uuid4()),
            message="find all pdfs in dowlnoads and orgnize them",
        )
    )
    assert r2.status == "ready"
    plan2 = json.loads(r2.reply)
    tools2 = [
        t.get("required_tool")
        for t in plan2.get("tasks", [])
        if t.get("task_type") == TaskType.LEAF.value
    ]
    assert "file_explorer" in tools2

    # Misspelled Example 3
    r3 = planner_agent.process_request(
        PlannerRequest(
            session_id=str(uuid4()),
            message="reseach latest ai agent frameworks and prep a presntation",
        )
    )
    assert r3.status == "ready"
    plan3 = json.loads(r3.reply)
    tools3 = [
        t.get("required_tool")
        for t in plan3.get("tasks", [])
        if t.get("task_type") == TaskType.LEAF.value
    ]
    assert "web_research_tool" in tools3
    assert "ppt_tool" in tools3

    # Misspelled Example 4
    r4 = planner_agent.process_request(
        PlannerRequest(
            session_id=str(uuid4()),
            message="open my gthub repositry and inspct the latest changes",
            context={"repository": "owner/repo"},
        )
    )
    assert r4.status == "ready"
    plan4 = json.loads(r4.reply)
    tools4 = [
        t.get("required_tool")
        for t in plan4.get("tasks", [])
        if t.get("task_type") == TaskType.LEAF.value
    ]
    assert "git_tool" in tools4


# =====================================================================
# 4. JUMBLED SENTENCE STRUCTURES
# =====================================================================


def test_jumbled_sentence_structures(planner_agent):
    """Planner must extract intent and select tools regardless of word order."""
    # Word order inverted: "In downloads find all pdfs and organize"
    r1 = planner_agent.process_request(
        PlannerRequest(
            session_id=str(uuid4()), message="In downloads find all pdfs and organize"
        )
    )
    assert r1.status == "ready"
    plan1 = json.loads(r1.reply)
    tools1 = [
        t.get("required_tool")
        for t in plan1.get("tasks", [])
        if t.get("task_type") == TaskType.LEAF.value
    ]
    assert "file_explorer" in tools1

    # Inverted: "prepare presentation after researching AI agent frameworks"
    r2 = planner_agent.process_request(
        PlannerRequest(
            session_id=str(uuid4()),
            message="Prepare a presentation after researching AI agent frameworks",
        )
    )
    assert r2.status == "ready"
    plan2 = json.loads(r2.reply)
    tools2 = [
        t.get("required_tool")
        for t in plan2.get("tasks", [])
        if t.get("task_type") == TaskType.LEAF.value
    ]
    assert "web_research_tool" in tools2
    assert "ppt_tool" in tools2


# =====================================================================
# 5. MULTI-STEP INSTRUCTIONS & DAG TOPOLOGY
# =====================================================================


def test_multistep_instructions_dag_topology(planner_agent):
    """Multi-step goals must produce a valid acyclic DAG with correct prerequisites."""
    request = PlannerRequest(
        session_id=str(uuid4()),
        message="Open VS Code and run my project.",
    )
    response = planner_agent.process_request(request)
    plan = json.loads(response.reply)

    tasks = plan["tasks"]
    dep_graph = plan["dependency_graph"]
    task_map = {t["task_id"]: t for t in tasks}

    # Verify that every dependency exists in tasks
    for task_id, deps in dep_graph.items():
        assert task_id in task_map
        for dep in deps:
            assert dep in task_map


# =====================================================================
# 6. FOLLOW-UP REQUESTS USING CONTEXT
# =====================================================================


def test_followup_requests_using_context(planner_agent):
    """Ambiguous goal asks for clarification, then follow-up fulfills it."""
    session_id = f"session-followup-{uuid4()}"

    # Turn 1: Vague request
    r1 = planner_agent.process_request(
        PlannerRequest(session_id=session_id, message="organize my files")
    )
    assert r1.status == "clarifying"
    assert session_id in planner_agent.active_sessions

    # Turn 2: Follow-up clarification
    r2 = planner_agent.process_request(
        PlannerRequest(
            session_id=session_id,
            message="Organize Downloads by file type",
        )
    )
    assert r2.status == "ready"
    assert session_id not in planner_agent.active_sessions


# =====================================================================
# 7. AMBIGUOUS REQUESTS (CLARIFICATION ASKING)
# =====================================================================


def test_clarification_on_missing_repository(planner_agent):
    """When remote repo operation is requested and repository is not identified, ask."""
    request = PlannerRequest(
        session_id=str(uuid4()),
        message="Inspect my remote github repository",
        context={"require_explicit_repo": True},
    )
    response = planner_agent.process_request(request)
    assert response.status == "clarifying"
    assert "repository" in response.reply.lower() or "github" in response.reply.lower()


def test_clarification_on_ambiguous_destination(planner_agent):
    """When destination folder is ambiguous, clarify."""
    request = PlannerRequest(
        session_id=str(uuid4()),
        message="organize my files",
        context={"ambiguous_destination": True},
    )
    response = planner_agent.process_request(request)
    assert response.status == "clarifying"


def test_clarification_on_data_loss_risk(planner_agent):
    """When an operation could cause data loss, clarify with warning."""
    request = PlannerRequest(
        session_id=str(uuid4()),
        message="delete all files in C: drive",
        context={},
    )
    response = planner_agent.process_request(request)
    assert response.status == "clarifying"
    assert (
        "data loss" in response.reply.lower() or "permanent" in response.reply.lower()
    )


def test_clarification_on_multiple_projects(planner_agent):
    """When multiple projects are detected, clarify which one to run."""
    request = PlannerRequest(
        session_id=str(uuid4()),
        message="Open VS Code and run my project",
        context={
            "multiple_projects": True,
            "detected_projects": ["Frontend (React)", "Backend (FastAPI)"],
        },
    )
    response = planner_agent.process_request(request)
    assert response.status == "clarifying"
    assert "multiple projects" in response.reply.lower()


# =====================================================================
# 8. UNKNOWN CAPABILITIES & INCORRECT TOOL SELECTION
# =====================================================================


def test_unknown_capabilities_never_silently_substituted(planner_agent):
    """Unknown tools must never be silently substituted with unrelated capabilities."""
    unsupported_task = Task(
        workflow_id=uuid4(),
        task_name="Quantum Teleportation",
        description="Teleport user across dimensions",
        required_tool="quantum_teleporter",
        category=TaskCategory.OTHER,
        expected_output="Teleportation complete",
    )
    tasks, unsupported = planner_agent.capability_engine.discover_capabilities(
        [unsupported_task]
    )

    assert (
        "quantum_teleporter" in unsupported
    ), "Unknown tool must be caught as unsupported"
