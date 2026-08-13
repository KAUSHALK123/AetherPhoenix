import uuid

import pytest
from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import (
    ExecutionMetrics,
    ExecutionResult,
    FailureType,
    TaskError,
)
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.supervisor.agent import SupervisorAgent
from app.agents.supervisor.failure_detector import FailureDetectorService
from app.core.events.bus import EventBus
from app.core.exceptions import (
    AgentRuntimeException,
    PermissionDeniedException,
    RuntimeException,
    ToolExecutionException,
    ToolNotFoundException,
    ValidationException,
    WorkflowRuntimeException,
)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def service():
    return FailureDetectorService(default_timeout_seconds=10)


@pytest.fixture
def supervisor(event_bus, service):
    return SupervisorAgent(event_bus=event_bus, failure_detector=service)


@pytest.fixture
def workflow_state():
    metadata = WorkflowMetadata(
        goal="Test failure detection workflow",
        status=WorkflowStatus.RUNNING,
    )
    return SharedWorkflowState(metadata=metadata)


def create_base_task(workflow_id: uuid.UUID) -> Task:
    return Task(
        task_id=uuid.uuid4(),
        workflow_id=workflow_id,
        task_name="Write document",
        description="Generates a text document",
        required_tool="document_generator",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="document.txt",
        status=TaskStatus.RUNNING,
    )


def create_base_result(task_id: uuid.UUID, workflow_id: uuid.UUID) -> ExecutionResult:
    return ExecutionResult(
        task_id=task_id,
        workflow_id=workflow_id,
        success=True,
        output={"status": "SUCCESS"},
        metrics=ExecutionMetrics(execution_time_ms=500.0),
    )


# 1. Test Worker Explicitly Reports Failure
def test_detect_worker_explicit_failure(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)
    result = create_base_result(task.task_id, task.workflow_id)
    result.success = False
    result.error = TaskError(
        error_code="EXECUTION_FAILED",
        error_message="Worker encountered critical system failure",
        is_recoverable=True,
    )

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.UNEXPECTED_EXCEPTION
    assert "critical system failure" in report.message
    assert report.retryability is True


# 2. Test Tool Returns An Error
def test_detect_tool_error(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)
    result = create_base_result(task.task_id, task.workflow_id)
    result.success = False
    result.error = TaskError(
        error_code="TOOL_EXECUTION_ERROR",
        error_message="PDF generator engine exited with non-zero code",
        is_recoverable=True,
    )

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.TOOL_ERROR
    assert "PDF generator" in report.message
    assert report.retryability is True


# 3. Test Expected Output is Missing
def test_detect_expected_output_missing(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)
    task.expected_output = "report.pdf"

    # Successful result but expected output file is not mentioned in output or artifacts
    result = create_base_result(task.task_id, task.workflow_id)
    result.output = {"data": "some text"}
    result.artifacts = []

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.OUTPUT_MISSING
    assert "missing" in report.message
    assert report.retryability is False


# 4. Test Artifact Validation Fails
def test_detect_artifact_validation_failures(service, workflow_state, tmp_path):
    task = create_base_task(workflow_state.metadata.workflow_id)
    task.expected_output = "report.pdf"
    result = create_base_result(task.task_id, task.workflow_id)

    # A: File path does not exist
    non_existent_file = str(tmp_path / "missing_file.pdf")
    artifact_a = Artifact(
        workflow_id=task.workflow_id,
        task_id=task.task_id,
        name="report.pdf",
        filepath=non_existent_file,
        artifact_type=ArtifactType.PDF,
    )
    result.artifacts = [artifact_a]

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.ARTIFACT_VALIDATION_FAILED
    assert "does not exist" in report.message

    # B: File exists but has 0 bytes (empty)
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")
    artifact_b = Artifact(
        workflow_id=task.workflow_id,
        task_id=task.task_id,
        name="report.pdf",
        filepath=str(empty_file),
        artifact_type=ArtifactType.PDF,
    )
    result.artifacts = [artifact_b]

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.ARTIFACT_VALIDATION_FAILED
    assert "empty" in report.message

    # C: Successful artifact check
    valid_file = tmp_path / "valid.pdf"
    valid_file.write_bytes(b"%PDF-1.4 header contents")
    artifact_c = Artifact(
        workflow_id=task.workflow_id,
        task_id=task.task_id,
        name="report.pdf",
        filepath=str(valid_file),
        artifact_type=ArtifactType.PDF,
        size_bytes=len(b"%PDF-1.4 header contents"),
    )
    result.artifacts = [artifact_c]

    report = service.check_failure(task, result, workflow_state)
    # Output file and artifact exists, size > 0 and readable,
    # so should NOT fail validation
    assert report is None


# 5. Test Task Exceeds Timeout
def test_detect_timeout(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)
    task.estimated_duration_seconds = 2  # 2 seconds limit

    # Took 3 seconds
    result = create_base_result(task.task_id, task.workflow_id)
    result.metrics = ExecutionMetrics(execution_time_ms=3000.0)

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.TIMEOUT
    assert "exceeded configured timeout" in report.message
    assert report.retryability is True


# 6. Test Required Dependency Failed
def test_detect_dependency_failure(service, workflow_state):
    parent_task_id = uuid.uuid4()

    # Enqueue parent task in state and mark it as failed
    parent_task = Task(
        task_id=parent_task_id,
        workflow_id=workflow_state.metadata.workflow_id,
        task_name="Parent Operation",
        description="Extract raw data",
        required_tool="extractor",
        category=TaskCategory.OTHER,
        expected_output="raw_data",
        status=TaskStatus.FAILED,
    )
    workflow_state.tasks[parent_task_id] = parent_task

    # Create child task depending on parent
    child_task = create_base_task(workflow_state.metadata.workflow_id)
    child_task.dependencies = [parent_task_id]

    result = create_base_result(child_task.task_id, child_task.workflow_id)

    report = service.check_failure(child_task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.DEPENDENCY_FAILED
    assert "Parent Operation" in report.message
    assert report.retryability is False


# 7. Test Permission Denied
def test_detect_permission_denied(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)
    result = create_base_result(task.task_id, task.workflow_id)
    result.success = False
    result.error = TaskError(
        error_code="PERMISSION_DENIED",
        error_message="Access denied to write to registry",
        is_recoverable=False,
    )

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.PERMISSION_DENIED
    assert "Access denied" in report.message
    assert report.retryability is False


# 8. Test Tool Unavailable
def test_detect_tool_unavailable(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)
    task.required_tool = "non_existent_tool"
    result = create_base_result(task.task_id, task.workflow_id)
    result.success = False
    result.error = TaskError(
        error_code="TOOL_NOT_FOUND",
        error_message="Tool 'non_existent_tool' is not registered.",
        is_recoverable=False,
    )

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.TOOL_UNAVAILABLE
    assert "is not registered" in report.message
    assert report.retryability is False


# 9. Test Unexpected Execution Exception
def test_detect_unexpected_execution_exception(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)
    result = create_base_result(task.task_id, task.workflow_id)
    result.success = False
    result.error = TaskError(
        error_code="UNEXPECTED_EXCEPTION",
        error_message="ZeroDivisionError: division by zero",
        is_recoverable=False,
    )

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.UNEXPECTED_EXCEPTION
    assert "ZeroDivisionError" in report.message
    assert report.retryability is False


# 10. Test Workflow Blocked
def test_detect_workflow_blocked(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)
    task.status = TaskStatus.WAITING
    workflow_state.tasks[task.task_id] = task

    # Workflow is running, but no tasks are in queue or running,
    # and task remains uncompleted
    workflow_state.execution_queue = []
    workflow_state.running_tasks = []

    result = create_base_result(task.task_id, task.workflow_id)

    report = service.check_failure(task, result, workflow_state)
    assert report is not None
    assert report.failure_type == FailureType.WORKFLOW_BLOCKED
    assert "blocked" in report.message
    assert report.retryability is False


# 11. Test Exception Mapping
def test_exception_mapping(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)

    # We will test all failure types map to their correct exception classes
    mappings = {
        FailureType.PERMISSION_DENIED: PermissionDeniedException,
        FailureType.TOOL_UNAVAILABLE: ToolNotFoundException,
        FailureType.TOOL_ERROR: ToolExecutionException,
        FailureType.OUTPUT_MISSING: ValidationException,
        FailureType.ARTIFACT_VALIDATION_FAILED: ValidationException,
        FailureType.DEPENDENCY_FAILED: WorkflowRuntimeException,
        FailureType.WORKFLOW_BLOCKED: WorkflowRuntimeException,
        FailureType.WORKER_FAILURE: AgentRuntimeException,
        FailureType.TIMEOUT: RuntimeException,
        FailureType.UNEXPECTED_EXCEPTION: RuntimeException,
    }

    for f_type, exc_class in mappings.items():
        report = service._create_report(
            task=task,
            failure_type=f_type,
            message="Test mapping error msg",
            retryability=True,
            execution_context={},
        )
        mapped_exc = service.map_to_exception(report)
        assert isinstance(mapped_exc, exc_class)
        assert mapped_exc.message == "Test mapping error msg"
        assert mapped_exc.details["failure_type"] == f_type.value


# 12. Test Retryability Heuristics
def test_retryability_heuristics(service, workflow_state):
    task = create_base_task(workflow_state.metadata.workflow_id)

    # A: Error containing network timeout keywords should be retryable
    result_a = create_base_result(task.task_id, task.workflow_id)
    result_a.success = False
    result_a.error = TaskError(
        error_code="HTTP_ERROR",
        error_message="Connection timed out while retrieving website",
    )
    report_a = service.check_failure(task, result_a, workflow_state)
    assert report_a is not None
    assert report_a.retryability is True

    # B: Error explicitly marked as non-retryable by worker
    result_b = create_base_result(task.task_id, task.workflow_id)
    result_b.success = False
    result_b.error = TaskError(
        error_code="SQL_SYNTAX_ERROR",
        error_message="Table 'users' does not exist in schema",
        is_recoverable=False,
    )
    report_b = service.check_failure(task, result_b, workflow_state)
    assert report_b is not None
    assert report_b.retryability is False


# 13. Test SupervisorAgent Validation & SharedWorkflowState Sync
@pytest.mark.asyncio
async def test_supervisor_validation_and_state_sync(
    supervisor, event_bus, workflow_state, tmp_path
):
    task = create_base_task(workflow_state.metadata.workflow_id)
    task.expected_output = "data.txt"
    workflow_state.tasks[task.task_id] = task
    workflow_state.running_tasks = [task.task_id]

    # Verify initial state
    assert task.status == TaskStatus.RUNNING

    # 1. Test validation success
    result_success = create_base_result(task.task_id, task.workflow_id)
    result_success.output = {"data.txt": "File created"}

    # We will subscribe to check if EVENT_COMPLETED is published
    emitted_events = []

    async def handler(evt):
        emitted_events.append(evt)

    event_bus.subscribe_all(handler)

    validation_success = await supervisor.execute(task, result_success, workflow_state)
    assert validation_success.is_valid is True
    assert task.status == TaskStatus.COMPLETED
    assert task.task_id in workflow_state.completed_tasks
    assert task.task_id not in workflow_state.running_tasks

    # Allow asyncio loop to process published events
    import asyncio
    from shared.contracts.event import EventType

    await asyncio.sleep(0.1)

    assert len(emitted_events) >= 2
    assert emitted_events[0].event_type == EventType.SUPERVISION_STARTED
    assert emitted_events[1].event_type == EventType.SUPERVISION_COMPLETED

    # Reset state and test validation failure
    task.status = TaskStatus.RUNNING
    workflow_state.running_tasks = [task.task_id]
    workflow_state.completed_tasks = []
    emitted_events.clear()

    result_fail = create_base_result(task.task_id, task.workflow_id)
    result_fail.success = False
    result_fail.error = TaskError(
        error_code="EXECUTION_FAILED", error_message="Disk Full"
    )

    validation_fail = await supervisor.execute(task, result_fail, workflow_state)
    assert validation_fail.is_valid is False
    assert task.status == TaskStatus.FAILED
    assert task.task_id in workflow_state.failed_tasks
    assert task.task_id not in workflow_state.running_tasks

    await asyncio.sleep(0.1)
    assert len(emitted_events) >= 2
    assert emitted_events[0].event_type == EventType.SUPERVISION_STARTED
    assert emitted_events[1].event_type == EventType.SUPERVISION_COMPLETED
