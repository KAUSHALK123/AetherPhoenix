import os
import tempfile
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from shared.contracts.browser import BrowserResult
from shared.contracts.execution import ExecutionResult
from shared.contracts.task import Task, TaskCategory
from shared.contracts.tool import ToolHealth, ToolState

from app.engine.registry import CapabilityRegistry
from app.services.artifact_storage import ArtifactStorageService
from app.tools.canva import register_canva_tool
from app.tools.canva.adapter import CanvaToolAdapter
from app.tools.canva.controller import CanvaBrowserController
from app.tools.registry import ToolRegistry


@pytest.fixture
def mock_canva_controller():
    controller = MagicMock(spec=CanvaBrowserController)
    controller.active_design_info = {
        "title": "Instagram Post",
        "topic": "Fashion Week",
        "dimensions": "1080 x 1080 px",
    }
    controller.open_canva = AsyncMock(
        return_value=BrowserResult(
            success=True, data={"url": "https://www.canva.com", "action": "open_canva"}
        )
    )
    controller.create_design = AsyncMock(
        return_value=BrowserResult(
            success=True,
            data={
                "design_type": "instagram_post",
                "width": 1080,
                "height": 1080,
                "unit": "px",
                "topic": "Fashion Week",
                "editor_open": True,
            },
        )
    )
    controller.edit_existing_design = AsyncMock(
        return_value=BrowserResult(success=True, data={"status": "editor_opened"})
    )
    controller.add_text = AsyncMock(
        return_value=BrowserResult(success=True, data={"action": "add_text"})
    )
    controller.add_element = AsyncMock(
        return_value=BrowserResult(success=True, data={"action": "add_element"})
    )
    controller.change_colors = AsyncMock(
        return_value=BrowserResult(success=True, data={"action": "change_colors"})
    )
    controller.apply_template = AsyncMock(
        return_value=BrowserResult(success=True, data={"action": "apply_template"})
    )
    return controller


@pytest.fixture
def mock_artifact_service():
    service = MagicMock(spec=ArtifactStorageService)
    service.save_artifact = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_canva_adapter_execute_open(mock_canva_controller, mock_artifact_service):
    adapter = CanvaToolAdapter(
        controller=mock_canva_controller,
        artifact_storage_service=mock_artifact_service,
    )
    task = Task(
        workflow_id=uuid4(),
        task_name="Open Canva in Browser",
        description="Launch Canva",
        required_tool="canva_tool",
        category=TaskCategory.BROWSER,
        expected_output="Open",
        inputs={"action": "open_canva"},
    )

    result = await adapter.execute(task)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.output["action"] == "open_canva"
    mock_canva_controller.open_canva.assert_called_once()


@pytest.mark.asyncio
async def test_canva_adapter_execute_create_design(
    mock_canva_controller, mock_artifact_service
):
    adapter = CanvaToolAdapter(
        controller=mock_canva_controller,
        artifact_storage_service=mock_artifact_service,
    )
    task = Task(
        workflow_id=uuid4(),
        task_name="Create Instagram Post",
        description="Create 1080x1080 design",
        required_tool="canva_tool",
        category=TaskCategory.BROWSER,
        expected_output="Design created",
        inputs={
            "action": "create_design",
            "design_type": "instagram_post",
            "width": 1080,
            "height": 1080,
            "topic": "Fashion Week",
            "text": "Exclusive Drop",
        },
    )

    result = await adapter.execute(task)

    assert result.success is True
    assert result.output["design_type"] == "instagram_post"
    mock_canva_controller.create_design.assert_called_once()
    mock_canva_controller.add_text.assert_called_once_with(
        text="Exclusive Drop",
        workflow_id=task.workflow_id,
        task_id=task.task_id,
    )


@pytest.mark.asyncio
async def test_canva_adapter_execute_export(
    mock_canva_controller, mock_artifact_service
):
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_pdf = os.path.join(tmpdir, "exported.pdf")
        with open(dummy_pdf, "wb") as f:
            f.write(b"%PDF-1.4 dummy valid pdf content")

        mock_canva_controller.export_design = AsyncMock(
            return_value=BrowserResult(
                success=True,
                data={
                    "action": "export_design",
                    "format": "pdf",
                    "filepath": dummy_pdf,
                    "filename": "exported.pdf",
                    "size_bytes": os.path.getsize(dummy_pdf),
                    "verified": True,
                },
            )
        )

        adapter = CanvaToolAdapter(
            controller=mock_canva_controller,
            artifact_storage_service=mock_artifact_service,
        )

        task = Task(
            workflow_id=uuid4(),
            task_name="Export Canva Design as PDF",
            description="Export to PDF",
            required_tool="canva_tool",
            category=TaskCategory.BROWSER,
            expected_output="PDF deliverable",
            inputs={
                "action": "export_design",
                "format": "pdf",
                "output_path": dummy_pdf,
            },
        )

        result = await adapter.execute(task)

        assert result.success is True
        assert result.output["action"] == "export_design"
        assert result.output["format"] == "pdf"
        assert result.output["verified"] is True
        assert "/api/v1/artifacts/" in result.output["download_url"]
        mock_artifact_service.save_artifact.assert_called_once()


def test_canva_tool_registration():
    tool_reg = ToolRegistry()
    cap_reg = CapabilityRegistry()
    mock_worker = MagicMock()
    mock_worker.register_adapter = MagicMock()

    tool = register_canva_tool(
        registry=tool_reg,
        cap_registry=cap_reg,
        worker_agent=mock_worker,
    )

    assert tool.name == "canva_tool"
    assert tool.status == ToolState.READY
    assert tool.health == ToolHealth.HEALTHY

    registered_tool = tool_reg.get("canva_tool")
    assert registered_tool is not None
    assert registered_tool.adapter == "app.tools.canva.adapter.CanvaToolAdapter"

    cap = cap_reg.get("canva_design")
    assert cap is not None
    assert cap.category == TaskCategory.BROWSER
    assert "canva_tool" in cap.required_tools

    assert mock_worker.register_adapter.call_count == 2
