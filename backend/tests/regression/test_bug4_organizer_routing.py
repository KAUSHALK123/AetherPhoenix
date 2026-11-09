"""Regression test for Bug 4: Local File Organizer intent routing and clarification."""

import json
import uuid
import pytest

from app.agents.planner.agent import PlannerAgent
from shared.contracts.planner import PlannerRequest


@pytest.fixture
def planner():
    return PlannerAgent()


@pytest.mark.parametrize(
    "query",
    [
        "Local File Organizer",
        "organize my files",
        "sort downloads",
        "clean up folder",
        "file organizer",
    ],
)
def test_organizer_prompts_file_organization_clarification(planner, query):
    """
    Assert vague file organization requests prompt file organization clarification
    (folder, organization criteria, move vs copy) and NEVER ask about PPT or slides.
    """
    session_id = f"test-clarif-{uuid.uuid4()}"
    req = PlannerRequest(message=query, session_id=session_id)
    res = planner.process_request(req)

    assert res.status == "clarifying", f"Expected 'clarifying' status for '{query}', got '{res.status}'"
    reply_lower = res.reply.lower()

    # Must ask relevant file organization questions
    assert "folder" in reply_lower, f"Clarification should ask about folder: {res.reply}"
    assert "organized" in reply_lower or "file type" in reply_lower, (
        f"Clarification should ask about organization criteria: {res.reply}"
    )
    assert "moved or copied" in reply_lower or "move" in reply_lower, (
        f"Clarification should ask about move vs copy: {res.reply}"
    )

    # Must NEVER mention presentation / PPT / slides
    forbidden = ["ppt", "pptx", "slide", "slides", "presentation", "powerpoint", "deck"]
    for word in forbidden:
        assert word not in reply_lower, (
            f"Clarification for file organization should never mention '{word}': {res.reply}"
        )


def test_organizer_preset_and_clarified_goal_decomposes_to_file_explorer_dag(planner):
    """
    Assert preset button query directly decomposes into the required 3-step file_explorer DAG:
    1. list files in source dir
    2. create target categories/folders
    3. move/copy files into destination
    And asserts NO PPT or PDF tasks exist in the DAG.
    """
    session_id = f"test-preset-{uuid.uuid4()}"
    preset_query = "Organize files in the downloads directory by file type and date"
    req = PlannerRequest(message=preset_query, session_id=session_id)
    res = planner.process_request(req)

    assert res.status == "ready", f"Expected 'ready' plan for preset query, got status '{res.status}'"

    plan_data = json.loads(res.reply)
    tasks = plan_data["tasks"]
    leaf_tasks = [t for t in tasks if t.get("task_type") == "LEAF"]

    assert len(leaf_tasks) == 3, f"Expected 3 leaf tasks, got {len(leaf_tasks)}"

    task_names = [t["task_name"] for t in leaf_tasks]
    assert task_names[0] == "List files in source dir"
    assert task_names[1] == "Create target categories/folders"
    assert task_names[2] == "Move/copy files into destination"

    for t in leaf_tasks:
        assert t["required_tool"] == "file_explorer", (
            f"Expected leaf task to use 'file_explorer', got '{t.get('required_tool')}'"
        )
        assert t["category"] == "FILE_SYSTEM", (
            f"Expected task category 'FILE_SYSTEM', got '{t.get('category')}'"
        )

        name_lower = t["task_name"].lower()
        desc_lower = t["description"].lower()
        for forbidden in ["ppt", "pptx", "slide", "slides", "presentation", "pdf"]:
            assert forbidden not in name_lower, f"Forbidden '{forbidden}' in task name: {t['task_name']}"
            assert forbidden not in desc_lower, f"Forbidden '{forbidden}' in task desc: {t['description']}"


def test_multiturn_clarification_flow(planner):
    """
    Test two-turn conversation:
    Turn 1: vague request -> clarifying
    Turn 2: user clarifies folder and criteria -> ready plan with file_explorer DAG
    """
    session_id = f"test-multiturn-{uuid.uuid4()}"

    # Turn 1
    req1 = PlannerRequest(message="organize my files", session_id=session_id)
    res1 = planner.process_request(req1)
    assert res1.status == "clarifying"

    # Turn 2
    req2 = PlannerRequest(
        message="In Downloads folder, sort by file type, move files",
        session_id=session_id,
    )
    res2 = planner.process_request(req2)
    assert res2.status == "ready", f"Expected plan ready after clarification, got '{res2.status}': {res2.reply}"

    plan_data = json.loads(res2.reply)
    leaf_tasks = [t for t in plan_data["tasks"] if t.get("task_type") == "LEAF"]
    assert len(leaf_tasks) == 3
    for t in leaf_tasks:
        assert t["required_tool"] == "file_explorer"

