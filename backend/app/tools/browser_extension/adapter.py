import logging
import time
from typing import Optional

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.core.permissions.manager import PermissionManager
from app.tools.adapter import BaseToolAdapter
from app.tools.browser_extension.controller import (
    BrowserExtensionActionError,
    BrowserExtensionController,
)

logger = logging.getLogger(__name__)


class BrowserExtensionAdapter(BaseToolAdapter):
    """
    Adapter bridging Worker Agent tasks to the BrowserExtensionController.
    Implements the BaseToolAdapter interface for browser extension automation tasks.
    """

    def __init__(
        self,
        controller: Optional[BrowserExtensionController] = None,
        permission_manager: Optional[PermissionManager] = None,
    ):
        self.controller = controller or BrowserExtensionController(
            permission_manager=permission_manager
        )

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a browser extension task by parsing task inputs and delegating
        to BrowserExtensionController.
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
            if not action:
                raise ValueError("Task is missing required 'action' parameter")

            logs.append(f"Executing browser extension action: '{action}'")

            if action in ("detect_active_tab", "get_active_tab"):
                res = await self.controller.detect_active_tab(
                    workflow_id=workflow_id, task_id=task_id
                )

            elif action == "read_page_info":
                res = await self.controller.read_page_info(
                    workflow_id=workflow_id, task_id=task_id
                )

            elif action == "navigate":
                url = inputs.get("url")
                timeout_ms = inputs.get("timeout_ms", 30000.0)
                if not url:
                    raise ValueError("URL is required for 'navigate' action")
                logs.append(f"Navigating to: {url}")
                res = await self.controller.navigate(
                    url=url,
                    timeout_ms=timeout_ms,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif action == "open_new_tab":
                url = inputs.get("url", "about:blank")
                active = inputs.get("active", True)
                logs.append(f"Opening new tab with URL: {url}")
                res = await self.controller.open_new_tab(
                    url=url,
                    active=active,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif action == "interact":
                selector = inputs.get("selector")
                interaction_action = (
                    inputs.get("interaction_action")
                    or inputs.get("action_type")
                    or "click"
                )
                value = inputs.get("value")
                timeout_ms = inputs.get("timeout_ms", 10000.0)

                if not selector:
                    raise ValueError("Selector is required for 'interact' action")
                logs.append(f"Interacting with element '{selector}' (action={interaction_action})")
                res = await self.controller.interact(
                    selector=selector,
                    action=interaction_action,
                    value=value,
                    timeout_ms=timeout_ms,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif action == "extract_content":
                include_html = inputs.get("include_html", False)
                selector = inputs.get("selector")
                logs.append(f"Extracting content (include_html={include_html})")
                res = await self.controller.extract_content(
                    include_html=include_html,
                    selector=selector,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            else:
                raise ValueError(f"Unsupported browser extension action: '{action}'")

            if not res.success:
                raise BrowserExtensionActionError(res.error or "Action failed in browser extension")

            duration_ms = (time.time() - start_time) * 1000.0
            logs.append(f"Browser extension action '{action}' completed successfully")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=res.data or {},
                logs=logs,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(f"BrowserExtensionAdapter execution failed: {e}")
            logs.append(f"Error: {e}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="BROWSER_EXTENSION_ERROR",
                    error_message=str(e),
                    is_recoverable=True,
                ),
                logs=logs,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms),
            )
