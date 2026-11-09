from pathlib import Path
from uuid import uuid4
import pytest

from shared.contracts.artifact import ArtifactType
from shared.contracts.permission import PermissionRequest, PermissionStatus, PermissionType, RiskLevel
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata, WorkflowStatus

from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.core.config import get_config
from app.core.events.bus import EventBus
from app.core.permissions.manager import PermissionManager
from app.engine.orchestrator import PipelineOrchestrator
from app.planner.decomposer import TaskDecompositionEngine
from app.tools.ocr.adapter import OCRToolAdapter
from app.tools.ocr.tool import register_ocr_tool
from app.tools.pdf.generator import PDFGenerator
from app.tools.pdf.tool import PDFToolAdapter, register_pdf_tool
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_pdf_generation_e2e_and_contract_validation(tmp_path):
    """Regression test for Bug 2: PDF generation runs end-to-end, produces valid %PDF- file and passes contract checks."""
    cfg = get_config()
    cfg.ARTIFACTS_DIR = str(tmp_path / "artifacts")
    Path(cfg.ARTIFACTS_DIR).mkdir(parents=True, exist_ok=True)

    event_bus = EventBus()
    permission_manager = PermissionManager()
    tool_registry = ToolRegistry()

    workflow_id = uuid4()
    perm_req = PermissionRequest(
        workflow_id=workflow_id,
        permission_type=PermissionType.FILE_SYSTEM,
        reason="Generate PDF report",
        risk_level=RiskLevel.SAFE,
        status=PermissionStatus.GRANTED,
    )
    permission_manager.request_permission(perm_req)

    # Register PDF tool in registry under registered name
    pdf_tool = register_pdf_tool(tool_registry)
    assert pdf_tool.name == "pdf_generator"
    assert tool_registry.get("pdf_generator") is not None
    assert tool_registry.get("pdf_tool") is not None

    pdf_adapter = PDFToolAdapter(permission_manager=permission_manager)
    worker = WorkerAgent(
        tool_registry=tool_registry,
        permission_manager=permission_manager,
    )
    worker.register_adapter("pdf_generator", pdf_adapter)
    worker.register_adapter("app.tools.pdf.tool.PDFToolAdapter", pdf_adapter)

    supervisor = SupervisorAgent(event_bus=event_bus, max_retries=3)
    orchestrator = PipelineOrchestrator(
        worker_agent=worker,
        supervisor_agent=supervisor,
        event_bus=event_bus,
    )

    # 1. Test Decomposition of PDF generation goal
    decomposer = TaskDecompositionEngine()
    plan = decomposer.decompose_goal("generate pdf report on System Reliability", workflow_id=workflow_id)
    tasks = plan.tasks
    leaf_tasks = [t for t in tasks if t.required_tool]
    assert len(leaf_tasks) == 1
    pdf_task = leaf_tasks[0]
    assert pdf_task.required_tool == "pdf_generator"
    assert pdf_task.category == TaskCategory.PDF_GENERATION

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="generate pdf report on System Reliability",
            status=WorkflowStatus.CREATED,
        )
    )
    for t in tasks:
        state.tasks[t.task_id] = t
        state.execution_queue.append(t.task_id)

    # Run workflow
    final_state = await orchestrator.run_workflow(state, max_retries=3)
    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert pdf_task.status == TaskStatus.COMPLETED

    # Check generated PDF file has valid %PDF- header
    assert pdf_task.artifact_location is not None
    output_path = Path(pdf_task.artifact_location)
    assert output_path.exists()
    assert output_path.suffix.lower() == ".pdf"
    assert output_path.stat().st_size > 0

    with open(output_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-", f"Invalid PDF header: {header}"


@pytest.mark.asyncio
async def test_pdf_search_e2e(tmp_path):
    """Regression test for Bug 2: PDF search accurately extracts text and finds matching keywords."""
    cfg = get_config()
    cfg.ARTIFACTS_DIR = str(tmp_path / "artifacts")
    Path(cfg.ARTIFACTS_DIR).mkdir(parents=True, exist_ok=True)

    event_bus = EventBus()
    permission_manager = PermissionManager()
    tool_registry = ToolRegistry()

    workflow_id = uuid4()
    perm_req = PermissionRequest(
        workflow_id=workflow_id,
        permission_type=PermissionType.FILE_SYSTEM,
        reason="Search PDF text",
        risk_level=RiskLevel.SAFE,
        status=PermissionStatus.GRANTED,
    )
    permission_manager.request_permission(perm_req)

    # Register OCR tool and aliases
    register_ocr_tool(tool_registry)
    assert tool_registry.get("ocr") is not None
    assert tool_registry.get("pdf_search") is not None

    ocr_adapter = OCRToolAdapter(permission_manager=permission_manager)
    worker = WorkerAgent(
        tool_registry=tool_registry,
        permission_manager=permission_manager,
    )
    worker.register_adapter("ocr", ocr_adapter)
    worker.register_adapter("app.tools.ocr.adapter.OCRToolAdapter", ocr_adapter)

    # 1. Create a sample PDF file with a specific keyword
    target_pdf = tmp_path / "financial_report.pdf"
    pdf_adapter = PDFToolAdapter(permission_manager=permission_manager)
    sample_payload = {
        "title": "Quarterly Financial Analysis",
        "elements": [
            {"element_type": "paragraph", "text": "Executive revenue summary for fiscal year 2026."},
            {"element_type": "paragraph", "text": "Special keyword found here: PHOENIX_AUDIT_VERIFIED_77."},
            {"element_type": "paragraph", "text": "Operating margin increased by 14% across all regions."},
        ],
        "output_path": str(target_pdf),
    }
    pdf_adapter.execute(sample_payload)
    assert target_pdf.exists()

    # 2. Decompose a PDF search goal
    decomposer = TaskDecompositionEngine()
    search_goal = f"search for 'PHOENIX_AUDIT_VERIFIED_77' in '{str(target_pdf)}'"
    plan = decomposer.decompose_goal(search_goal, workflow_id=workflow_id)
    tasks = plan.tasks
    leaf_tasks = [t for t in tasks if t.required_tool]
    assert len(leaf_tasks) == 1
    search_task = leaf_tasks[0]
    assert search_task.required_tool == "ocr"
    assert search_task.category == TaskCategory.OCR
    assert search_task.inputs["query"] == "PHOENIX_AUDIT_VERIFIED_77"

    # 3. Execute OCR search task directly via WorkerAgent
    result = await worker.execute(search_task)
    assert result.success is True
    assert result.output.get("found") is True
    assert len(result.output.get("matches", [])) > 0
    assert "PHOENIX_AUDIT_VERIFIED_77" in result.output["extracted_text"]


@pytest.mark.asyncio
async def test_pdf_adapter_exception_not_swallowed(tmp_path):
    """Verify that errors in PDFToolAdapter are cleanly surfaced as TaskError rather than swallowed."""
    permission_manager = PermissionManager()
    adapter = PDFToolAdapter(permission_manager=permission_manager)

    # Create task pointing to an invalid/unwritable path to provoke an error
    task = Task(
        workflow_id=uuid4(),
        task_name="Failing PDF Task",
        description="Write to invalid location",
        assigned_agent="WorkerAgent",
        required_tool="pdf_generator",
        category=TaskCategory.PDF_GENERATION,
        expected_output="PDF document (.pdf)",
        inputs={
            "title": "Test Title",
            # Invalid path on Windows
            "output_path": "Z:\\nonexistent_network_drive\\illegal:path\\doc.pdf",
        },
    )

    result = await adapter.execute(task)
    assert result.success is False
    assert result.error is not None
    assert result.error.error_code in ("PDF_GENERATION_FAILED", "PERMISSION_DENIED", "TOOL_EXECUTION_ERROR")
    assert result.error.error_message
