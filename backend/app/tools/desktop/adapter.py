import time
from typing import Any, Dict, Optional

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.tools.adapter import BaseToolAdapter
from app.tools.desktop.interface import DesktopTool

logger = get_logger(__name__)


class DesktopToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging the Worker Agent and DesktopTool / MouseController.
    Executes desktop automation tasks and returns structured ExecutionResults.
    """

    def __init__(
        self,
        desktop_tool: Optional[DesktopTool] = None,
        permission_manager: Optional[Any] = None,
    ) -> None:
        self.permission_manager = permission_manager
        self.desktop_tool = desktop_tool or DesktopTool(
            permission_manager=permission_manager
        )

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a desktop task.

        Args:
            task: Task contract to execute.

        Returns:
            ExecutionResult containing execution status, output, metrics, and logs.
        """
        start_time = time.time()
        logs_captured = [f"DesktopToolAdapter executing task '{task.task_name}'"]

        # Parse inputs from task
        inputs: Dict[str, Any] = (
            task.inputs.copy() if hasattr(task, "inputs") and task.inputs else {}
        )
        action = inputs.get("action")

        # Infer action if not explicitly specified
        if not action:
            task_name_lower = task.task_name.lower()
            desc_lower = (task.description or "").lower()
            combined = f"{task_name_lower} {desc_lower}"
            if any(
                w in combined
                for w in [
                    "open notepad",
                    "notepad",
                    "vs code",
                    "vscode",
                    "open code",
                    "launch app",
                    "open app",
                    "calculator",
                    "calc",
                    "explorer",
                ]
            ):
                action = "launch_app"
                if "notepad" in combined and "app_name" not in inputs:
                    inputs["app_name"] = "notepad"
                elif (
                    "vs code" in combined
                    or "vscode" in combined
                    or "open code" in combined
                ) and "app_name" not in inputs:
                    inputs["app_name"] = "code"
                elif (
                    "calc" in combined or "calculator" in combined
                ) and "app_name" not in inputs:
                    inputs["app_name"] = "calc"
                elif (
                    "explorer" in combined or "folder" in combined
                ) and "app_name" not in inputs:
                    inputs["app_name"] = "explorer"
            elif "move" in task_name_lower:
                action = "mouse_move"
            elif "right click" in task_name_lower or "right_click" in task_name_lower:
                action = "mouse_right_click"
            elif "double click" in task_name_lower or "double_click" in task_name_lower:
                action = "mouse_double_click"
            elif "scroll" in task_name_lower:
                action = "mouse_scroll"
            elif "position" in task_name_lower or "cursor" in task_name_lower:
                action = "mouse_get_position"
            elif "click" in task_name_lower:
                action = "mouse_click"
            elif "type" in task_name_lower:
                action = "keyboard_type"
            else:
                action = "mouse_click"

        logs_captured.append(f"Resolved desktop action: {action}")

        try:
            output = self.desktop_tool.execute(
                action=action,
                params=inputs,
                workflow_id=task.workflow_id,
                task_id=task.task_id,
            )

            duration_ms = (time.time() - start_time) * 1000.0
            logs_captured.append(f"Desktop action '{action}' completed successfully")

            # Convert result to dict if model
            output_dict = output if isinstance(output, dict) else output.model_dump()

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output_dict,
                logs=logs_captured,
                metrics=ExecutionMetrics(
                    execution_time_ms=duration_ms,
                    exit_code=0,
                ),
            )

        except PermissionDeniedException as pde:
            duration_ms = (time.time() - start_time) * 1000.0
            err_msg = str(pde)
            logs_captured.append(f"Permission denied: {err_msg}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="PERMISSION_DENIED",
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(
                    execution_time_ms=duration_ms,
                    exit_code=1,
                ),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            err_code = getattr(e, "code", type(e).__name__)
            err_msg = str(e)
            logs_captured.append(f"Execution failed: {err_msg}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code=str(err_code),
                    error_message=err_msg,
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(
                    execution_time_ms=duration_ms,
                    exit_code=1,
                ),
            )
