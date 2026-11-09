import asyncio
from pathlib import Path
from uuid import uuid4
import pytest
import pptx

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import ExecutionResult
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata, WorkflowStatus

from app.agents.supervisor.agent import SupervisorAgent
from app.agents.supervisor.failure_detector import FailureDetectorService
from app.agents.worker.agent import WorkerAgent
from app.core.config import get_config
from app.core.events.bus import EventBus
from app.core.permissions.manager import PermissionManager
from shared.contracts.permission import PermissionRequest, PermissionStatus, PermissionType, RiskLevel
from app.engine.orchestrator import PipelineOrchestrator
from app.tools.ppt import register_ppt_tool
from app.tools.ppt.adapter import PPTToolAdapter
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_ppt_5_slide_e2e_valid_pptx(tmp_path):
    """Regression test for Bug 1: Run 5-slide PPT goal end-to-end, assert valid openable .pptx exists."""
    cfg = get_config()
    cfg.ARTIFACTS_DIR = str(tmp_path / "artifacts")
    Path(cfg.ARTIFACTS_DIR).mkdir(parents=True, exist_ok=True)

    event_bus = EventBus()
    permission_manager = PermissionManager()
    tool_registry = ToolRegistry()

    workflow_id = uuid4()

    # Pre-approve FILE_SYSTEM permissions
    perm_req = PermissionRequest(
        workflow_id=workflow_id,
        permission_type=PermissionType.FILE_SYSTEM,
        reason="Generate PowerPoint presentation file",
        risk_level=RiskLevel.SAFE,
        status=PermissionStatus.GRANTED,
    )
    permission_manager.request_permission(perm_req)

    # Register PPT tool and adapter
    register_ppt_tool(tool_registry)
    ppt_adapter = PPTToolAdapter(
        permission_manager=permission_manager,
    )

    worker = WorkerAgent(
        tool_registry=tool_registry,
        permission_manager=permission_manager,
    )
    worker.register_adapter("app.tools.ppt.adapter.PPTToolAdapter", ppt_adapter)
    worker.register_adapter("ppt_tool", ppt_adapter)

    supervisor = SupervisorAgent(
        event_bus=event_bus,
        max_retries=3,
    )

    orchestrator = PipelineOrchestrator(
        worker_agent=worker,
        supervisor_agent=supervisor,
        event_bus=event_bus,
    )

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Create a 5 slide presentation on Renewable Energy",
            status=WorkflowStatus.CREATED,
        )
    )

    task = Task(
        workflow_id=workflow_id,
        task_name="Build PPTX Deck",
        description="Create 5 presentation slides with formatting and visuals",
        assigned_agent="WorkerAgent",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="Presentation deck (.pptx)",
        inputs={"topic": "Renewable Energy Strategy", "slides_count": 5},
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    # Execute workflow end-to-end
    final_state = await orchestrator.run_workflow(state, max_retries=3)

    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED
    assert task.retry_count == 0  # Should NOT get stuck in a retry loop

    # Verify output file exists on disk and is a valid .pptx with 5 slides
    assert task.artifact_location is not None
    output_path = Path(task.artifact_location)
    assert output_path.exists(), f"File does not exist: {output_path}"
    assert output_path.suffix.lower() == ".pptx"
    assert output_path.stat().st_size > 0

    prs = pptx.Presentation(str(output_path))
    assert len(prs.slides) == 5, f"Expected 5 slides, got {len(prs.slides)}"


def test_failure_detector_does_not_flag_valid_ppt_output():
    """Verify Supervisor contract check matches 'Presentation deck (.pptx)' to 'presentation.pptx'."""
    fd = FailureDetectorService()
    workflow_id = uuid4()
    task = Task(
        workflow_id=workflow_id,
        task_name="Build PPTX Deck",
        description="Create slides",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="Presentation deck (.pptx)",
    )
    artifact = Artifact(
        workflow_id=workflow_id,
        task_id=task.task_id,
        name="presentation.pptx",
        filepath="artifacts/test/presentation.pptx",
        artifact_type=ArtifactType.PPT,
        size_bytes=1000,
        checksum="dummy",
    )
    res = ExecutionResult(
        task_id=task.task_id,
        workflow_id=workflow_id,
        success=True,
        output={
            "artifact_id": "art-1",
            "filepath": "artifacts/test/presentation.pptx",
            "output_path": "artifacts/test/presentation.pptx",
            "download_url": "/api/v1/artifacts/art-1/download",
        },
        artifacts=[artifact],
    )

    is_missing = fd._is_output_missing(task, res)
    assert is_missing is False, "FailureDetector incorrectly flagged valid PPT output as missing"


@pytest.mark.asyncio
async def test_retry_budget_hard_cap_exhaustion_fails_workflow(tmp_path):
    """Verify that exhausting the retry budget (K_max=3) ends the workflow as FAILED without infinite loop."""
    event_bus = EventBus()
    permission_manager = PermissionManager()
    tool_registry = ToolRegistry()

    # Create a failing adapter
    from app.tools.adapter import BaseToolAdapter

    class AlwaysFailingAdapter(BaseToolAdapter):
        def __init__(self):
            self.call_count = 0

        async def execute(self, t):
            self.call_count += 1
            return ExecutionResult(
                task_id=t.task_id,
                workflow_id=t.workflow_id,
                success=False,
                error=TaskError(
                    error_code="PPT_RENDER_CRASH",
                    error_message="Repeated render crash",
                    is_recoverable=True,
                ),
            )

    failing_adapter = AlwaysFailingAdapter()
    register_ppt_tool(tool_registry)

    worker = WorkerAgent(
        tool_registry=tool_registry,
        permission_manager=permission_manager,
    )
    worker.register_adapter("app.tools.ppt.adapter.PPTToolAdapter", failing_adapter)
    worker.register_adapter("ppt_tool", failing_adapter)

    supervisor = SupervisorAgent(
        event_bus=event_bus,
        max_retries=3,
    )

    orchestrator = PipelineOrchestrator(
        worker_agent=worker,
        supervisor_agent=supervisor,
        event_bus=event_bus,
    )

    workflow_id = uuid4()
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Create PPT deck",
            status=WorkflowStatus.CREATED,
        )
    )

    task = Task(
        workflow_id=workflow_id,
        task_name="Build PPTX Deck",
        description="Create slides",
        assigned_agent="WorkerAgent",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="Presentation deck (.pptx)",
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    # Run workflow: must terminate as FAILED after max 3 retries (total 4 attempts: initial + 3 retries)
    final_state = await orchestrator.run_workflow(state, max_retries=3)

    assert final_state.metadata.status == WorkflowStatus.FAILED
    assert task.status == TaskStatus.FAILED
    assert failing_adapter.call_count <= 4, f"Infinite loop detected: called {failing_adapter.call_count} times"


@pytest.mark.asyncio
async def test_download_artifact_ppt_mime_type_and_filename(tmp_path):
    """Verify download endpoint returns native openxmlformats PPTX MIME type and correct filename."""
    from app.api.endpoints.artifacts import download_artifact
    from app.services.artifact_storage import get_artifact_storage_service

    test_file = tmp_path / "presentation.pptx"
    test_file.write_bytes(b"PK\x03\x04test_presentation_bytes")

    storage = get_artifact_storage_service()
    workflow_id = uuid4()
    task_id = uuid4()
    artifact = Artifact(
        workflow_id=workflow_id,
        task_id=task_id,
        name="presentation.pptx",
        filepath=str(test_file),
        artifact_type=ArtifactType.PPT,
        size_bytes=test_file.stat().st_size,
        checksum="dummy_checksum",
    )
    saved_art = await storage.register_artifact(artifact, content=test_file.read_bytes())

    response = await download_artifact(saved_art.artifact_id)
    assert response.media_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert response.headers["Content-Disposition"] == 'attachment; filename="presentation.pptx"'
    assert response.filename == "presentation.pptx"

