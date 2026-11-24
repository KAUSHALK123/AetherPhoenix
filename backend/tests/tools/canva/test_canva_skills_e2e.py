"""
End-to-End and Unit Tests for Canva Skills Layer (Phase 3)
Tests:
1. Registration of Canva skills in ToolRegistry.
2. Decomposer mapping: 'canva' + design/presentation/poster maps to skills.
   Specifically verifies that 'create a 5 slide presentation on AI in Canva' decomposes to
   verified skills (open, create_design, pick_template, edit_text, and 4 add_slide tasks).
3. CRITICAL risk enforcement: publishing, sharing, and purchasing templates require explicit approval.
4. Verification guard: skills verify through screenshot and OCR text, never assuming success.
5. End-to-end execution: reaching verified design OR cleanly handing off at sign-in.
"""

import asyncio
import os
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from shared.contracts.browser import BrowserResult
from shared.contracts.ocr import OCRBoundingBox, OCRResult, OCRTextSegment
from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus, TaskType

from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.core.permissions.models import ExecutionMode
from app.core.permissions.policies import SafeExecutionPolicy
from app.planner.decomposer import TaskDecompositionEngine
from app.services.artifact_storage import ArtifactStorageService
from app.tools.browser.controller import BrowserController
from app.tools.canva import (
    CANVA_SKILL_NAMES,
    CRITICAL_SKILLS,
    CanvaBrowserController,
    CanvaSkillAdapter,
    CanvaSkills,
    register_canva_skills,
)
from app.tools.ocr.engine import OCREngine
from app.tools.registry import ToolRegistry


class MockCanvaServer:
    """Lightweight HTTP server serving mock Canva pages (login wall vs editor)."""

    def __init__(self, mode: str = "login"):
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int = 0
        self.mode = mode  # "login" or "editor"

    def start(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                if parent.mode == "login":
                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head><title>Log in to Canva</title></head>
                    <body>
                        <h2>Welcome back</h2>
                        <form action="/login" method="post">
                            <input type="text" name="email" placeholder="Email" />
                            <input type="password" name="password" placeholder="Password" />
                            <button type="submit">Log in</button>
                        </form>
                    </body>
                    </html>
                    """
                else:
                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head><title>AI Presentation - Canva</title></head>
                    <body>
                        <header>
                            <button id="file-btn">File</button>
                            <button id="resize-btn">Resize</button>
                            <button id="share-btn">Share</button>
                            <button id="present-btn">Present</button>
                        </header>
                        <div id="canvas-area">
                            <h1>AI Presentation - Overview</h1>
                            <p>Key Insights Part 1</p>
                        </div>
                        <footer>
                            <button id="add-page">Add page</button>
                            <span>Page 1 of 5</span>
                        </footer>
                    </body>
                    </html>
                    """
                self.wfile.write(html.encode("utf-8"))

            def log_message(self, format, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


# ------------------------------------------------------------------------------
# Test 1: ToolRegistry Registration
# ------------------------------------------------------------------------------

def test_canva_skills_registered_in_tool_registry():
    """Verify all Canva skill tools are registered in ToolRegistry."""
    registry = ToolRegistry()
    registered = register_canva_skills(registry)

    for skill_name in CANVA_SKILL_NAMES:
        tool = registry.get(skill_name)
        assert tool is not None, f"Tool '{skill_name}' was not found in ToolRegistry."
        assert tool.status.value.lower() == "ready"
        assert tool.adapter == "app.tools.canva.skill_adapter.CanvaSkillAdapter"
        assert PermissionType.BROWSER_ACCESS.value in tool.required_permissions


# ------------------------------------------------------------------------------
# Test 2: Decomposer Mapping for 5-Slide Presentation
# ------------------------------------------------------------------------------

def test_canva_decomposer_routes_5_slide_presentation():
    """
    Verify that 'create a 5 slide presentation on AI in Canva' decomposes into
    ordered skills: open, create_design, pick_template, edit_text, and 4 add_slide tasks.
    """
    engine = TaskDecompositionEngine()
    workflow_id = uuid4()
    goal = "create a 5 slide presentation on AI in Canva"

    plan = engine.decompose_goal(goal=goal, workflow_id=workflow_id)
    leaf_tasks = [t for t in plan.tasks if t.task_type != TaskType.PHASE]

    assert len(leaf_tasks) >= 8, f"Expected at least 8 tasks, got {len(leaf_tasks)}"

    tools_used = [t.required_tool for t in leaf_tasks]
    assert "canva_skill_open" in tools_used
    assert "canva_skill_create_design" in tools_used
    assert "canva_skill_pick_template" in tools_used
    assert "canva_skill_edit_text" in tools_used

    # Verify 4 add_slide tasks (for slides 2, 3, 4, 5)
    add_slide_tasks = [t for t in leaf_tasks if t.required_tool == "canva_skill_add_slide"]
    assert len(add_slide_tasks) == 4, f"Expected 4 add_slide tasks, got {len(add_slide_tasks)}"

    # Verify input parameters contain the extracted topic and slide numbers
    create_task = next(t for t in leaf_tasks if t.required_tool == "canva_skill_create_design")
    assert create_task.inputs.get("design_type") == "presentation"
    assert "Ai" in create_task.inputs.get("topic", "")

    # Verify execution order (topological order)
    order = plan.execution_order
    open_task = next(t for t in leaf_tasks if t.required_tool == "canva_skill_open")
    assert order.index(open_task.task_id) < order.index(create_task.task_id)


# ------------------------------------------------------------------------------
# Test 3: CRITICAL Risk Gating for Publish, Share, and Purchase
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_critical_skills_require_explicit_approval():
    """
    Verify that publishing, sharing, and purchasing templates are classified as
    CRITICAL risk and blocked without explicit human approval.
    """
    # 1. Verify policy risk classification
    assert SafeExecutionPolicy.classify_risk("publish_design") == RiskLevel.CRITICAL
    assert SafeExecutionPolicy.classify_risk("share_design") == RiskLevel.CRITICAL
    assert SafeExecutionPolicy.classify_risk("purchase_template") == RiskLevel.CRITICAL
    assert SafeExecutionPolicy.classify_risk("canva_skill_publish") == RiskLevel.CRITICAL

    # 2. Setup PermissionManager in SAFE mode (requires explicit approval for critical)
    pm = PermissionManager(mode=ExecutionMode.SAFE)

    skills = CanvaSkills(
        controller=MagicMock(spec=BrowserController),
        permission_manager=pm,
    )
    adapter = CanvaSkillAdapter(skills=skills, permission_manager=pm)

    # 3. Attempt publish without approval -> PermissionDeniedException / failure
    task_publish = Task(
        workflow_id=uuid4(),
        task_name="Publish Presentation",
        description="Publish Canva presentation",
        required_tool="canva_skill_publish",
        category=TaskCategory.BROWSER,
        expected_output="Published design",
        inputs={"skill": "publish_design"},
    )
    res_pub = await adapter.execute(task_publish)
    assert not res_pub.success
    assert res_pub.error is not None
    assert res_pub.error.error_code == "PERMISSION_DENIED"

    # 4. Attempt share without approval
    task_share = Task(
        workflow_id=uuid4(),
        task_name="Share Presentation",
        description="Share Canva presentation",
        required_tool="canva_skill_share",
        category=TaskCategory.BROWSER,
        expected_output="Shared design",
        inputs={"skill": "share_design", "email": "team@example.com"},
    )
    res_share = await adapter.execute(task_share)
    assert not res_share.success
    assert res_share.error.error_code == "PERMISSION_DENIED"

    # 5. Attempt purchase without approval
    task_purchase = Task(
        workflow_id=uuid4(),
        task_name="Purchase Template",
        description="Buy Canva template",
        required_tool="canva_skill_purchase",
        category=TaskCategory.BROWSER,
        expected_output="Purchased template",
        inputs={"skill": "purchase_template", "template_id": "pro-123"},
    )
    res_pur = await adapter.execute(task_purchase)
    assert not res_pur.success
    assert res_pur.error.error_code == "PERMISSION_DENIED"


# ------------------------------------------------------------------------------
# Test 4: Verification Guard (Screenshot & OCR Required, Never Assumed)
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_skill_verification_guard_never_assumes_success():
    """
    Verify that skills never claim success when OCR does NOT confirm the goal state,
    even if browser navigation or button clicks succeeded.
    """
    mock_controller = MagicMock(spec=BrowserController)
    mock_controller.page = MagicMock()
    mock_controller.page.screenshot = AsyncMock(return_value=b"fake_image_bytes")

    # OCR returns unrelated text (e.g. blank page or random error)
    mock_ocr = MagicMock(spec=OCREngine)
    mock_ocr.extract_text = AsyncMock(
        return_value=OCRResult(
            extracted_text="404 Not Found. Service Unavailable.",
            source_artifact="screenshot.png",
            segments=[],
        )
    )

    mock_canva_ctrl = MagicMock(spec=CanvaBrowserController)
    mock_canva_ctrl.create_design = AsyncMock(
        return_value=BrowserResult(success=True, data={"editor_open": True})
    )

    skills = CanvaSkills(
        controller=mock_controller,
        canva_controller=mock_canva_ctrl,
        ocr_engine=mock_ocr,
        permission_manager=None,
    )

    # Attempt create_design with unverified OCR
    report = await skills.create_design(design_type="presentation", topic="AI Strategy")

    # Must be FAILED, not COMPLETED, because OCR did not detect editor controls
    assert not report.success
    assert report.status == "FAILED"
    assert "not recognized in screenshot/OCR" in report.stuck_reason


# ------------------------------------------------------------------------------
# Test 5: End-to-End Presentation Workflow (Clean Handoff at Sign-in Wall)
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_5_slide_presentation_clean_handoff_at_signin():
    """
    End-to-End Test: 'create a 5 slide presentation on AI in Canva'
    When signed out, must detect the sign-in wall and cleanly hand off with
    status 'WAITING_FOR_HUMAN', attaching screenshot and stuck reason.
    """
    mock_server = MockCanvaServer(mode="login")
    mock_server.start()

    temp_profile = tempfile.mkdtemp(prefix="test_canva_profile_")
    try:
        controller = BrowserController(
            permission_manager=False,
            user_data_dir=temp_profile,
        )

        mock_ocr = MagicMock(spec=OCREngine)
        mock_ocr.extract_text = AsyncMock(
            return_value=OCRResult(
                extracted_text="Welcome back. Log in to Canva. Email Password Log in",
                source_artifact="screenshot.png",
                segments=[
                    OCRTextSegment(text="Welcome back", confidence=0.98, bounding_box=OCRBoundingBox(x=50, y=50, width=100, height=20)),
                    OCRTextSegment(text="Log in to Canva", confidence=0.99, bounding_box=OCRBoundingBox(x=50, y=80, width=120, height=20)),
                ],
            )
        )

        skills = CanvaSkills(
            controller=controller,
            ocr_engine=mock_ocr,
            permission_manager=None,
        )

        # Execute open_canva targeting the login wall server
        report = await skills.open_canva(
            url=f"http://127.0.0.1:{mock_server.port}/",
            auto_handoff=True,
            workflow_id=uuid4(),
            task_id=uuid4(),
        )

        # Clean handoff check: must reach WAITING_FOR_HUMAN with screenshot attached
        assert report.status == "WAITING_FOR_HUMAN"
        assert not report.success
        assert any(term in report.stuck_reason.lower() for term in ["log in", "login", "sign-in", "sign in", "password", "authentication"])
        assert report.final_screenshot_b64 is not None

        await controller.close()

    finally:
        mock_server.stop()
        shutil.rmtree(temp_profile, ignore_errors=True)


# ------------------------------------------------------------------------------
# Test 6: End-to-End Presentation Workflow (Verified Design Editor State)
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_5_slide_presentation_verified_design():
    """
    End-to-End Test: 'create a 5 slide presentation on AI in Canva'
    When active session is authenticated, executes skills sequentially:
    open_canva -> create_design -> pick_template -> edit_text -> add_slide (x4) -> export.
    Every step is verified by OCR, reaching a fully verified 5-slide presentation deliverable.
    """
    mock_server = MockCanvaServer(mode="editor")
    mock_server.start()

    temp_profile = tempfile.mkdtemp(prefix="test_canva_profile_")
    temp_artifacts = tempfile.mkdtemp(prefix="test_canva_artifacts_")

    try:
        controller = BrowserController(
            permission_manager=False,
            user_data_dir=temp_profile,
        )

        # Mock OCR that simulates recognizing Canva editor controls and presentation text
        mock_ocr = MagicMock(spec=OCREngine)

        def mock_extract(req):
            return OCRResult(
                extracted_text="File Resize Share Present AI Presentation Overview Page 1 of 5 Add page",
                source_artifact="screenshot.png",
                segments=[
                    OCRTextSegment(text="File", confidence=0.95, bounding_box=OCRBoundingBox(x=10, y=10, width=30, height=15)),
                    OCRTextSegment(text="Share", confidence=0.95, bounding_box=OCRBoundingBox(x=100, y=10, width=40, height=15)),
                    OCRTextSegment(text="AI Presentation Overview", confidence=0.97, bounding_box=OCRBoundingBox(x=200, y=200, width=300, height=40)),
                    OCRTextSegment(text="Page 1 of 5", confidence=0.94, bounding_box=OCRBoundingBox(x=500, y=700, width=80, height=20)),
                    OCRTextSegment(text="Add page", confidence=0.96, bounding_box=OCRBoundingBox(x=600, y=700, width=70, height=20)),
                ],
            )

        mock_ocr.extract_text = AsyncMock(side_effect=mock_extract)

        # CanvaBrowserController with working export deliverable
        canva_ctrl = CanvaBrowserController(
            browser_controller=controller,
            permission_manager=None,
        )

        skills = CanvaSkills(
            controller=controller,
            canva_controller=canva_ctrl,
            ocr_engine=mock_ocr,
            artifacts_dir=temp_artifacts,
            permission_manager=None,
        )

        wf_id = uuid4()
        t_id = uuid4()

        # Step 1: Open Canva (verified dashboard/session)
        open_report = await skills.open_canva(
            url=f"http://127.0.0.1:{mock_server.port}/",
            workflow_id=wf_id,
            task_id=t_id,
        )
        assert open_report.status in ("COMPLETED", "WAITING_FOR_HUMAN")

        # Step 2: Create Presentation Design
        create_report = await skills.create_design(
            design_type="presentation",
            topic="AI",
            title="AI Presentation",
            workflow_id=wf_id,
            task_id=t_id,
        )
        assert create_report.success
        assert create_report.status == "COMPLETED"
        assert "controls verified" in create_report.what_agent_sees_now.lower()

        # Step 3: Pick & Apply Template
        template_report = await skills.pick_template(
            query="AI",
            workflow_id=wf_id,
            task_id=t_id,
        )
        assert template_report.success
        assert template_report.status == "COMPLETED"

        # Step 4: Edit Slide 1 Text
        edit_report = await skills.edit_text(
            text="AI Presentation Overview",
            workflow_id=wf_id,
            task_id=t_id,
        )
        assert edit_report.success
        assert edit_report.status == "COMPLETED"

        # Step 5: Add remaining 4 slides (reaching 5 slides total)
        for slide_no in range(2, 6):
            slide_report = await skills.add_slide(
                slide_number=slide_no,
                workflow_id=wf_id,
                task_id=t_id,
            )
            assert slide_report.success
            assert slide_report.status == "COMPLETED"

        # Step 6: Export Presentation as PDF deliverable
        export_report = await skills.export(
            format="pdf",
            workflow_id=wf_id,
            task_id=t_id,
        )
        assert export_report.success
        assert export_report.status == "COMPLETED"
        assert os.path.exists(export_report.final_screenshot_path)
        assert os.path.getsize(export_report.final_screenshot_path) > 0

        await controller.close()

    finally:
        mock_server.stop()
        shutil.rmtree(temp_profile, ignore_errors=True)
        shutil.rmtree(temp_artifacts, ignore_errors=True)


def test_canva_dimension_prompts_not_flagged_as_nonsense():
    """
    Verifies that Canva design requests with dimensions (1080×1080, 1920x1080, 1080 1080)
    are recognized as actionable goals and NOT falsely flagged as keyboard-mash nonsense.
    """
    from app.planner.llm_planner import LLMPlanner
    from shared.contracts.planner import PlannerRequest
    import json

    planner = LLMPlanner()

    dimension_prompts = [
        "create instagram post 1080×1080 in canva",
        "create instagram post 1080x1080 in canva",
        "create presentation 1920x1080 in canva",
        "create instagram post 1080 1080 in canva",
        "design a poster 1080*1920 in canva",
    ]

    for prompt in dimension_prompts:
        # 1. Must not be classified as nonsense
        assert not planner.is_nonsense(prompt), f"Prompt '{prompt}' falsely flagged as nonsense"

        # 2. Plan generation must produce a ready plan, not error
        session_id = f"test-dim-{uuid4()}"
        res = planner.plan(PlannerRequest(message=prompt, session_id=session_id), uuid4())
        assert res.status == "ready", f"Expected 'ready' status for '{prompt}', got '{res.status}': {res.reply}"
        assert res.action == "execute_plan"

        plan = json.loads(res.reply)
        task_names = [t.get("task_name") for t in plan.get("tasks", [])]
        assert any("canva" in n.lower() or "design" in n.lower() or "post" in n.lower() for n in task_names)

    # Verify that true gibberish is still properly caught
    nonsense_prompts = ["asdfghjk", "flkjsdflkjsd", "blabla random qwertyuiop"]
    for prompt in nonsense_prompts:
        assert planner.is_nonsense(prompt), f"True nonsense prompt '{prompt}' was not flagged"

