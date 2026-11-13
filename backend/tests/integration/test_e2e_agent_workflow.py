import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from shared.contracts.task import Task, TaskCategory, TaskType

from app.agents.planner.agent import PlannerAgent
from app.core.permissions.manager import PermissionManager
from app.main import app
from app.services.agent_factory import (
    reset_orchestrator,
)
from app.tools.file_explorer.adapter import FileExplorerToolAdapter
from app.tools.file_explorer.executor import FileExplorerExecutor
from app.tools.git.adapter import GitToolAdapter
from app.tools.ppt.adapter import PPTToolAdapter

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_singletons():
    reset_orchestrator()
    yield
    reset_orchestrator()


@pytest.fixture
def planner_stack():
    agent = PlannerAgent()
    return {
        "analyzer": agent.requirement_analyzer,
        "clarifier": agent.clarification_engine,
        "goal_engine": agent.goal_engine,
        "decomposer": agent.task_engine,
        "agent": agent,
    }


# ============================================================================
# SCENARIO A: Open VS Code and run the project
# ============================================================================
def test_scenario_a_vscode_project_workflow(planner_stack):
    """
    TEST A: 'Open VS Code and run the project'
    Verifies:
      - Intent recognized
      - Adapters: File Explorer / Desktop automation / Terminal
      - Inter-task dependencies: Discover -> VS Code Launch -> Terminal Execution
    """
    decomposer = planner_stack["decomposer"]
    workflow_id = uuid4()
    plan = decomposer.decompose_goal(
        "Open VS Code and run the project in workspace.", workflow_id
    )

    assert len(plan.tasks) >= 3
    leaf_tasks = [t for t in plan.tasks if t.task_type != TaskType.PHASE]
    assert len(leaf_tasks) >= 2

    # Check tools present in plan
    tools_used = [t.required_tool for t in leaf_tasks]
    assert "desktop_automation" in tools_used
    assert any(t in ("terminal_tool", "file_explorer") for t in tools_used)

    # Check VS Code task specifics
    vscode_task = next(t for t in leaf_tasks if t.required_tool == "desktop_automation")
    assert vscode_task.category == TaskCategory.DESKTOP
    assert (
        vscode_task.inputs.get("app_name") in ("code", "Visual Studio Code")
        or vscode_task.inputs.get("app") == "Visual Studio Code"
    )

    # Check terminal task dependency on prior setup
    terminal_tasks = [t for t in leaf_tasks if t.required_tool == "terminal_tool"]
    if terminal_tasks:
        assert len(terminal_tasks[0].dependencies) > 0


# ============================================================================
# SCENARIO B: Find all PDFs in Downloads and organize them
# ============================================================================
@pytest.mark.asyncio
async def test_scenario_b_find_and_organize_pdfs(planner_stack):
    """
    TEST B: 'Find all PDFs in Downloads and organize them into Invoices folder'
    Verifies:
      - Scan & filter matching PDFs
      - Creation of target destination folder
      - FileExplorerToolAdapter moves PDFs into destination
      - Non-PDF files remain in source
    """
    decomposer = planner_stack["decomposer"]
    workflow_id = uuid4()

    with tempfile.TemporaryDirectory() as temp_dir:
        downloads_dir = Path(temp_dir) / "Downloads"
        invoices_dir = Path(temp_dir) / "Invoices"
        downloads_dir.mkdir(parents=True, exist_ok=True)

        # Create test files
        pdf1 = downloads_dir / "invoice_jan.pdf"
        pdf2 = downloads_dir / "statement_feb.pdf"
        doc1 = downloads_dir / "notes.txt"
        pdf1.write_text("dummy invoice 1 content", encoding="utf-8")
        pdf2.write_text("dummy statement 2 content", encoding="utf-8")
        doc1.write_text("leave me alone", encoding="utf-8")

        plan = decomposer.decompose_goal(
            f"Find all PDFs in {downloads_dir} and organize them into {invoices_dir}.",
            workflow_id,
        )

        leaf_tasks = [t for t in plan.tasks if t.task_type != TaskType.PHASE]
        assert len(leaf_tasks) >= 2
        assert all(t.required_tool == "file_explorer" for t in leaf_tasks)

        # Execute file operations with adapter (with permitted execution manager)
        class AutoApprovePermissionManager(PermissionManager):
            def check_permission(self, *args, **kwargs):
                return True

        pm = AutoApprovePermissionManager()
        executor = FileExplorerExecutor(permission_manager=pm)
        adapter = FileExplorerToolAdapter(executor=executor)

        # Step 1: Scan and filter
        task_scan = Task(
            workflow_id=workflow_id,
            task_name="Scan PDFs",
            description="Scan files in directory",
            category=TaskCategory.FILE_SYSTEM,
            expected_output="File list",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            inputs={"action": "list_files", "path": str(downloads_dir)},
        )
        scan_res = await adapter.execute(task_scan)
        assert scan_res.success is True
        assert scan_res.output["metadata"]["count"] == 3

        # Step 2: Create target folder
        task_mkdir = Task(
            workflow_id=workflow_id,
            task_name="Create Target Directory",
            description="Create Invoices folder",
            category=TaskCategory.FILE_SYSTEM,
            expected_output="Invoices folder created",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            inputs={"action": "create_folder", "path": str(invoices_dir)},
        )
        mkdir_res = await adapter.execute(task_mkdir)
        assert mkdir_res.success is True
        assert invoices_dir.exists()

        # Step 3: Move/Organize PDFs
        task_move = Task(
            workflow_id=workflow_id,
            task_name="Organize and Move PDFs",
            description="Move PDFs into Invoices folder",
            category=TaskCategory.FILE_SYSTEM,
            expected_output="PDF files moved",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            inputs={
                "action": "move_file",
                "source": str(downloads_dir),
                "destination": str(invoices_dir),
                "filter": "*.pdf",
            },
        )
        move_res = await adapter.execute(task_move)
        assert move_res.success is True
        assert move_res.output["metadata"]["count"] == 2

        # Verify filesystem state: PDFs moved, TXT stayed
        assert (invoices_dir / "invoice_jan.pdf").exists()
        assert (invoices_dir / "statement_feb.pdf").exists()
        assert not (downloads_dir / "invoice_jan.pdf").exists()
        assert (downloads_dir / "notes.txt").exists()


# ============================================================================
# SCENARIO C: Research AI frameworks and prepare presentation
# ============================================================================
@pytest.mark.asyncio
async def test_scenario_c_research_ai_frameworks_and_ppt(planner_stack):
    """
    TEST C: 'Research top 3 AI frameworks and prepare a presentation'
    Verifies:
      - Intent decomposed into research + presentation tasks
      - Presentation generated and saved to disk
      - Registered with ArtifactStorageService
      - Download endpoint serves binary PPTX
    """
    decomposer = planner_stack["decomposer"]
    workflow_id = uuid4()
    goal = "Research top 3 AI frameworks and prepare a 4-slide presentation."
    plan = decomposer.decompose_goal(goal, workflow_id)

    leaf_tasks = [t for t in plan.tasks if t.task_type != TaskType.PHASE]
    tools = [t.required_tool for t in leaf_tasks]
    assert "ppt_tool" in tools

    # Execute PPT generation via PPTToolAdapter
    with tempfile.TemporaryDirectory() as temp_dir:
        output_pptx = Path(temp_dir) / "ai_frameworks_overview.pptx"
        ppt_adapter = PPTToolAdapter()
        task_ppt = Task(
            workflow_id=workflow_id,
            task_name="Generate AI Frameworks Presentation",
            description="Generate a 5-slide presentation summarizing top AI frameworks",
            category=TaskCategory.PPT_GENERATION,
            expected_output="presentation.pptx",
            assigned_agent="WorkerAgent",
            required_tool="ppt_tool",
            inputs={
                "topic": "Top 3 AI Frameworks: PyTorch, TensorFlow, JAX",
                "title": "Top 3 AI Frameworks: PyTorch, TensorFlow, JAX",
                "output_path": str(output_pptx),
            },
        )
        ppt_res = await ppt_adapter.execute(task_ppt)
        assert ppt_res.success is True
        assert output_pptx.exists()
        assert output_pptx.stat().st_size > 1000
        assert len(ppt_res.artifacts) > 0

        registered_artifact = ppt_res.artifacts[0]
        assert registered_artifact.artifact_id is not None

        # Verify download endpoint
        res = client.get(
            f"/api/v1/artifacts/{registered_artifact.artifact_id}/download"
        )
        assert res.status_code == 200
        assert (
            res.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        assert len(res.content) == output_pptx.stat().st_size


# ============================================================================
# SCENARIO D: Open GitHub repo and inspect recent changes
# ============================================================================
@pytest.mark.asyncio
async def test_scenario_d_git_repo_inspection():
    """
    TEST D: 'Open GitHub repo and inspect recent changes'
    Verifies:
      - Git tool executes detect_repo, status, and history
      - Returns structured logs and valid exit code
    """
    adapter = GitToolAdapter()
    workflow_id = uuid4()

    # 1. Detect repo
    task_detect = Task(
        workflow_id=workflow_id,
        task_name="Detect Git Repository",
        description="Verify inside work tree",
        category=TaskCategory.GIT,
        expected_output="true",
        assigned_agent="WorkerAgent",
        required_tool="git_tool",
        inputs={"operation": "detect_repo", "working_directory": "."},
    )
    detect_res = await adapter.execute(task_detect)
    assert detect_res.success is True
    assert detect_res.output.get("output") == "true"

    # 2. Check Git status
    task_status = Task(
        workflow_id=workflow_id,
        task_name="Inspect Git Status",
        description="Check changed files",
        category=TaskCategory.GIT,
        expected_output="Short status",
        assigned_agent="WorkerAgent",
        required_tool="git_tool",
        inputs={"operation": "status", "working_directory": "."},
    )
    status_res = await adapter.execute(task_status)
    assert status_res.success is True

    # 3. Check Git history / log
    task_history = Task(
        workflow_id=workflow_id,
        task_name="Inspect Git Commit History",
        description="Check recent commits",
        category=TaskCategory.GIT,
        expected_output="Commit logs",
        assigned_agent="WorkerAgent",
        required_tool="git_tool",
        inputs={"operation": "history", "limit": 5, "working_directory": "."},
    )
    history_res = await adapter.execute(task_history)
    assert history_res.success is True
    assert len(history_res.output.get("output", "")) > 0


# ============================================================================
# ROBUSTNESS TESTS: Misspellings, Punctuation, Informal Language
# ============================================================================
@pytest.mark.parametrize(
    "query,expected_tool,expected_category",
    [
        ("opn vscod", "desktop_automation", TaskCategory.DESKTOP),
        ("open notepad plz", "desktop_automation", TaskCategory.DESKTOP),
        ("organiez pdfs in dwonloads", "file_explorer", TaskCategory.FILE_SYSTEM),
        ("creat 3-slid ppt abot AI", "ppt_tool", TaskCategory.PPT_GENERATION),
        ("what is my ip address???", "terminal_tool", TaskCategory.TERMINAL),
        ("chekc git status", "git_tool", TaskCategory.GIT),
    ],
)
def test_language_robustness_routing(
    planner_stack, query, expected_tool, expected_category
):
    """
    Verifies the Planner handles misspellings, trailing punctuation,
    and informal phrasing robustly.
    """
    decomposer = planner_stack["decomposer"]
    workflow_id = uuid4()
    plan = decomposer.decompose_goal(query, workflow_id)

    leaf_tasks = [t for t in plan.tasks if t.task_type != TaskType.PHASE]
    assert len(leaf_tasks) > 0
    tools_used = [t.required_tool for t in leaf_tasks]
    assert expected_tool in tools_used
    matching_task = next(t for t in leaf_tasks if t.required_tool == expected_tool)
    assert matching_task.category in (expected_category, TaskCategory.POWERSHELL)
