"""Unit tests for Sprint 0 runtime contracts and shared interfaces."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionMetrics,
    ExecutionResult,
    HealingResult,
    SupervisorValidation,
)
from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)
from shared.contracts.task import (
    RollbackInfo,
    Task,
    TaskCategory,
    TaskPriority,
    TaskStatus,
)
from shared.contracts.workflow import (
    ExecutionMode,
    PlannerOutput,
    ProgressState,
    SharedWorkflowState,
    WorkflowMetadata,
)


def test_artifact_contract():
    workflow_id = uuid4()
    artifact = Artifact(
        workflow_id=workflow_id,
        name="presentation.pptx",
        filepath="/artifacts/presentation.pptx",
        artifact_type=ArtifactType.PPT,
        size_bytes=10240,
        checksum="sha256:abc123def456",
    )
    assert artifact.artifact_id is not None
    assert artifact.workflow_id == workflow_id
    assert artifact.artifact_type == ArtifactType.PPT
    assert artifact.size_bytes == 10240

    # JSON serialization check
    json_data = artifact.model_dump_json()
    reconstructed = Artifact.model_validate_json(json_data)
    assert reconstructed.artifact_id == artifact.artifact_id
    assert reconstructed.name == artifact.name


def test_permission_contract():
    workflow_id = uuid4()
    perm = PermissionRequest(
        workflow_id=workflow_id,
        permission_type=PermissionType.POWERSHELL,
        reason="Execution of system diagnostic command",
        risk_level=RiskLevel.HIGH,
    )
    assert perm.status == PermissionStatus.PENDING
    assert perm.risk_level == RiskLevel.HIGH

    json_data = perm.model_dump_json()
    reconstructed = PermissionRequest.model_validate_json(json_data)
    assert reconstructed.permission_type == PermissionType.POWERSHELL


def test_event_contract():
    workflow_id = uuid4()
    task_id = uuid4()
    event = RuntimeEvent(
        workflow_id=workflow_id,
        task_id=task_id,
        event_type=EventType.TASK_STARTED,
        source_component=EventSource.WORKER,
        target_component=EventSource.SUPERVISOR,
        payload={"attempt": 1},
    )
    assert event.event_type == EventType.TASK_STARTED
    assert event.source_component == EventSource.WORKER
    assert event.payload["attempt"] == 1


def test_task_contract():
    workflow_id = uuid4()
    rollback = RollbackInfo(
        rollback_point="git_commit_hash",
        changed_files=["/tmp/test.txt"],
    )
    task = Task(
        workflow_id=workflow_id,
        task_name="Search Web",
        description="Search recent news about AI",
        required_tool="BrowserTool",
        category=TaskCategory.BROWSER,
        priority=TaskPriority.HIGH,
        expected_output="HTML content summary",
        rollback_info=rollback,
    )
    assert task.status == TaskStatus.CREATED
    assert task.retry_count == 0
    assert task.assigned_agent == "WorkerAgent"
    assert task.rollback_info.rollback_point == "git_commit_hash"


def test_execution_result_contract():
    workflow_id = uuid4()
    task_id = uuid4()
    metrics = ExecutionMetrics(
        execution_time_ms=120.5,
        memory_usage_mb=45.2,
        cpu_usage_percent=12.1,
        exit_code=0,
    )
    result = ExecutionResult(
        task_id=task_id,
        workflow_id=workflow_id,
        success=True,
        output={"status": "completed"},
        metrics=metrics,
        logs=["Task started", "Task finished successfully"],
    )
    assert result.success is True
    assert result.metrics.execution_time_ms == 120.5
    assert len(result.logs) == 2


def test_supervisor_and_healing_contracts():
    workflow_id = uuid4()
    task_id = uuid4()
    validation = SupervisorValidation(
        task_id=task_id,
        workflow_id=workflow_id,
        is_valid=False,
        issues=["Missing expected output artifact"],
    )
    assert validation.is_valid is False
    assert len(validation.issues) == 1

    healing = HealingResult(
        task_id=task_id,
        workflow_id=workflow_id,
        root_cause="Browser timeout during navigation",
        recovery_strategy="Retry with increased timeout",
        attempt_number=1,
        success=True,
    )
    assert healing.attempt_number == 1
    assert healing.success is True


def test_workflow_and_shared_state_contract():
    workflow_id = uuid4()
    metadata = WorkflowMetadata(
        workflow_id=workflow_id,
        goal="Create PowerPoint on AI Trends",
        execution_mode=ExecutionMode.AUTONOMOUS,
    )
    planner_out = PlannerOutput(
        workflow_spec="Step 1 -> Step 2 -> Step 3",
        estimated_time_seconds=60,
        risks=["Network latency"],
        confidence_score=0.95,
    )
    sws = SharedWorkflowState(
        metadata=metadata,
        planner_output=planner_out,
        progress=ProgressState(
            total_tasks=3,
            pending_tasks=3,
        ),
    )
    assert sws.metadata.workflow_id == workflow_id
    assert sws.planner_output.confidence_score == 0.95
    assert sws.progress.total_tasks == 3

    # Validate JSON Schema generation works seamlessly
    schema = SharedWorkflowState.model_json_schema()
    assert "properties" in schema


def test_validation_errors():
    with pytest.raises(ValidationError):
        # Invalid confidence score > 1.0
        PlannerOutput(
            workflow_spec="test",
            confidence_score=1.5,
        )

    with pytest.raises(ValidationError):
        # Negative retry count
        Task(
            workflow_id=uuid4(),
            task_name="Invalid Task",
            description="desc",
            required_tool="tool",
            category=TaskCategory.PYTHON,
            expected_output="output",
            retry_count=-1,
        )
