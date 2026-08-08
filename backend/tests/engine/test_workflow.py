from uuid import uuid4

import pytest
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.engine.workflow import WorkflowEngine


@pytest.fixture
def state():
    metadata = WorkflowMetadata(goal="Test Workflow")
    return SharedWorkflowState(metadata=metadata)


@pytest.fixture
def engine(state):
    return WorkflowEngine(state)


def test_start_workflow_success(engine, state):
    assert state.metadata.status == WorkflowStatus.CREATED
    engine.start()
    assert state.metadata.status == WorkflowStatus.RUNNING


def test_pause_workflow(engine, state):
    engine.start()
    engine.pause()
    assert state.metadata.status == WorkflowStatus.PAUSED


def test_invalid_start_transition(engine, state):
    engine.start()
    engine.complete()
    with pytest.raises(ValueError, match="Cannot start workflow from status"):
        engine.start()


def test_invalid_pause_transition(engine, state):
    with pytest.raises(ValueError, match="Only RUNNING workflows can be paused"):
        engine.pause()


def test_cancel_complete_fail(engine, state):
    engine.cancel()
    assert state.metadata.status == WorkflowStatus.CANCELLED

    engine.complete()
    assert state.metadata.status == WorkflowStatus.COMPLETED

    engine.fail()
    assert state.metadata.status == WorkflowStatus.FAILED


def create_dummy_task(name: str) -> Task:
    from shared.contracts.task import TaskCategory

    return Task(
        workflow_id=uuid4(),
        task_name=name,
        description=f"Description for {name}",
        required_tool="dummy_tool",
        category=TaskCategory.OTHER,
        expected_output="dummy output",
    )


def test_enqueue_dequeue_task(engine, state):
    task = create_dummy_task("A sample task")
    engine.enqueue(task)

    assert task.status == TaskStatus.WAITING
    assert task.task_id in state.tasks
    assert state.execution_queue == [task.task_id]

    popped = engine.dequeue()
    assert popped is not None
    assert popped.task_id == task.task_id
    assert len(state.execution_queue) == 0


def test_update_task_status(engine, state):
    task = create_dummy_task("Status test")
    engine.enqueue(task)

    # Running
    engine.update_task_status(task.task_id, TaskStatus.RUNNING)
    assert task.status == TaskStatus.RUNNING
    assert task.task_id in state.running_tasks

    # Completed
    engine.update_task_status(task.task_id, TaskStatus.COMPLETED)
    assert task.status == TaskStatus.COMPLETED
    assert task.task_id not in state.running_tasks
    assert task.task_id in state.completed_tasks

    # Failed
    task2 = create_dummy_task("Fail test")
    engine.enqueue(task2)
    engine.update_task_status(task2.task_id, TaskStatus.RUNNING)
    engine.update_task_status(task2.task_id, TaskStatus.FAILED)

    assert task2.status == TaskStatus.FAILED
    assert task2.task_id not in state.running_tasks
    assert task2.task_id in state.failed_tasks


def test_update_missing_task_status(engine):
    with pytest.raises(ValueError, match="Task .* not found"):
        engine.update_task_status(uuid4(), TaskStatus.RUNNING)
