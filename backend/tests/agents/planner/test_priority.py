import uuid

import pytest
from shared.contracts import Task, TaskCategory, TaskPriority

from app.agents.planner.priority_engine import PriorityAssignmentEngine


def create_task(
    priority: TaskPriority = TaskPriority.MEDIUM,
    risk_level: str = "LOW",
    dependencies: list = None,
) -> Task:
    return Task(
        workflow_id=uuid.uuid4(),
        task_name="Test Task",
        description="A test task",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        priority=priority,
        risk_level=risk_level,
        expected_output="Success",
        dependencies=dependencies or [],
    )


def test_independent_tasks_ordered_by_priority():
    engine = PriorityAssignmentEngine()

    t_low = create_task(priority=TaskPriority.LOW)
    t_med = create_task(priority=TaskPriority.MEDIUM)
    t_high = create_task(priority=TaskPriority.HIGH)
    t_crit = create_task(priority=TaskPriority.CRITICAL)

    # Initial order is scrambled
    tasks = [t_low, t_crit, t_med, t_high]
    ordered_tasks = engine.assign_priorities(tasks)

    assert len(ordered_tasks) == 4
    assert ordered_tasks[0].task_id == t_crit.task_id
    assert ordered_tasks[1].task_id == t_high.task_id
    assert ordered_tasks[2].task_id == t_med.task_id
    assert ordered_tasks[3].task_id == t_low.task_id


def test_dependency_ordering():
    engine = PriorityAssignmentEngine()

    t_parent = create_task(priority=TaskPriority.MEDIUM)
    t_child1 = create_task(
        priority=TaskPriority.MEDIUM, dependencies=[t_parent.task_id]
    )
    t_child2 = create_task(
        priority=TaskPriority.MEDIUM, dependencies=[t_parent.task_id]
    )
    t_grandchild = create_task(
        priority=TaskPriority.MEDIUM, dependencies=[t_child1.task_id, t_child2.task_id]
    )

    tasks = [t_grandchild, t_child2, t_parent, t_child1]
    ordered_tasks = engine.assign_priorities(tasks)

    # Parent must be first
    assert ordered_tasks[0].task_id == t_parent.task_id
    # Grandchild must be last
    assert ordered_tasks[3].task_id == t_grandchild.task_id
    # Child1 and Child2 must be in between
    assert ordered_tasks[1].task_id in [t_child1.task_id, t_child2.task_id]
    assert ordered_tasks[2].task_id in [t_child1.task_id, t_child2.task_id]


def test_priority_propagation():
    engine = PriorityAssignmentEngine()

    # t_parent is LOW priority
    t_parent = create_task(priority=TaskPriority.LOW)

    # t_child is CRITICAL priority and depends on t_parent
    t_child = create_task(
        priority=TaskPriority.CRITICAL, dependencies=[t_parent.task_id]
    )

    tasks = [t_child, t_parent]
    ordered_tasks = engine.assign_priorities(tasks)

    # t_parent should be upgraded to CRITICAL because t_child is CRITICAL
    assert ordered_tasks[0].task_id == t_parent.task_id
    assert ordered_tasks[0].priority == TaskPriority.CRITICAL

    assert ordered_tasks[1].task_id == t_child.task_id
    assert ordered_tasks[1].priority == TaskPriority.CRITICAL


def test_priority_propagation_chain():
    engine = PriorityAssignmentEngine()

    t1 = create_task(priority=TaskPriority.LOW)
    t2 = create_task(priority=TaskPriority.LOW, dependencies=[t1.task_id])
    t3 = create_task(priority=TaskPriority.HIGH, dependencies=[t2.task_id])

    tasks = [t3, t2, t1]
    ordered_tasks = engine.assign_priorities(tasks)

    # Both t1 and t2 should be upgraded to HIGH
    assert ordered_tasks[0].task_id == t1.task_id
    assert ordered_tasks[0].priority == TaskPriority.HIGH

    assert ordered_tasks[1].task_id == t2.task_id
    assert ordered_tasks[1].priority == TaskPriority.HIGH

    assert ordered_tasks[2].task_id == t3.task_id
    assert ordered_tasks[2].priority == TaskPriority.HIGH


def test_cycle_detection():
    engine = PriorityAssignmentEngine()

    t1 = create_task()
    t2 = create_task(dependencies=[t1.task_id])
    t3 = create_task(dependencies=[t2.task_id])

    # Create a cycle
    t1.dependencies.append(t3.task_id)

    tasks = [t1, t2, t3]

    with pytest.raises(ValueError, match="Dependency cycle detected among tasks."):
        engine.assign_priorities(tasks)


def test_empty_tasks():
    engine = PriorityAssignmentEngine()
    assert engine.assign_priorities([]) == []


def test_deterministic_ordering_with_tie():
    engine = PriorityAssignmentEngine()

    t1 = create_task(priority=TaskPriority.MEDIUM)
    t2 = create_task(priority=TaskPriority.MEDIUM)
    t3 = create_task(priority=TaskPriority.MEDIUM)

    # All have same priority and no dependencies, so ordered by UUID string
    tasks = [t1, t2, t3]
    ordered_tasks = engine.assign_priorities(tasks)

    sorted_ids = sorted([str(t.task_id) for t in tasks])
    assert str(ordered_tasks[0].task_id) == sorted_ids[0]
    assert str(ordered_tasks[1].task_id) == sorted_ids[1]
    assert str(ordered_tasks[2].task_id) == sorted_ids[2]
