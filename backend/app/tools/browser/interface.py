import logging
import time
from typing import Any, Optional

from shared.contracts.capability import Capability
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task, TaskCategory
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.engine.registry import CapabilityRegistry
from app.tools.adapter import BaseToolAdapter
from app.tools.browser.controller import BrowserActionError, BrowserController
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_browser_capability(
    tool_registry: ToolRegistry,
    cap_registry: Optional[CapabilityRegistry] = None,
    worker_agent: Optional[Any] = None,
    permission_manager: Optional[Any] = None,
):
    """Registers the browser tool and capability into the system."""
    browser_tool = Tool(
        name="browser_automation",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="browser_adapter",
        dependencies=["playwright"],
        required_permissions=[
            PermissionType.BROWSER_ACCESS.value,
            PermissionType.INTERNET.value,
        ],
    )
    tool_registry.register(browser_tool)

    if cap_registry is not None:
        browser_cap = Capability(
            name="web_searcher",
            description="Searches and extracts content from the web",
            category=TaskCategory.BROWSER,
            required_tools=["browser_automation"],
        )
        cap_registry.register(browser_cap)

    if worker_agent is not None:
        adapter = BrowserAdapter(permission_manager=permission_manager)
        worker_agent.register_adapter("browser_adapter", adapter)
        worker_agent.register_adapter(
            "app.tools.browser.interface.BrowserAdapter", adapter
        )


class BrowserAdapter(BaseToolAdapter):
    """
    Adapter that connects the Worker Agent to the Browser Controller.
    Implements the BaseToolAdapter interface.
    """

    def __init__(
        self,
        controller: Optional[BrowserController] = None,
        permission_manager: Optional[Any] = None,
    ):
        self.controller = controller or BrowserController(
            permission_manager=permission_manager
        )

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a browser task by interpreting its inputs and calling the controller.
        """
        start_time = time.time()
        logs = []
        inputs = (
            getattr(task, "input_parameters", {}) or getattr(task, "inputs", {}) or {}
        )
        action = inputs.get("action")
        workflow_id = task.workflow_id
        task_id = task.task_id

        try:
            if action == "start_session":
                logs.append("Starting browser session...")
                res = await self.controller.start_session(
                    workflow_id=workflow_id, task_id=task_id
                )
                output = res.data

            elif action == "close_session":
                logs.append("Closing browser session...")
                res = await self.controller.close_session(
                    workflow_id=workflow_id, task_id=task_id
                )
                output = {"status": "closed"}

            elif action == "navigate":
                url = inputs.get("url")
                timeout = inputs.get("timeout_ms", 30000.0)
                if not url:
                    raise ValueError("URL is required for navigation.")
                logs.append(f"Navigating to {url}...")
                res = await self.controller.navigate(
                    url,
                    timeout_ms=timeout,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data

            elif action == "extract_content":
                include_html = inputs.get("include_html", False)
                logs.append(f"Extracting content (include_html={include_html})...")
                res = await self.controller.extract_content(
                    include_html=include_html,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data

            elif action == "interact":
                selector = inputs.get("selector")
                interaction_action = (
                    inputs.get("interaction_action")
                    or inputs.get("action_type")
                    or "click"
                )
                value = inputs.get("value")
                timeout = inputs.get("timeout_ms", 10000.0)

                if not selector or not interaction_action:
                    raise ValueError(
                        "selector and interaction_action are required for interaction."
                    )

                logs.append(
                    f"Interacting with {selector} (action={interaction_action})..."
                )
                res = await self.controller.interact(
                    selector=selector,
                    action=interaction_action,
                    value=value,
                    timeout_ms=timeout,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data

            elif action in ("capture_screenshot", "screenshot"):
                output_path = inputs.get("output_path")
                full_page = inputs.get("full_page", False)
                clip = inputs.get("clip")
                image_type = inputs.get("image_type", "png")
                quality = inputs.get("quality")
                logs.append(f"Capturing screenshot (full_page={full_page})...")
                res = await self.controller.capture_screenshot(
                    output_path=output_path,
                    full_page=full_page,
                    clip=clip,
                    image_type=image_type,
                    quality=quality,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data

            else:
                raise ValueError(f"Unknown browser action: {action}")

            if res and not res.success:
                raise BrowserActionError(res.error)

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output,
                logs=logs,
                metrics=ExecutionMetrics(
                    execution_time_ms=(time.time() - start_time) * 1000.0
                ),
            )

        except Exception as e:
            logger.error(f"BrowserAdapter execution failed: {e}")
            logs.append(f"Error: {e}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(error_code="BROWSER_ERROR", error_message=str(e)),
                logs=logs,
                metrics=ExecutionMetrics(
                    execution_time_ms=(time.time() - start_time) * 1000.0
                ),
            )


class BrowserTool:
    """
    Deprecated: Kept for backward compatibility with existing tests.
    Use BrowserAdapter or BrowserController instead.
    """

    def __init__(self, permission_checker=None):
        self.permission_checker = permission_checker
        # If a custom legacy permission_checker is provided,
        # do not bind default PermissionManager
        self.controller = BrowserController(
            permission_manager=False if permission_checker else None
        )

    def _check_permission(self, permission: PermissionType) -> None:
        if self.permission_checker and not self.permission_checker(permission):
            raise PermissionError(
                f"Action denied: Missing {permission.value} permission."
            )

    async def start_session(self) -> None:
        self._check_permission(PermissionType.BROWSER_ACCESS)
        res = await self.controller.start_session()
        if not res.success:
            raise RuntimeError(res.error)

    async def close_session(self) -> None:
        res = await self.controller.close_session()
        if not res.success:
            raise RuntimeError(res.error)

    async def navigate(self, url: str) -> bool:
        self._check_permission(PermissionType.INTERNET)
        res = await self.controller.navigate(url)
        if not res.success:
            return False
        return True

    async def extract_content(self, include_html: bool = False) -> str:
        res = await self.controller.extract_content(include_html=include_html)
        if not res.success:
            return ""
        return res.data.get("content", "")

    async def interact(self, selector: str, action: str, value: str = None) -> bool:
        res = await self.controller.interact(
            selector=selector, action=action, value=value
        )
        return res.success

    async def capture_screenshot(
        self,
        output_path: Optional[str] = None,
        full_page: bool = False,
        clip: Optional[dict] = None,
        image_type: str = "png",
        quality: Optional[int] = None,
    ) -> bytes:
        self._check_permission(PermissionType.BROWSER_ACCESS)
        res = await self.controller.capture_screenshot(
            output_path=output_path,
            full_page=full_page,
            clip=clip,
            image_type=image_type,
            quality=quality,
        )
        if not res.success:
            raise RuntimeError(res.error)
        return res.data["screenshot_bytes"]
