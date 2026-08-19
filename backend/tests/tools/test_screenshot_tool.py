from unittest.mock import patch
from uuid import uuid4

import pytest
from PIL import Image
from shared.contracts.execution import ExecutionResult
from shared.contracts.screenshot import (
    ScreenshotResult,
)
from shared.contracts.task import Task, TaskCategory
from shared.contracts.tool import ToolHealth, ToolState

from app.agents.worker.agent import WorkerAgent
from app.engine.registry import CapabilityRegistry
from app.tools.registry import ToolRegistry
from app.tools.screenshot.engine import ScreenshotEngine
from app.tools.screenshot.tool import (
    ScreenshotToolAdapter,
    register_screenshot_tool,
)


@pytest.fixture
def mock_img():
    return Image.new("RGB", (1280, 720), color="purple")


def test_register_screenshot_tool():
    tool_reg = ToolRegistry()
    cap_reg = CapabilityRegistry()

    tool = register_screenshot_tool(tool_reg, cap_reg)

    assert tool.name == "screenshot_engine"
    assert tool.status == ToolState.READY
    assert tool.health == ToolHealth.HEALTHY
    assert "screenshot_engine" in [t.name for t in tool_reg.list_all()]

    cap = cap_reg.get("screen_inspector")
    assert cap is not None
    assert cap.category == TaskCategory.DESKTOP
    assert "screenshot_engine" in cap.required_tools


@pytest.mark.asyncio
async def test_screenshot_adapter_execute_payload(tmp_path, mock_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)
    adapter = ScreenshotToolAdapter(engine=engine)

    with patch.object(
        engine.desktop_controller, "capture_fullscreen", return_value=mock_img
    ):
        result = await adapter.execute_payload(
            {"source": "DESKTOP", "format": "PNG"},
            workflow_id=uuid4(),
        )

        assert isinstance(result, ScreenshotResult)
        assert result.width == 1280
        assert result.height == 720
        assert result.status == "SUCCESS"

    engine.cleanup_all()


@pytest.mark.asyncio
async def test_screenshot_adapter_execute_task(tmp_path, mock_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)
    adapter = ScreenshotToolAdapter(engine=engine)

    task = Task(
        task_id=uuid4(),
        workflow_id=uuid4(),
        task_name="Capture Test Region",
        description="Captures a specific region of the desktop",
        expected_output="Valid ScreenshotResult output dictionary",
        category=TaskCategory.DESKTOP,
        required_tool="screenshot_engine",
        preconditions=[
            "source=REGION",
            "format=PNG",
            "region_x=10",
            "region_y=20",
            "region_width=500",
            "region_height=300",
        ],
    )

    with patch.object(
        engine.desktop_controller,
        "capture_region",
        return_value=Image.new("RGB", (500, 300), color="yellow"),
    ):
        exec_result: ExecutionResult = await adapter.execute(
            task,
            payload={
                "source": "REGION",
                "region": {"x": 10, "y": 20, "width": 500, "height": 300},
                "format": "PNG",
            },
        )

        assert exec_result.success is True
        assert exec_result.output["width"] == 500
        assert exec_result.output["height"] == 300
        assert exec_result.output["source"] == "REGION"
        assert exec_result.metrics.execution_time_ms > 0

    engine.cleanup_all()


@pytest.mark.asyncio
async def test_screenshot_worker_agent_integration(tmp_path, mock_img):
    tool_reg = ToolRegistry()
    register_screenshot_tool(tool_reg)

    engine = ScreenshotEngine(temp_dir=tmp_path)
    adapter = ScreenshotToolAdapter(engine=engine)

    class MockPermissionManager:
        async def check_permission(self, *args, **kwargs) -> bool:
            return True

        def validate_permission(self, *args, **kwargs) -> bool:
            return True

    worker = WorkerAgent(
        tool_registry=tool_reg, permission_manager=MockPermissionManager()
    )
    worker.register_adapter("app.tools.screenshot.tool.ScreenshotToolAdapter", adapter)

    task = Task(
        task_id=uuid4(),
        workflow_id=uuid4(),
        task_name="Capture Desktop Automation",
        description="Captures full-screen desktop screenshot",
        expected_output="Valid ScreenshotResult output dictionary",
        category=TaskCategory.DESKTOP,
        required_tool="screenshot_engine",
    )

    with patch.object(
        engine.desktop_controller, "capture_fullscreen", return_value=mock_img
    ):
        result = await worker.execute(task)

        assert result.success is True
        assert result.output["width"] == 1280
        assert result.output["height"] == 720

    engine.cleanup_all()
