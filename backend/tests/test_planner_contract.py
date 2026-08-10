from uuid import uuid4

import pytest
from pydantic import ValidationError
from shared.contracts.planner import PlanMetadata, PlannerOutput, PlanVersion
from shared.contracts.task import Task, TaskCategory


def test_valid_planner_output():
    """Test that a well-formed PlannerOutput validates successfully."""
    task1_id = uuid4()
    task2_id = uuid4()

    t1 = Task(
        task_id=task1_id,
        workflow_id=uuid4(),
        task_name="Task 1",
        description="First task",
        required_tool="None",
        category=TaskCategory.OTHER,
        expected_output="Output 1",
    )

    t2 = Task(
        task_id=task2_id,
        workflow_id=uuid4(),
        task_name="Task 2",
        description="Second task",
        required_tool="None",
        category=TaskCategory.OTHER,
        expected_output="Output 2",
    )

    output = PlannerOutput(
        metadata=PlanMetadata(version=PlanVersion.V1_0),
        workflow_spec="Test workflow",
        tasks=[t1, t2],
        dependency_graph={task1_id: [], task2_id: [task1_id]},
        estimated_time_seconds=60,
        risks=["Low disk space"],
        required_permissions=["FILE_SYSTEM"],
    )

    assert output.metadata.version == PlanVersion.V1_0
    assert len(output.tasks) == 2
    assert output.dependency_graph[task2_id] == [task1_id]


def test_cycle_detection_in_dependency_graph():
    """Test that cycles in the dependency graph raise a validation error."""
    t1_id = uuid4()
    t2_id = uuid4()
    t3_id = uuid4()

    with pytest.raises(ValidationError, match="Cycle detected"):
        PlannerOutput(
            workflow_spec="Cycle test",
            tasks=[],
            dependency_graph={t1_id: [t2_id], t2_id: [t3_id], t3_id: [t1_id]},
        )


def test_missing_tasks_in_dependency_graph():
    """Test that a dependency graph referencing missing tasks raises an error."""
    t1_id = uuid4()
    t2_id = uuid4()

    t1 = Task(
        task_id=t1_id,
        workflow_id=uuid4(),
        task_name="Task 1",
        description="First task",
        required_tool="None",
        category=TaskCategory.OTHER,
        expected_output="Output 1",
    )

    # Intentionally missing t2 from the tasks list
    with pytest.raises(ValidationError, match="is missing from tasks list"):
        PlannerOutput(
            workflow_spec="Missing task test",
            tasks=[t1],
            dependency_graph={t2_id: [t1_id]},
        )
