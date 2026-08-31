from uuid import uuid4

import pytest
from shared.contracts.planner import TaskDecompositionPlan
from shared.contracts.task import Task, TaskCategory, TaskStatus

from app.planner.decomposer import TaskDecompositionEngine


@pytest.fixture
def decomposer():
    return TaskDecompositionEngine()


def test_decompose_presentation_goal(decomposer):
    workflow_id = uuid4()
    goal = "Create a PowerPoint presentation on AI Desktop Assistant"

    plan = decomposer.decompose_goal(goal=goal, workflow_id=workflow_id)

    assert isinstance(plan, TaskDecompositionPlan)
    assert plan.workflow_id == workflow_id
    assert plan.goal == goal
    assert len(plan.tasks) == 6
    assert len(plan.execution_order) == 6

    # Verify root tasks exist (parent_task_id is None)
    root_tasks = [t for t in plan.tasks if t.parent_task_id is None]
    assert len(root_tasks) == 2

    for t in plan.tasks:
        assert t.status == TaskStatus.CREATED
        assert t.required_tool == ""


def test_decompose_research_goal(decomposer):
    workflow_id = uuid4()
    goal = "Research recent advancements in Quantum Computing"

    plan = decomposer.decompose_goal(goal=goal, workflow_id=workflow_id)

    assert len(plan.tasks) == 4
    assert plan.tasks[0].category == TaskCategory.WEB_RESEARCH

    # Verify order: search -> extract -> synthesize
    task_names = [
        t.task_name
        for t in decomposer.get_ordered_execution_plan(plan.tasks)
        if t.parent_task_id
    ]
    assert "Execute Web Search" in task_names
    assert "Extract Content Details" in task_names
    assert "Synthesize Research Report" in task_names


def test_decompose_coding_goal(decomposer):
    workflow_id = uuid4()
    goal = "Build a FastAPI web app with database integration"

    plan = decomposer.decompose_goal(goal=goal, workflow_id=workflow_id)

    assert len(plan.tasks) == 4
    assert plan.tasks[0].category == TaskCategory.CODE_GENERATION


def test_decompose_system_goal(decomposer):
    workflow_id = uuid4()
    goal = "Fix Windows wifi driver configuration"

    plan = decomposer.decompose_goal(goal=goal, workflow_id=workflow_id)

    assert len(plan.tasks) == 3
    assert plan.tasks[0].category == TaskCategory.POWERSHELL


def test_decompose_generic_goal(decomposer):
    workflow_id = uuid4()
    goal = "Organize my workspace documents"

    plan = decomposer.decompose_goal(goal=goal, workflow_id=workflow_id)

    assert len(plan.tasks) == 4
    assert plan.tasks[0].category == TaskCategory.FILE_SYSTEM


def test_task_hierarchy(decomposer):
    workflow_id = uuid4()
    tasks = decomposer._decompose_generic_goal("Sample task", workflow_id)

    hierarchy = decomposer.build_task_hierarchy(tasks)

    # Root tasks under None
    assert None in hierarchy
    assert len(hierarchy[None]) == 1

    root_id = hierarchy[None][0].task_id
    assert root_id in hierarchy
    assert len(hierarchy[root_id]) == 2


def test_dependency_mapping(decomposer):
    workflow_id = uuid4()
    tasks = decomposer._decompose_generic_goal("Sample task", workflow_id)

    dep_graph = decomposer.build_dependency_graph(tasks)

    assert len(dep_graph) == 3
    # Subtask 2 depends on Subtask 1
    subtask_run = tasks[2]
    subtask_analyze = tasks[1]
    assert subtask_analyze.task_id in dep_graph[subtask_run.task_id]


def test_topological_sort_ordered_plan(decomposer):
    workflow_id = uuid4()
    tasks = decomposer._decompose_presentation_goal("Create slides", workflow_id)

    ordered = decomposer.get_ordered_execution_plan(tasks)
    assert len(ordered) == len(tasks)

    # Verify that for every task, its dependencies appear BEFORE it in the ordered plan
    seen_ids = set()
    for task in ordered:
        for dep_id in task.dependencies:
            assert (
                dep_id in seen_ids
            ), f"Dependency {dep_id} must precede task {task.task_id}"
        seen_ids.add(task.task_id)


def test_circular_dependency_detection(decomposer):
    workflow_id = uuid4()

    t1 = Task(
        workflow_id=workflow_id,
        task_name="Task 1",
        description="First task",
        required_tool="",
        category=TaskCategory.OTHER,
        expected_output="Result 1",
        status=TaskStatus.CREATED,
    )
    t2 = Task(
        workflow_id=workflow_id,
        task_name="Task 2",
        description="Second task",
        required_tool="",
        category=TaskCategory.OTHER,
        expected_output="Result 2",
        dependencies=[t1.task_id],
        status=TaskStatus.CREATED,
    )
    # Create circular dependency: t1 depends on t2
    t1.dependencies = [t2.task_id]

    with pytest.raises(ValueError, match="Circular dependency detected"):
        decomposer.validate_dag([t1, t2])

    with pytest.raises(ValueError, match="Circular dependency detected"):
        decomposer.get_ordered_execution_plan([t1, t2])


def test_no_task_execution_or_tool_assignment(decomposer):
    workflow_id = uuid4()
    plan = decomposer.decompose_goal("Research modern AI architecture", workflow_id)

    for task in plan.tasks:
        # Constraint: Do NOT execute tasks
        assert task.status == TaskStatus.CREATED
        # Constraint: Do NOT assign tools
        assert task.required_tool == ""
