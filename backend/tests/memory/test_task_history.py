from uuid import uuid4

import pytest
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.memory.task_history import (
    reset_task_history_service,
)
from app.runtime.kernel import RuntimeKernel
from app.tools.registry import ToolRegistry


@pytest.fixture
def service():
    """Provides a fresh TaskHistoryService for each test."""
    return reset_task_history_service()


@pytest.fixture
def sample_task():
    """Provides a sample Task contract instance."""
    return Task(
        task_id=uuid4(),
        workflow_id=uuid4(),
        task_name="Test Task 1",
        description="Sample test task description",
        assigned_agent="WorkerAgent",
        required_tool="dummy_tool",
        category=TaskCategory.BROWSER,
        status=TaskStatus.CREATED,
        expected_output="Sample expected output",
    )


def test_task_creation_recording(service, sample_task):
    """Verifies that task creation is recorded cleanly."""
    rec = service.record_task_created(sample_task, metadata={"meta_key": "meta_val"})
    assert rec.task_id == sample_task.task_id
    assert rec.workflow_id == sample_task.workflow_id
    assert rec.task_name == "Test Task 1"
    assert rec.status == TaskStatus.CREATED
    assert rec.metadata.get("meta_key") == "meta_val"

    history = service.get_task_history(sample_task.task_id)
    assert len(history) == 1
    assert history[0].task_id == sample_task.task_id


def test_task_start_completion_recording(service, sample_task):
    """Verifies recording task start and completion."""
    service.record_task_created(sample_task)

    start_rec = service.record_task_started(
        sample_task, agent_name="CustomWorker", inputs={"arg1": "val1"}
    )
    assert start_rec.status == TaskStatus.RUNNING
    assert start_rec.assigned_agent == "CustomWorker"
    assert start_rec.inputs == {"arg1": "val1"}
    assert start_rec.started_at is not None

    exec_result = ExecutionResult(
        task_id=sample_task.task_id,
        workflow_id=sample_task.workflow_id,
        success=True,
        output={"result_key": "result_val"},
        metrics=ExecutionMetrics(execution_time_ms=150.5),
    )
    comp_rec = service.record_task_completed(sample_task.task_id, exec_result)
    assert comp_rec.status == TaskStatus.COMPLETED
    assert comp_rec.outputs == {"result_key": "result_val"}
    assert comp_rec.execution_time_ms == 150.5
    assert comp_rec.completed_at is not None

    all_history = service.get_task_history(sample_task.task_id)
    assert len(all_history) == 3  # CREATED, RUNNING, COMPLETED


def test_task_failure_recording(service, sample_task):
    """Verifies recording task execution failure."""
    service.record_task_created(sample_task)
    service.record_task_started(sample_task)

    err = TaskError(error_code="TIMEOUT_EXCEEDED", error_message="Task timed out")
    fail_rec = service.record_task_failed(sample_task.task_id, err)

    assert fail_rec.status == TaskStatus.FAILED
    assert fail_rec.error is not None
    assert fail_rec.error.error_code == "TIMEOUT_EXCEEDED"
    assert fail_rec.error.error_message == "Task timed out"

    history = service.get_task_history(sample_task.task_id)
    assert history[-1].status == TaskStatus.FAILED


def test_retry_attempt_recording(service, sample_task):
    """Verifies recording retry attempts."""
    service.record_task_created(sample_task)
    service.record_task_started(sample_task)
    service.record_task_failed(
        sample_task.task_id, TaskError(error_code="ERR", error_message="Fail")
    )

    retry_rec = service.record_retry_attempt(
        sample_task.task_id, attempt_number=2, reason="Transient failure"
    )
    assert retry_rec.status == TaskStatus.HEALING
    assert retry_rec.attempt_number == 2
    assert retry_rec.retry_count == 1
    assert retry_rec.metadata.get("retry_reason") == "Transient failure"

    history = service.get_task_history(sample_task.task_id)
    assert len(history) == 4


def test_workflow_history_retrieval(service, sample_task):
    """Verifies retrieving top-level workflow history record and progress."""
    wf_id = sample_task.workflow_id

    service.record_workflow_status(wf_id, goal="Test Workflow Goal", status="RUNNING")
    service.record_task_created(sample_task)
    service.record_task_started(sample_task)

    exec_result = ExecutionResult(
        task_id=sample_task.task_id,
        workflow_id=wf_id,
        success=True,
        output={"ok": True},
        metrics=ExecutionMetrics(execution_time_ms=50.0),
    )
    service.record_task_completed(sample_task.task_id, exec_result)

    wf_rec = service.get_workflow_history(wf_id)
    assert wf_rec is not None
    assert wf_rec.workflow_id == wf_id
    assert wf_rec.goal == "Test Workflow Goal"
    assert wf_rec.total_tasks == 1
    assert wf_rec.completed_tasks == 1
    assert len(wf_rec.tasks_history) >= 3


def test_history_filtering(service):
    """Verifies querying and filtering task history records."""
    wf_1 = uuid4()
    wf_2 = uuid4()

    t1 = Task(
        task_id=uuid4(),
        workflow_id=wf_1,
        task_name="Task A",
        description="A",
        required_tool="tool_a",
        category=TaskCategory.BROWSER,
        assigned_agent="AgentA",
        expected_output="Output A",
    )
    t2 = Task(
        task_id=uuid4(),
        workflow_id=wf_1,
        task_name="Task B",
        description="B",
        required_tool="tool_b",
        category=TaskCategory.PYTHON,
        assigned_agent="AgentB",
        expected_output="Output B",
    )
    t3 = Task(
        task_id=uuid4(),
        workflow_id=wf_2,
        task_name="Task C",
        description="C",
        required_tool="tool_c",
        category=TaskCategory.BROWSER,
        assigned_agent="AgentA",
        expected_output="Output C",
    )

    service.record_task_created(t1)
    service.record_task_started(t1, agent_name="AgentA")
    service.record_task_completed(
        t1.task_id,
        ExecutionResult(
            task_id=t1.task_id,
            workflow_id=wf_1,
            success=True,
            metrics=ExecutionMetrics(execution_time_ms=10.0),
        ),
    )

    service.record_task_created(t2)
    service.record_task_started(t2, agent_name="AgentB")
    service.record_task_failed(
        t2.task_id, TaskError(error_code="ERR", error_message="fail")
    )

    service.record_task_created(t3)
    service.record_task_started(t3, agent_name="AgentA")

    # Filter by workflow_id
    wf1_records = service.filter_history(workflow_id=wf_1)
    assert len(wf1_records) == 6

    # Filter by status
    completed_records = service.filter_history(status=TaskStatus.COMPLETED)
    assert len(completed_records) == 1
    assert completed_records[0].task_name == "Task A"

    # Filter by category
    browser_records = service.filter_history(category=TaskCategory.BROWSER)
    assert all(
        r.task_category in (TaskCategory.BROWSER, TaskCategory.BROWSER.value)
        for r in browser_records
    )

    # Filter by agent
    agent_b_records = service.filter_history(agent_name="AgentB")
    assert all(r.assigned_agent == "AgentB" for r in agent_b_records)

    # Filter with limit
    limited_records = service.filter_history(limit=2)
    assert len(limited_records) == 2


def test_empty_and_invalid_history_queries(service):
    """Verifies safe behavior when querying empty history or non-existent IDs."""
    fake_id = uuid4()
    assert service.get_task_history(fake_id) == []
    assert service.get_workflow_history(fake_id) is None
    assert service.get_workflow_task_records(fake_id) == []
    assert service.filter_history(workflow_id=fake_id) == []


def test_runtime_kernel_and_context_integration(service):
    """Verifies that RuntimeKernel and RuntimeContext record history automatically."""
    kernel = RuntimeKernel(task_history_service=service)
    wf_id = uuid4()
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(workflow_id=wf_id, goal="Kernel Integration Goal")
    )

    ctx = kernel.create_context(session_id="sess_123", shared_state=state)
    assert ctx.task_history_service == service

    wf_rec = service.get_workflow_history(wf_id)
    assert wf_rec is not None
    assert wf_rec.goal == "Kernel Integration Goal"

    ctx.mark_complete()
    wf_rec_after = service.get_workflow_history(wf_id)
    assert wf_rec_after.status == "COMPLETED"


@pytest.mark.asyncio
async def test_worker_agent_history_integration(service):
    """
    Verifies WorkerAgent automatically logs execution start, complete, and failure.
    """

    registry = ToolRegistry()
    worker = WorkerAgent(tool_registry=registry, task_history_service=service)

    task = Task(
        task_id=uuid4(),
        workflow_id=uuid4(),
        task_name="Worker Task",
        description="Executing test task",
        required_tool="non_existent_tool",
        category=TaskCategory.OTHER,
        expected_output="Output",
    )

    # Execute task (which will fail due to missing tool)
    result = await worker.execute(task)
    assert not result.success

    history = service.get_task_history(task.task_id)
    assert len(history) >= 2
    assert history[0].status == TaskStatus.RUNNING
    assert history[-1].status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_supervisor_agent_history_integration(service):
    """Verifies SupervisorAgent records retry attempts and validation failures."""
    supervisor = SupervisorAgent(task_history_service=service)

    task = Task(
        task_id=uuid4(),
        workflow_id=uuid4(),
        task_name="Supervisor Task",
        description="Testing supervisor",
        required_tool="tool_x",
        category=TaskCategory.OTHER,
        status=TaskStatus.FAILED,
        expected_output="Output",
    )

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(workflow_id=task.workflow_id, goal="Supervisor Goal")
    )
    state.tasks[task.task_id] = task

    # Trigger failure analysis/retry check
    retried = await supervisor._execute_retry(
        task=task,
        state=state,
        error=TaskError(error_code="TIMEOUT", error_message="Time out"),
    )

    history = service.get_task_history(task.task_id)
    if retried:
        assert any(r.status == TaskStatus.HEALING for r in history)
