import time
from typing import Any, Dict, Optional, Union
from uuid import UUID

from shared.contracts.capability import Capability
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.permission import PermissionType
from shared.contracts.screenshot import (
    CaptureRegion,
    CaptureSource,
    ImageFormat,
    ScreenshotRequest,
    ScreenshotResult,
)
from shared.contracts.task import Task, TaskCategory
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.engine.registry import CapabilityRegistry
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry
from app.tools.screenshot.engine import ScreenshotEngine

logger = get_logger(__name__)


class ScreenshotToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging Worker Agent tasks with the ScreenshotEngine.
    Supports both direct payload execution and Task-based workflow execution.
    """

    def __init__(
        self,
        engine: Optional[ScreenshotEngine] = None,
        permission_manager: Optional[Any] = None,
        browser_controller: Optional[Any] = None,
    ) -> None:
        self.engine = engine or ScreenshotEngine(
            permission_manager=permission_manager,
            browser_controller=browser_controller,
        )

    async def execute_payload(
        self,
        payload: Union[Dict[str, Any], ScreenshotRequest],
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> ScreenshotResult:
        """
        Executes a screenshot capture from a payload dict or ScreenshotRequest.

        Args:
            payload: Parameters matching ScreenshotRequest.
            workflow_id: Optional workflow ID.
            task_id: Optional task ID.

        Returns:
            ScreenshotResult object.
        """
        if isinstance(payload, ScreenshotRequest):
            request = payload
        else:
            request = ScreenshotRequest.model_validate(payload)

        if workflow_id and not request.workflow_id:
            request.workflow_id = workflow_id
        if task_id and not request.task_id:
            request.task_id = task_id

        return await self.engine.capture(request)

    async def execute(
        self,
        task: Task,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ExecutionResult:
        """
        Executes a task assigned to the screenshot engine tool.

        Args:
            task: The atomic Task object.
            payload: Optional parameter dictionary overriding or specifying inputs.

        Returns:
            ExecutionResult containing the screenshot metadata and status.
        """
        start_time = time.time()
        logs = [f"Starting screenshot execution for task {task.task_id}"]

        try:
            # Extract parameters from payload or task attributes
            params: Dict[str, Any] = {}
            if payload:
                params.update(payload)
            if hasattr(task, "metadata") and isinstance(task.metadata, dict):
                params.update(task.metadata)
            if kwargs:
                params.update(kwargs)

            # Map input parameters to request fields
            source_val = params.get("source", CaptureSource.DESKTOP)
            format_val = params.get("format", ImageFormat.PNG)
            quality_val = params.get("quality")
            output_path_val = params.get("output_path")
            full_page_val = params.get("full_page", False)

            region_obj = None
            if "region" in params and params["region"]:
                reg = params["region"]
                if isinstance(reg, dict):
                    region_obj = CaptureRegion(**reg)
                elif isinstance(reg, (tuple, list)) and len(reg) == 4:
                    region_obj = CaptureRegion(
                        x=reg[0], y=reg[1], width=reg[2], height=reg[3]
                    )
                elif isinstance(reg, CaptureRegion):
                    region_obj = reg

            req = ScreenshotRequest(
                source=source_val,
                region=region_obj,
                format=format_val,
                quality=quality_val,
                output_path=output_path_val,
                full_page=full_page_val,
                workflow_id=task.workflow_id,
                task_id=task.task_id,
                metadata={"task_name": task.task_name},
            )

            result: ScreenshotResult = await self.engine.capture(req)
            elapsed_ms = (time.time() - start_time) * 1000.0
            logs.append(
                f"Captured screenshot successfully: {result.file_name} "
                f"({result.width}x{result.height}, {result.size_bytes} bytes)"
            )

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=result.model_dump(mode="json"),
                logs=logs,
                metrics=ExecutionMetrics(execution_time_ms=elapsed_ms),
            )

        except PermissionDeniedException as pde:
            elapsed_ms = (time.time() - start_time) * 1000.0
            logs.append(f"Permission denied: {str(pde)}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="PERMISSION_DENIED",
                    error_message=str(pde),
                ),
                logs=logs,
                metrics=ExecutionMetrics(execution_time_ms=elapsed_ms),
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000.0
            logs.append(f"Screenshot execution failed: {str(e)}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="SCREENSHOT_CAPTURE_ERROR",
                    error_message=str(e),
                ),
                logs=logs,
                metrics=ExecutionMetrics(execution_time_ms=elapsed_ms),
            )


def register_screenshot_tool(
    registry: ToolRegistry,
    capability_registry: Optional[CapabilityRegistry] = None,
) -> Tool:
    """
    Registers the Screenshot Engine tool and its capability into registries.

    Args:
        registry: The ToolRegistry instance.
        capability_registry: Optional CapabilityRegistry instance.

    Returns:
        The registered Tool contract object.
    """
    screenshot_tool = Tool(
        name="screenshot_engine",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.screenshot.tool.ScreenshotToolAdapter",
        dependencies=["pyautogui", "pillow", "playwright"],
        required_permissions=[
            PermissionType.SCREEN_CAPTURE.value,
            PermissionType.DESKTOP_AUTOMATION.value,
        ],
    )
    registry.register(screenshot_tool)
    logger.info("Successfully registered 'screenshot_engine' in ToolRegistry.")

    if capability_registry:
        screen_cap = Capability(
            name="screen_inspector",
            description=(
                "Captures controlled desktop and browser "
                "screenshots for visual inspection"
            ),
            category=TaskCategory.DESKTOP,
            required_tools=["screenshot_engine"],
        )
        capability_registry.register(screen_cap)
        logger.info("Successfully registered 'screen_inspector' capability.")

    return screenshot_tool
