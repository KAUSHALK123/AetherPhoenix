"""Regression tests for planner intelligence fixes."""

import json
import uuid
import pytest
from unittest.mock import MagicMock

from app.agents.planner.agent import PlannerAgent
from shared.contracts.planner import PlannerRequest
from shared.contracts.task import TaskType


@pytest.fixture
def planner():
    return PlannerAgent()


def test_what_folders_are_in_d_drive_routes_to_file_explorer_no_ppt(planner):
    """
    Test 1: 'can u tell me what folders are in d drive'
    Must produce a real list-directory task with file_explorer.
    Must NOT trigger clarification and NEVER mention PPT or slides.
    """
    session_id = f"test-d-drive-{uuid.uuid4()}"
    req = PlannerRequest(
        message="can u tell me what folders are in d drive",
        session_id=session_id,
    )
    res = planner.process_request(req)

    # Must be ready (not clarifying or error)
    assert res.status == "ready", f"Expected 'ready' status, got '{res.status}': {res.reply}"
    assert res.reply is not None

    plan = json.loads(res.reply)
    tasks = plan.get("tasks", [])
    leaf_tasks = [t for t in tasks if t.get("task_type") == TaskType.LEAF.value or t.get("task_type") == "LEAF"]

    assert len(leaf_tasks) >= 1, "Expected at least 1 leaf task"
    target_task = leaf_tasks[0]
    assert target_task.get("required_tool") == "file_explorer", (
        f"Expected required_tool to be 'file_explorer', got '{target_task.get('required_tool')}'"
    )
    assert target_task.get("inputs", {}).get("action") == "list_files"
    assert "D:" in target_task.get("inputs", {}).get("path", "")

    # Never mention presentation or PPT
    reply_lower = res.reply.lower()
    for forbidden in ["ppt", "pptx", "slide", "slides", "presentation", "powerpoint"]:
        assert forbidden not in reply_lower, f"Forbidden '{forbidden}' found in reply: {res.reply}"


def test_check_d_drive_produces_real_task_not_placeholder_plan(planner):
    """
    Test 2: 'check d drive'
    Must NOT generate the generic 3-phase placeholder plan ('Evaluate Goal Context', 'Execute Primary Action').
    Must call real tool file_explorer.
    """
    session_id = f"test-check-d-{uuid.uuid4()}"
    req = PlannerRequest(
        message="check d drive",
        session_id=session_id,
    )
    res = planner.process_request(req)

    assert res.status == "ready", f"Expected 'ready' status, got '{res.status}': {res.reply}"
    plan = json.loads(res.reply)
    tasks = plan.get("tasks", [])
    task_names = [t.get("task_name") for t in tasks]

    # Prohibited placeholder tasks
    assert "Evaluate Goal Context" not in task_names, "Generic placeholder task 'Evaluate Goal Context' detected"
    assert "Execute Primary Action" not in task_names, "Generic placeholder task 'Execute Primary Action' detected"

    leaf_tasks = [t for t in tasks if t.get("task_type") == "LEAF" or t.get("task_type") == TaskType.LEAF.value]
    assert len(leaf_tasks) >= 1
    for t in leaf_tasks:
        assert t.get("required_tool") != "", "Found leaf task with empty required_tool"
        assert t.get("required_tool") == "file_explorer"


def test_nonsense_request_returns_honest_cant_do_this_response(planner):
    """
    Test 3: Nonsense request -> honest 'can't do this' response.
    Never emit a placeholder plan and never ask for clarification on gibberish.
    """
    nonsense_queries = [
        "asdfghjk",
        "flkjsdflkjsd",
        "blabla random qwertyuiop",
    ]
    for query in nonsense_queries:
        session_id = f"test-nonsense-{uuid.uuid4()}"
        req = PlannerRequest(message=query, session_id=session_id)
        res = planner.process_request(req)

        # Must report error / unable to fulfill, NOT ready with placeholder plan
        assert res.status == "error", f"Expected status 'error' for nonsense query '{query}', got '{res.status}'"
        assert "cannot fulfill" in res.reply.lower() or "unable" in res.reply.lower() or "not" in res.reply.lower()


def test_make_a_5_slide_ppt_routes_to_ppt(planner):
    """
    Test 4: 'make a 5 slide ppt on X' -> PPT.
    """
    session_id = f"test-ppt-{uuid.uuid4()}"
    req = PlannerRequest(
        message="make a 5 slide ppt on quantum computing",
        session_id=session_id,
    )
    res = planner.process_request(req)

    assert res.status == "ready", f"Expected 'ready' status, got '{res.status}': {res.reply}"
    plan = json.loads(res.reply)
    tasks = plan.get("tasks", [])

    # PPT tasks present
    ppt_tasks = [t for t in tasks if "ppt" in t.get("task_name", "").lower() or t.get("required_tool") in ("ppt_generator", "ppt_tool")]
    assert len(ppt_tasks) >= 1, "Expected at least 1 PPT-related task"


def test_conversational_chat_answered_directly_without_workflow(planner):
    """
    Test 5: Pure question / chat -> answered directly without creating workflow.
    """
    chat_queries = [
        "what can you do?",
        "how does this work?",
        "who are you?",
    ]
    for query in chat_queries:
        session_id = f"test-chat-{uuid.uuid4()}"
        req = PlannerRequest(message=query, session_id=session_id)
        res = planner.process_request(req)

        assert res.status == "chat", f"Expected status 'chat' for '{query}', got '{res.status}'"
        assert res.action == "reply"
        assert "AetherPhoenix" in res.reply or "assistant" in res.reply.lower()


@pytest.mark.asyncio
async def test_file_explorer_out_of_sandbox_requests_permission_modal():
    """
    Test 6: File access outside workspace/artifacts prompts PermissionManager.
    If denied or not granted, raises PermissionDeniedException without blowing up.
    """
    from app.core.exceptions import PermissionDeniedException
    from app.tools.file_explorer.executor import FileExplorerExecutor
    from app.core.permissions.manager import PermissionManager

    mock_pm = MagicMock(spec=PermissionManager)
    # Mock check_permission returning False (denied)
    mock_pm.check_permission.return_value = False
    mock_pm.requests = {}

    executor = FileExplorerExecutor(permission_manager=mock_pm)

    # Attempting to list outside sandbox (e.g. D:\outside) should prompt check_permission
    with pytest.raises(PermissionDeniedException) as exc_info:
        await executor.list_files(path="D:\\outside_sandbox_dir", workflow_id="wf-1", task_id="t-1")

    assert "Access denied" in str(exc_info.value)
    mock_pm.check_permission.assert_called_once()
