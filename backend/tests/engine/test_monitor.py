from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.engine.monitor import WorkflowProgressMonitor


@pytest.fixture
def monitor():
    return WorkflowProgressMonitor()


@pytest.fixture
def state():
    metadata = WorkflowMetadata(
        goal="Test Goal",
        started_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    return SharedWorkflowState(metadata=metadata)


def create_task(status: TaskStatus) -> Task:
    return Task(
        workflow_id=uuid4(),
        task_name="Task",
        description="Task description",
        required_tool="dummy",
        category=TaskCategory.OTHER,
        expected_output="dummy output",
        status=status,
    )


def test_calculate_progress_empty(monitor, state):
    progress = monitor.calculate_progress(state)
    assert progress.total_tasks == 0
    assert progress.completed_tasks == 0
    assert progress.running_tasks == 0
    assert progress.failed_tasks == 0
    assert progress.pending_tasks == 0
    assert progress.blocked_tasks == 0
    assert progress.overall_percentage == 0.0
    assert progress.estimated_remaining_time_seconds is None


def test_calculate_progress_multiple_states(monitor, state):
    t1 = create_task(TaskStatus.COMPLETED)
    t2 = create_task(TaskStatus.COMPLETED)
    t3 = create_task(TaskStatus.RUNNING)
    t4 = create_task(TaskStatus.FAILED)
    t5 = create_task(TaskStatus.BLOCKED)
    t6 = create_task(TaskStatus.CREATED)
    t7 = create_task(TaskStatus.WAITING)

    state.tasks = {
        t1.task_id: t1,
        t2.task_id: t2,
        t3.task_id: t3,
        t4.task_id: t4,
        t5.task_id: t5,
        t6.task_id: t6,
        t7.task_id: t7,
    }

    progress = monitor.calculate_progress(state)
    assert progress.total_tasks == 7
    assert progress.completed_tasks == 2
    assert progress.running_tasks == 1
    assert progress.failed_tasks == 1
    assert progress.blocked_tasks == 1
    assert progress.pending_tasks == 2
    assert abs(progress.overall_percentage - 28.57) < 0.1
    assert progress.execution_duration_seconds >= 10.0
    assert progress.estimated_remaining_time_seconds is not None
    assert progress.estimated_remaining_time_seconds > 0


def test_calculate_duration_not_started(monitor, state):
    state.metadata.started_at = None
    assert monitor.calculate_duration(state) == 0.0


def test_calculate_duration_completed(monitor, state):
    state.metadata.started_at = datetime.now(timezone.utc) - timedelta(seconds=20)
    state.metadata.completed_at = state.metadata.started_at + timedelta(seconds=15)
    assert monitor.calculate_duration(state) == 15.0


def test_update_progress_state(monitor, state):
    t1 = create_task(TaskStatus.COMPLETED)
    state.tasks = {t1.task_id: t1}

    monitor.update_progress_state(state)
    assert state.progress.total_tasks == 1
    assert state.progress.completed_tasks == 1
    assert state.progress.overall_percentage == 100.0
