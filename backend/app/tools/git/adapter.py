import asyncio
import logging
from typing import Any

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.tools.adapter import BaseToolAdapter
from app.tools.git.tool import GitToolInput

logger = logging.getLogger(__name__)


class GitToolAdapter(BaseToolAdapter):
    """
    Adapter for executing Git operations.
    Maps task instructions to underlying Git CLI commands.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.name = "git_tool_adapter"

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a Git operation based on the task parameters.
        """
        try:
            # Parse inputs with robust fallback and normalization
            raw_inputs = dict(task.inputs) if task.inputs else {}
            op = (
                raw_inputs.get("operation")
                or raw_inputs.get("action")
                or raw_inputs.get("command")
            )
            if not op:
                combined = f"{task.task_name} {task.description or ''}".lower()
                if "status" in combined:
                    op = "status"
                elif any(
                    k in combined
                    for k in ["log", "history", "commits", "recent changes"]
                ):
                    op = "history"
                elif "branch" in combined:
                    op = "branches"
                elif "diff" in combined:
                    op = "diff"
                elif "detect" in combined or "check repo" in combined:
                    op = "detect_repo"
                else:
                    op = "status"

            raw_inputs["operation"] = op
            if "working_directory" not in raw_inputs:
                raw_inputs["working_directory"] = (
                    raw_inputs.get("repo_path") or raw_inputs.get("path")
                )

            input_data = GitToolInput(**raw_inputs)

            operation = input_data.operation.lower()
            working_directory = input_data.working_directory

            cmd = []

            if operation == "detect_repo":
                cmd = ["git", "rev-parse", "--is-inside-work-tree"]
            elif operation == "status":
                cmd = ["git", "status", "-s"]
            elif operation == "branches":
                cmd = ["git", "branch", "-a"]
            elif operation in ("history", "log"):
                limit = input_data.limit or 10
                cmd = ["git", "log", f"-n{limit}", "--oneline"]
            elif operation == "checkout":
                if not input_data.branch:
                    raise ValueError("Branch name is required for checkout operation.")
                cmd = ["git", "checkout"]
                if input_data.create_branch:
                    cmd.append("-b")
                cmd.append(input_data.branch)
            elif operation == "stage":
                if not input_data.files:
                    raise ValueError("Files are required for stage operation.")
                cmd = ["git", "add"] + input_data.files
            elif operation == "commit":
                if not input_data.message:
                    raise ValueError("Message is required for commit operation.")
                cmd = ["git", "commit", "-m", input_data.message]
            elif operation == "diff":
                cmd = ["git", "diff"]
                if input_data.files:
                    cmd.extend(input_data.files)
            elif operation == "pull":
                cmd = ["git", "pull"]
            elif operation == "push":
                cmd = ["git", "push"]
            else:
                raise ValueError(f"Unsupported Git operation: {operation}")

            logger.info(f"Executing Git command: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
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
                    error_code="GIT_COMMAND_FAILED",
                    error_message=err_str
                    or ("Git command failed without stderr output."),
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
            logger.error(f"Git adapter execution failed: {e}", exc_info=True)
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                output={},
                error=TaskError(
                    error_code="GIT_EXECUTION_ERROR",
                    error_message=str(e),
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(),
            )
