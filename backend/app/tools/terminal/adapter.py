import asyncio
import logging
from typing import Any

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task

from app.core.permissions.manager import PermissionManager
from app.tools.adapter import BaseToolAdapter
from app.tools.terminal.tool import TerminalToolInput

logger = logging.getLogger(__name__)


class TerminalToolAdapter(BaseToolAdapter):
    """
    Adapter for executing terminal commands in the local environment.
    """

    def __init__(self, permission_manager: PermissionManager = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.name = "terminal_tool_adapter"
        self.permission_manager = permission_manager

    def _assess_risk(self, command: str) -> str:
        """
        Classify the risk level of the terminal command based on keywords.
        """
        cmd_lower = command.lower()

        # High risk keywords
        high_risk = ["del ", "rm ", "rmdir ", "sudo ", "drop-item ", "remove-item "]
        if any(keyword in cmd_lower for keyword in high_risk):
            return "HIGH"

        # Medium risk keywords
        medium_risk = [
            "npm install",
            "pip install",
            "docker compose up",
            "apt-get",
            "brew install",
        ]
        if any(keyword in cmd_lower for keyword in medium_risk):
            return "MEDIUM"

        # Default to LOW for pwd, dir, ls, python --version, git status, etc.
        return "LOW"

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a terminal command based on the task parameters.
        """
        try:
            # Parse inputs
            input_data = TerminalToolInput(**task.inputs)
            command = input_data.command
            working_directory = input_data.working_directory

            risk_level = self._assess_risk(command)
            logger.info(f"Assessed risk level {risk_level} for command: {command}")

            # Permission check for HIGH risk commands
            if risk_level == "HIGH" and self.permission_manager:
                is_approved = await self.permission_manager.check_permission(
                    action=f"execute terminal command: {command}",
                    permission_type=PermissionType.TERMINAL,
                )
                if not is_approved:
                    error_msg = f"Permission denied for HIGH risk command: {command}"
                    logger.warning(error_msg)
                    return ExecutionResult(
                        task_id=task.task_id,
                        workflow_id=task.workflow_id,
                        success=False,
                        output={"error": error_msg},
                        error=TaskError(
                            error_code="PERMISSION_DENIED",
                            error_message=error_msg,
                            is_recoverable=False,
                        ),
                        metrics=ExecutionMetrics(),
                    )

            logger.info(f"Executing Terminal command: {command}")

            # Execute in the shell
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            out_str = stdout.decode("utf-8", errors="replace").strip()
            err_str = stderr.decode("utf-8", errors="replace").strip()

            success = process.returncode == 0

            if not success:
                error = TaskError(
                    error_code="TERMINAL_COMMAND_FAILED",
                    error_message=err_str or "Command failed without stderr output.",
                    is_recoverable=False,
                )
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=False,
                    output={"error": err_str, "stdout": out_str},
                    error=error,
                    metrics=ExecutionMetrics(),
                )

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output={"output": out_str},
                metrics=ExecutionMetrics(),
            )

        except Exception as e:
            logger.error(f"Terminal adapter execution failed: {e}", exc_info=True)
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                output={},
                error=TaskError(
                    error_code="TERMINAL_EXECUTION_ERROR",
                    error_message=str(e),
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(),
            )
