from uuid import uuid4

import pytest
from shared.contracts.planner import PlannerOutput
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.agents.supervisor.agent import SupervisorAgent
from app.engine.monitor import WorkflowProgressMonitor
from app.engine.parallel_monitor import ParallelTaskMonitor


@pytest.fixture
def monitor():
    return ParallelTaskMonitor()


@pytest.fixture
def progress_monitor():
    return WorkflowProgressMonitor()


@pytest.fixture
def supervisor():
    return SupervisorAgent()


@pytest.fixture
def base_state():
    metadata = WorkflowMetadata(goal="Parallel Monitoring Test")
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


def test_parallel_group_all_succeed(monitor, base_state):
    # Setup 3 parallel tasks and a downstream task
    t1 = create_task(TaskStatus.COMPLETED)
    t2 = create_task(TaskStatus.COMPLETED)
    t3 = create_task(TaskStatus.COMPLETED)
    t_downstream = create_task(TaskStatus.WAITING)

    base_state.tasks = {
        t1.task_id: t1,
        t2.task_id: t2,
        t3.task_id: t3,
        t_downstream.task_id: t_downstream,
    }

    base_state.planner_output = PlannerOutput(
        workflow_spec="Parallel flow spec",
        tasks=list(base_state.tasks.values()),
        dependency_graph={t_downstream.task_id: [t1.task_id, t2.task_id, t3.task_id]},
        parallel_groups=[[t1.task_id, t2.task_id, t3.task_id]],
    )

    group = monitor.get_parallel_group(t1.task_id, base_state)
    assert group == [t1.task_id, t2.task_id, t3.task_id]

    status = monitor.get_group_status(group, base_state)
    assert status == "COMPLETED"

    prereq_status = monitor.check_prerequisites(t_downstream.task_id, base_state)
    assert prereq_status == "READY"


def test_parallel_group_one_fails(monitor, progress_monitor, base_state):
    t1 = create_task(TaskStatus.COMPLETED)
    t2 = create_task(TaskStatus.FAILED)
    t3 = create_task(TaskStatus.COMPLETED)
    t_downstream = create_task(TaskStatus.WAITING)

    base_state.tasks = {
        t1.task_id: t1,
        t2.task_id: t2,
        t3.task_id: t3,
        t_downstream.task_id: t_downstream,
    }

    base_state.planner_output = PlannerOutput(
        workflow_spec="Parallel flow spec",
        tasks=list(base_state.tasks.values()),
        dependency_graph={t_downstream.task_id: [t1.task_id, t2.task_id, t3.task_id]},
        parallel_groups=[[t1.task_id, t2.task_id, t3.task_id]],
    )

    group = monitor.get_parallel_group(t2.task_id, base_state)
    status = monitor.get_group_status(group, base_state)
    assert status == "FAILED"

    # Propagate progress changes
    progress_monitor.update_progress_state(base_state)
    assert t_downstream.status == TaskStatus.BLOCKED
    assert base_state.progress.blocked_tasks == 1


def test_parallel_group_one_running(monitor, base_state):
    t1 = create_task(TaskStatus.COMPLETED)
    t2 = create_task(TaskStatus.RUNNING)
    t3 = create_task(TaskStatus.WAITING)
    t_downstream = create_task(TaskStatus.WAITING)

    base_state.tasks = {
        t1.task_id: t1,
        t2.task_id: t2,
        t3.task_id: t3,
        t_downstream.task_id: t_downstream,
    }

    base_state.planner_output = PlannerOutput(
        workflow_spec="Parallel flow spec",
        tasks=list(base_state.tasks.values()),
        dependency_graph={t_downstream.task_id: [t1.task_id, t2.task_id, t3.task_id]},
        parallel_groups=[[t1.task_id, t2.task_id, t3.task_id]],
    )

    group = monitor.get_parallel_group(t3.task_id, base_state)
    status = monitor.get_group_status(group, base_state)
    assert status == "RUNNING"

    prereq_status = monitor.check_prerequisites(t_downstream.task_id, base_state)
    assert prereq_status == "PENDING"


def test_supervisor_integration(supervisor, base_state):
    t1 = create_task(TaskStatus.COMPLETED)
    t2 = create_task(TaskStatus.COMPLETED)
    t_downstream = create_task(TaskStatus.WAITING)

    base_state.tasks = {
        t1.task_id: t1,
        t2.task_id: t2,
        t_downstream.task_id: t_downstream,
    }

    base_state.planner_output = PlannerOutput(
        workflow_spec="Parallel flow spec",
        tasks=list(base_state.tasks.values()),
        dependency_graph={t_downstream.task_id: [t1.task_id, t2.task_id]},
        parallel_groups=[[t1.task_id, t2.task_id]],
    )

    assert supervisor.is_task_ready(t_downstream.task_id, base_state) is True
    assert supervisor.get_parallel_group_status(t1.task_id, base_state) == "COMPLETED"
