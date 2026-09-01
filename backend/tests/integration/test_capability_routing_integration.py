from uuid import uuid4
import pytest
import json

from shared.contracts.planner import PlannerRequest
from shared.contracts.task import TaskCategory
from app.agents.planner.agent import PlannerAgent
from app.planner.decomposer import TaskDecompositionEngine


@pytest.fixture
def planner_agent():
    return PlannerAgent()


@pytest.fixture
def decomposer():
    return TaskDecompositionEngine()


def test_routing_ipconfig(decomposer, planner_agent):
    """TEST 2: 'Run ipconfig on my laptop.' must route to terminal_tool / POWERSHELL."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Run ipconfig on my laptop.", workflow_id)
    assert len(plan.tasks) >= 2
    leaf_tasks = [t for t in plan.tasks if t.required_tool]
    assert len(leaf_tasks) > 0
    assert leaf_tasks[0].required_tool == "terminal_tool"
    assert leaf_tasks[0].category == TaskCategory.POWERSHELL

    req = PlannerRequest(session_id=str(workflow_id), message="Run ipconfig on my laptop.", context={})
    res = planner_agent.process_request(req)
    assert res.status == "ready"
    reply_data = json.loads(res.reply)
    assert any(t["required_tool"] == "terminal_tool" for t in reply_data["tasks"])


def test_routing_open_notepad(decomposer, planner_agent):
    """TEST 3: 'Open Notepad.' must route to desktop_automation / DESKTOP."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Open Notepad.", workflow_id)
    assert len(plan.tasks) >= 2
    leaf_tasks = [t for t in plan.tasks if t.required_tool]
    assert len(leaf_tasks) > 0
    assert leaf_tasks[0].required_tool == "desktop_automation"
    assert leaf_tasks[0].category == TaskCategory.DESKTOP
    assert leaf_tasks[0].inputs.get("action") == "launch_app"
    assert leaf_tasks[0].inputs.get("app_name") == "notepad"

    req = PlannerRequest(session_id=str(workflow_id), message="Open Notepad.", context={})
    res = planner_agent.process_request(req)
    assert res.status == "ready"
    reply_data = json.loads(res.reply)
    assert any(t["required_tool"] == "desktop_automation" for t in reply_data["tasks"])


def test_routing_open_downloads(decomposer, planner_agent):
    """TEST 4: 'Open my Downloads folder.' must route to file_explorer / FILE_SYSTEM."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Open my Downloads folder.", workflow_id)
    assert len(plan.tasks) >= 2
    leaf_tasks = [t for t in plan.tasks if t.required_tool]
    assert len(leaf_tasks) > 0
    assert leaf_tasks[0].required_tool == "file_explorer"
    assert leaf_tasks[0].category == TaskCategory.FILE_SYSTEM

    req = PlannerRequest(session_id=str(workflow_id), message="Open my Downloads folder.", context={})
    res = planner_agent.process_request(req)
    assert res.status == "ready"
    reply_data = json.loads(res.reply)
    assert any(t["required_tool"] == "file_explorer" for t in reply_data["tasks"])


def test_routing_open_vscode(decomposer, planner_agent):
    """TEST 5: 'Open VS Code.' must route to desktop_automation / DESKTOP with app_name='code'."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Open VS Code.", workflow_id)
    assert len(plan.tasks) >= 2
    leaf_tasks = [t for t in plan.tasks if t.required_tool]
    assert len(leaf_tasks) > 0
    assert leaf_tasks[0].required_tool == "desktop_automation"
    assert leaf_tasks[0].inputs.get("app_name") == "code"


def test_routing_ppt_generation(decomposer, planner_agent):
    """TEST 1: 'Create a 5-slide PPT about electric vehicles.' must route to ppt_tool / PPT_GENERATION."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Create a 5-slide PPT about electric vehicles.", workflow_id)
    assert len(plan.tasks) >= 2
    leaf_tasks = [t for t in plan.tasks if t.category == TaskCategory.PPT_GENERATION and t.required_tool]
    assert len(leaf_tasks) > 0
    assert leaf_tasks[0].required_tool == "ppt_tool"


def test_routing_ocr_extraction(decomposer, planner_agent):
    """TEST 7: 'Extract the text from this uploaded image.' must route to ocr / OCR."""
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Extract the text from this uploaded image.", workflow_id)
    assert len(plan.tasks) >= 2
    leaf_tasks = [t for t in plan.tasks if t.category == TaskCategory.OCR and t.required_tool]
    assert len(leaf_tasks) > 0
    assert leaf_tasks[0].required_tool == "ocr"
