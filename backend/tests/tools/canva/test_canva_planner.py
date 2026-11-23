from uuid import uuid4

import pytest
from shared.contracts.planner import PlannerRequest, UserRequirement
from shared.contracts.task import TaskCategory

from app.planner.clarifier import ClarificationEngine
from app.planner.decomposer import TaskDecompositionEngine
from app.planner.llm_planner import LLMPlanner, get_default_tool_registry


@pytest.fixture
def decomposer():
    return TaskDecompositionEngine()


@pytest.fixture
def clarifier():
    return ClarificationEngine()


# =========================================================================
# MANDATORY TEST SCENARIOS
# =========================================================================


def test_scenario_open_canva(decomposer):
    """Scenario 1: 'Open Canva' -> Canva opens in live browser."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Open Canva", workflow_id)
    tasks = plan.tasks

    assert len(tasks) >= 2
    leaf_tasks = [t for t in tasks if t.task_type.value == "LEAF"]
    assert len(leaf_tasks) >= 1

    canva_task = leaf_tasks[0]
    assert canva_task.required_tool == "canva_tool"
    assert canva_task.category == TaskCategory.BROWSER
    assert canva_task.inputs["action"] == "open_canva"
    assert "canva.com" in canva_task.inputs["url"]


def test_scenario_create_instagram_post(decomposer):
    """Scenario 2: 'Create Instagram post 1080 × 1080' -> Correct dimensions."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Create Instagram post 1080 × 1080", workflow_id)
    tasks = plan.tasks

    leaf_tasks = [t for t in tasks if t.task_type.value == "LEAF"]
    assert len(leaf_tasks) >= 1

    create_task = leaf_tasks[0]
    assert create_task.required_tool == "canva_tool"
    assert create_task.inputs["action"] == "create_design"
    assert create_task.inputs["design_type"] == "instagram_post"
    assert create_task.inputs["width"] == 1080
    assert create_task.inputs["height"] == 1080
    assert create_task.inputs["unit"] == "px"


def test_scenario_create_college_fest_poster(decomposer):
    """Scenario 3: 'Create college fest poster' -> Actual Canva design created."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Create college fest poster", workflow_id)
    tasks = plan.tasks

    leaf_tasks = [t for t in tasks if t.task_type.value == "LEAF"]
    assert len(leaf_tasks) >= 1

    poster_task = leaf_tasks[0]
    assert poster_task.required_tool == "canva_tool"
    assert poster_task.inputs["action"] == "create_design"
    assert poster_task.inputs["design_type"] == "poster"
    assert "College Fest" in poster_task.inputs["topic"]
    assert poster_task.inputs["width"] == 1080
    assert poster_task.inputs["height"] == 1920


def test_scenario_create_presentation(decomposer):
    """Scenario 4: 'Create presentation' -> Canva presentation editor opens."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Create presentation", workflow_id)
    tasks = plan.tasks

    leaf_tasks = [t for t in tasks if t.task_type.value == "LEAF"]
    assert len(leaf_tasks) >= 1

    pres_task = leaf_tasks[0]
    assert pres_task.required_tool == "canva_tool"
    assert pres_task.inputs["action"] == "create_design"
    assert pres_task.inputs["design_type"] == "presentation"
    assert pres_task.inputs["width"] == 1920
    assert pres_task.inputs["height"] == 1080


def test_scenario_edit_existing_design(decomposer):
    """Scenario 5: 'Edit existing design' -> Correct design is modified."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Edit existing design", workflow_id)
    tasks = plan.tasks

    leaf_tasks = [t for t in tasks if t.task_type.value == "LEAF"]
    assert len(leaf_tasks) >= 1

    edit_task = leaf_tasks[0]
    assert edit_task.required_tool == "canva_tool"
    assert edit_task.inputs["action"] == "edit_design"
    assert "canva.com/design" in edit_task.inputs["design_url"]


def test_scenario_export_as_pdf(decomposer):
    """Scenario 6: 'Export as PDF' -> Valid downloadable PDF."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Export as PDF", workflow_id)
    tasks = plan.tasks

    leaf_tasks = [t for t in tasks if t.task_type.value == "LEAF"]
    assert len(leaf_tasks) >= 1

    export_task = leaf_tasks[0]
    assert export_task.required_tool == "canva_tool"
    assert export_task.inputs["action"] == "export_design"
    assert export_task.inputs["format"] == "pdf"


# =========================================================================
# GENERAL LANGUAGE TEST (Misspellings, Informal, Rearranged)
# =========================================================================


@pytest.mark.parametrize(
    "query,expected_type,expected_w,expected_h",
    [
        ("opn canva", None, None, None),  # Open Canva variation
        ("creat instagram pst 1080x1080", "instagram_post", 1080, 1080),  # Misspelling
        ("desing a colledge fest postr", "poster", 1080, 1920),  # Misspelling
        (
            "hey make an instagram post 1080 x 1080 please",
            "instagram_post",
            1080,
            1080,
        ),  # Informal
        (
            "1080 x 1080 instagram post please create",
            "instagram_post",
            1080,
            1080,
        ),  # Rearranged
        ("canva presentation", "presentation", 1920, 1080),  # Short instruction
        ("youtube thumbnail 1280x720", "youtube_thumbnail", 1280, 720),  # Thumbnail
    ],
)
def test_general_language_variations(
    decomposer, query, expected_type, expected_w, expected_h
):
    workflow_id = uuid4()
    plan = decomposer.decompose_goal(query, workflow_id)
    tasks = plan.tasks
    assert len(tasks) >= 2

    leaf_tasks = [t for t in tasks if t.task_type.value == "LEAF"]
    assert len(leaf_tasks) >= 1
    canva_task = leaf_tasks[0]

    assert canva_task.required_tool == "canva_tool"
    if expected_type:
        assert canva_task.inputs["design_type"] == expected_type
        assert canva_task.inputs["width"] == expected_w
        assert canva_task.inputs["height"] == expected_h


# =========================================================================
# CLARIFICATION ENGINE EVALUATION
# =========================================================================


def test_clarification_not_needed_for_specified_canva_requests(clarifier):
    """Specific Canva requests with dimensions or types should NOT trigger clarification."""
    for req_text in [
        "Open Canva",
        "Create Instagram post 1080 × 1080",
        "Create college fest poster",
        "Create presentation",
        "Edit existing design",
        "Export as PDF",
    ]:
        req = UserRequirement(requirements=[req_text])
        result = clarifier.evaluate_requirement(req)
        assert (
            result.needs_clarification is False
        ), f"Unexpected clarification for: {req_text}"


def test_clarification_triggered_for_vague_canva_request(clarifier):
    """Vague Canva request without topic or design type should ask for clarification."""
    req = UserRequirement(requirements=["canva"])
    result = clarifier.evaluate_requirement(req)
    assert result.needs_clarification is True
    assert "canva_design_type" in result.missing_fields
    assert result.options is not None
    assert "Instagram Post (1080x1080)" in result.options


# =========================================================================
# LLM PLANNER CATALOG TEST
# =========================================================================


def test_llm_planner_catalog_canva():
    registry = get_default_tool_registry()
    assert registry.get("canva_tool") is not None

    planner = LLMPlanner(tool_registry=registry)
    req = PlannerRequest(
        message="Create college fest poster", session_id="test-session"
    )
    res = planner.plan(req, workflow_id=uuid4())

    assert res.status == "ready"
    assert res.action == "execute_plan"
    assert "canva_tool" in res.reply
