from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw
from shared.contracts.ocr import (
    OCRBoundingBox,
    OCRRequest,
    OCRResult,
    OCRTextSegment,
)
from shared.contracts.permission import PermissionType
from shared.contracts.planner import PlannerOutput, PlannerRequest
from shared.contracts.task import Task, TaskCategory

from app.agents.planner.agent import PlannerAgent
from app.core.exceptions import PermissionDeniedException
from app.tools.ocr.adapter import OCRToolAdapter
from app.tools.ocr.engine import OCREngine, OCRError
from app.tools.ocr.tool import register_ocr_tool
from app.tools.registry import ToolRegistry


@pytest.fixture
def temp_image_path(tmp_path):
    """Creates a temporary sample image file for OCR testing."""
    image_file = tmp_path / "sample_screenshot.png"
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Error 404 Not Found", fill=(0, 0, 0))
    img.save(image_file, format="PNG")
    return str(image_file)


class MockPermissionManager:
    def __init__(self, granted: bool = True):
        self.granted = granted

    def check_permission(self, action, permission_type, workflow_id=None, context=None):
        return self.granted


@pytest.mark.asyncio
async def test_ocr_contracts():
    req = OCRRequest(filepath="test.png", language="eng", extract_boxes=True)
    assert req.filepath == "test.png"
    assert req.language == "eng"
    assert req.extract_boxes is True

    res = OCRResult(
        extracted_text="Hello World",
        source_artifact="test.png",
        confidence=0.95,
        segments=[
            OCRTextSegment(
                text="Hello World",
                confidence=0.95,
                bounding_box=OCRBoundingBox(x=0, y=0, width=100, height=20),
            )
        ],
        image_info={"width": 100, "height": 20, "format": "PNG"},
    )
    assert res.extracted_text == "Hello World"
    assert res.confidence == 0.95
    assert len(res.segments) == 1
    assert res.segments[0].text == "Hello World"
    assert res.status == "SUCCESS"


def test_register_ocr_tool():
    registry = ToolRegistry()
    tool = register_ocr_tool(registry)

    assert tool.name == "ocr"
    assert tool.adapter == "OCRToolAdapter"
    assert PermissionType.FILE_SYSTEM.value in tool.required_permissions
    assert registry.get("ocr") == tool


@pytest.mark.asyncio
async def test_ocr_engine_extract_text(temp_image_path):
    engine = OCREngine()
    req = OCRRequest(filepath=temp_image_path, extract_boxes=True)
    result = await engine.extract_text(req)

    assert result.status == "SUCCESS"
    assert result.source_artifact == str(Path(temp_image_path).resolve())
    assert result.image_info["width"] == 300
    assert result.image_info["height"] == 100
    assert result.image_info["format"] == "PNG"
    assert result.confidence > 0.0


@pytest.mark.asyncio
async def test_ocr_engine_file_not_found():
    engine = OCREngine()
    req = OCRRequest(filepath="non_existent_file_12345.png")

    with pytest.raises(FileNotFoundError):
        await engine.extract_text(req)


@pytest.mark.asyncio
async def test_ocr_engine_unsupported_format(tmp_path):
    invalid_file = tmp_path / "test.xyz"
    invalid_file.write_text("dummy content")

    engine = OCREngine()
    req = OCRRequest(filepath=str(invalid_file))

    with pytest.raises(OCRError, match="Unsupported image/document extension"):
        await engine.extract_text(req)


@pytest.mark.asyncio
async def test_ocr_engine_permission_denied(temp_image_path):
    mock_pm = MockPermissionManager(granted=False)
    engine = OCREngine(permission_manager=mock_pm)
    req = OCRRequest(filepath=temp_image_path)

    with pytest.raises(PermissionDeniedException):
        await engine.extract_text(req)


@pytest.mark.asyncio
async def test_ocr_tool_adapter_success(temp_image_path):
    adapter = OCRToolAdapter()
    wf_id = uuid4()
    task = Task(
        workflow_id=wf_id,
        task_name="Extract Error Messages",
        description="Extract errors from screenshot",
        required_tool="ocr",
        category=TaskCategory.OCR,
        expected_output="Extracted error text",
        inputs={"filepath": temp_image_path},
    )

    result = await adapter.execute(task)

    assert result.success is True
    assert result.output is not None
    assert result.output["source_artifact"] == str(Path(temp_image_path).resolve())
    assert result.error is None
    assert result.metrics.exit_code == 0


@pytest.mark.asyncio
async def test_ocr_tool_adapter_missing_file():
    adapter = OCRToolAdapter()
    wf_id = uuid4()
    task = Task(
        workflow_id=wf_id,
        task_name="Extract Error Messages",
        description="Extract errors from missing file",
        required_tool="ocr",
        category=TaskCategory.OCR,
        expected_output="Extracted error text",
        inputs={"filepath": "missing_screenshot_9999.png"},
    )

    result = await adapter.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "FILE_NOT_FOUND"
    assert result.metrics.exit_code == 1


@pytest.mark.asyncio
async def test_ocr_tool_adapter_missing_input_parameter():
    adapter = OCRToolAdapter()
    wf_id = uuid4()
    task = Task(
        workflow_id=wf_id,
        task_name="Extract Error Messages",
        description="Extract errors without inputs",
        required_tool="ocr",
        category=TaskCategory.OCR,
        expected_output="Extracted error text",
        inputs={},
    )

    result = await adapter.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "INVALID_INPUT"


def test_planner_ocr_capability_discovery_and_decomposition():
    planner = PlannerAgent()
    req = PlannerRequest(
        session_id=str(uuid4()),
        message="Read this screenshot and extract all the error messages.",
    )

    res = planner.process_request(req)

    assert res.status == "ready"
    planner_output = PlannerOutput.model_validate_json(res.reply)
    ocr_tasks = [
        t
        for t in planner_output.tasks
        if t.category == TaskCategory.OCR or t.required_tool == "ocr"
    ]
    assert len(ocr_tasks) > 0
    assert any(t.required_tool == "ocr" for t in ocr_tasks)
