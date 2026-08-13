import logging
import os
from typing import Any, Dict, List, Optional

from shared.contracts.artifact import Artifact
from shared.contracts.execution import (
    ExecutionResult,
    FailureType,
    TaskError,
    TaskFailureReport,
)
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

from app.core.config import get_config
from app.core.exceptions import (
    AetherPhoenixException,
    AgentRuntimeException,
    PermissionDeniedException,
    RuntimeException,
    ToolExecutionException,
    ToolNotFoundException,
    ValidationException,
    WorkflowRuntimeException,
)

logger = logging.getLogger(__name__)


class FailureDetectorService:
    """
    Service responsible for detecting task execution failures,
    classifying them into appropriate failure categories, and identifying retryability.
    """

    def __init__(self, default_timeout_seconds: Optional[int] = None) -> None:
        config = get_config()
        self.default_timeout_seconds = default_timeout_seconds or getattr(
            config, "EXECUTION_TIMEOUT_SECONDS", 300
        )

    def check_failure(
        self,
        task: Task,
        result: ExecutionResult,
        state: SharedWorkflowState,
    ) -> Optional[TaskFailureReport]:
        """
        Evaluates task execution result and workflow state to detect failures.
        Returns a TaskFailureReport if a failure is detected, else None.
        """
        # 1. Check for workflow blocked state
        if self._is_workflow_blocked(state):
            return self._create_report(
                task=task,
                failure_type=FailureType.WORKFLOW_BLOCKED,
                message=(
                    "Workflow became blocked: no tasks are queued or running "
                    "but uncompleted tasks remain."
                ),
                retryability=False,
                execution_context={"state_tasks": list(state.tasks.keys())},
            )

        # 2. Check for dependency failure
        dep_fail_msg = self._check_dependency_failures(task, state)
        if dep_fail_msg:
            return self._create_report(
                task=task,
                failure_type=FailureType.DEPENDENCY_FAILED,
                message=dep_fail_msg,
                retryability=False,
                execution_context={"dependencies": task.dependencies},
            )

        # 3. Check for permission denied
        if self._is_permission_denied(result):
            return self._create_report(
                task=task,
                failure_type=FailureType.PERMISSION_DENIED,
                message=(
                    result.error.error_message if result.error else "Permission denied."
                ),
                retryability=False,
                execution_context={
                    "error": result.error.model_dump() if result.error else None
                },
            )

        # 4. Check for tool unavailable
        if self._is_tool_unavailable(result):
            return self._create_report(
                task=task,
                failure_type=FailureType.TOOL_UNAVAILABLE,
                message=(
                    result.error.error_message
                    if result.error
                    else f"Tool '{task.required_tool}' is unavailable."
                ),
                retryability=False,
                execution_context={
                    "required_tool": task.required_tool,
                    "error": result.error.model_dump() if result.error else None,
                },
            )

        # 5. Check for execution timeout
        if self._is_timeout(task, result):
            exec_time = (
                result.metrics.execution_time_ms / 1000.0 if result.metrics else 0.0
            )
            timeout_limit = (
                task.estimated_duration_seconds or self.default_timeout_seconds
            )
            return self._create_report(
                task=task,
                failure_type=FailureType.TIMEOUT,
                message=(
                    f"Task exceeded configured timeout of {timeout_limit} "
                    f"seconds (took {exec_time:.2f}s)."
                ),
                retryability=True,
                execution_context={
                    "execution_time_seconds": exec_time,
                    "timeout_limit_seconds": timeout_limit,
                },
            )

        # 6. Check for tool returns an error
        if self._is_tool_error(result):
            return self._create_report(
                task=task,
                failure_type=FailureType.TOOL_ERROR,
                message=(
                    result.error.error_message
                    if result.error
                    else "Tool returned an error."
                ),
                retryability=self._determine_retryability(
                    FailureType.TOOL_ERROR, result.error
                ),
                execution_context={
                    "error": result.error.model_dump() if result.error else None
                },
            )

        # 7. Check for unexpected execution exception or explicit worker failure
        if not result.success:
            err_msg = (
                result.error.error_message
                if result.error
                else "Worker reported explicit failure."
            )
            is_unexpected = result.error and result.error.error_code in (
                "EXECUTION_FAILED",
                "UNEXPECTED_EXCEPTION",
            )
            failure_type = (
                FailureType.UNEXPECTED_EXCEPTION
                if is_unexpected
                else FailureType.WORKER_FAILURE
            )
            return self._create_report(
                task=task,
                failure_type=failure_type,
                message=err_msg,
                retryability=self._determine_retryability(failure_type, result.error),
                execution_context={
                    "error": result.error.model_dump() if result.error else None
                },
            )

        # 8. Check for expected output missing
        if self._is_output_missing(task, result):
            return self._create_report(
                task=task,
                failure_type=FailureType.OUTPUT_MISSING,
                message=f"Expected output '{task.expected_output}' is missing.",
                retryability=False,
                execution_context={
                    "expected_output": task.expected_output,
                    "actual_output": result.output,
                    "artifacts": [a.filepath for a in result.artifacts],
                },
            )

        # 9. Check for artifact validation failure
        artifact_fail_msg = self._check_artifact_failures(result.artifacts)
        if artifact_fail_msg:
            return self._create_report(
                task=task,
                failure_type=FailureType.ARTIFACT_VALIDATION_FAILED,
                message=artifact_fail_msg,
                retryability=False,
                execution_context={
                    "artifacts": [a.model_dump(mode="json") for a in result.artifacts]
                },
            )

        return None

    def map_to_exception(self, report: TaskFailureReport) -> AetherPhoenixException:
        """
        Maps a structured failure report to the corresponding project exception.
        """
        message = report.message
        details = {
            "failure_id": str(report.failure_id),
            "task_id": str(report.task_id),
            "workflow_id": str(report.workflow_id),
            "failure_type": report.failure_type.value,
            "execution_context": report.execution_context,
        }

        if report.failure_type == FailureType.PERMISSION_DENIED:
            return PermissionDeniedException(message=message, details=details)
        elif report.failure_type == FailureType.TOOL_UNAVAILABLE:
            return ToolNotFoundException(message=message, details=details)
        elif report.failure_type == FailureType.TOOL_ERROR:
            return ToolExecutionException(message=message, details=details)
        elif report.failure_type in (
            FailureType.OUTPUT_MISSING,
            FailureType.ARTIFACT_VALIDATION_FAILED,
        ):
            return ValidationException(message=message, details=details)
        elif report.failure_type in (
            FailureType.DEPENDENCY_FAILED,
            FailureType.WORKFLOW_BLOCKED,
        ):
            return WorkflowRuntimeException(message=message, details=details)
        elif report.failure_type == FailureType.WORKER_FAILURE:
            return AgentRuntimeException(message=message, details=details)
        else:
            return RuntimeException(message=message, details=details)

    def _create_report(
        self,
        task: Task,
        failure_type: FailureType,
        message: str,
        retryability: bool,
        execution_context: Dict[str, Any],
    ) -> TaskFailureReport:
        """Helper to instantiate TaskFailureReport."""
        return TaskFailureReport(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            failure_type=failure_type,
            message=message,
            retryability=retryability,
            execution_context=execution_context,
        )

    def _is_workflow_blocked(self, state: SharedWorkflowState) -> bool:
        """Detects if workflow execution has deadlocked or become blocked."""
        # Only check running workflows
        if state.metadata.status != "RUNNING" and state.metadata.status != "Running":
            return False

        # If there are active operations running or in queue, workflow is not blocked
        if len(state.running_tasks) > 0 or len(state.execution_queue) > 0:
            return False

        # Look for remaining tasks that haven't reached a terminal state
        uncompleted_tasks = [
            t
            for t in state.tasks.values()
            if t.status
            not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]

        return len(uncompleted_tasks) > 0

    def _check_dependency_failures(
        self, task: Task, state: SharedWorkflowState
    ) -> Optional[str]:
        """Verifies if any parent dependency task has failed or is missing."""
        for dep_id in task.dependencies:
            dep_task = state.tasks.get(dep_id)
            if not dep_task:
                return f"Dependency '{dep_id}' was not found in workflow state."
            if dep_task.status == TaskStatus.FAILED:
                return (
                    f"Required parent dependency '{dep_task.task_name}' "
                    f"({dep_id}) failed."
                )
            if dep_task.status == TaskStatus.CANCELLED:
                return (
                    f"Required parent dependency '{dep_task.task_name}' "
                    f"({dep_id}) was cancelled."
                )
        return None

    def _is_permission_denied(self, result: ExecutionResult) -> bool:
        """Detects permission enforcement failures."""
        if result.error and result.error.error_code == "PERMISSION_DENIED":
            return True
        if result.error and "permission denied" in result.error.error_message.lower():
            return True
        return False

    def _is_tool_unavailable(self, result: ExecutionResult) -> bool:
        """Detects if required tools are not configured or disabled."""
        if result.error and result.error.error_code in (
            "TOOL_NOT_FOUND",
            "TOOL_DISABLED",
            "TOOL_UNAVAILABLE",
        ):
            return True
        return False

    def _is_timeout(self, task: Task, result: ExecutionResult) -> bool:
        """Detects if task execution duration exceeded timeout boundaries."""
        timeout_limit = task.estimated_duration_seconds or self.default_timeout_seconds
        if result.metrics and result.metrics.execution_time_ms:
            exec_time_seconds = result.metrics.execution_time_ms / 1000.0
            if exec_time_seconds > timeout_limit:
                return True
        return False

    def _is_tool_error(self, result: ExecutionResult) -> bool:
        """Checks if tool execution reported error codes."""
        if result.error:
            code = result.error.error_code
            if code not in ("TOOL_NOT_FOUND", "TOOL_DISABLED") and (
                code.startswith("TOOL_") or "tool" in code.lower()
            ):
                return True
        return False

    def _is_output_missing(self, task: Task, result: ExecutionResult) -> bool:
        """Validates presence of requested outputs or matching artifacts."""
        if not task.expected_output:
            return False

        expected = task.expected_output.strip()

        # Check physical artifacts list first
        for artifact in result.artifacts:
            if expected == artifact.name or expected in artifact.filepath:
                return False
            # Check filename base
            filename = os.path.basename(artifact.filepath)
            if (
                expected == filename
                or os.path.splitext(expected)[0] == os.path.splitext(filename)[0]
            ):
                return False

        # Check raw output dict
        if isinstance(result.output, dict):
            if expected in result.output:
                return False
            for val in result.output.values():
                if isinstance(val, str) and expected.lower() in val.lower():
                    return False
                if str(val) == expected:
                    return False

        return True

    def _check_artifact_failures(self, artifacts: List[Artifact]) -> Optional[str]:
        """Validates system artifact physical properties and readability."""
        for artifact in artifacts:
            path = artifact.filepath
            if not path:
                return f"Artifact '{artifact.name}' contains no filepath context."

            # Verify file exists
            if not os.path.exists(path):
                return f"Artifact file '{path}' does not exist on disk."

            # Check size is non-zero
            try:
                if os.path.getsize(path) == 0:
                    return f"Artifact file '{path}' is empty (0 bytes)."
            except OSError as exc:
                return f"Cannot retrieve size of artifact '{path}': {str(exc)}"

            # Verify readability
            try:
                with open(path, "rb") as f:
                    f.read(1024)
            except OSError as exc:
                return f"Artifact file '{path}' is not readable: {str(exc)}"

        return None

    def _determine_retryability(
        self, failure_type: FailureType, error: Optional[TaskError]
    ) -> bool:
        """Determines retry viability without execution."""
        # Non-retryable types
        if failure_type in (
            FailureType.PERMISSION_DENIED,
            FailureType.TOOL_UNAVAILABLE,
            FailureType.DEPENDENCY_FAILED,
            FailureType.WORKFLOW_BLOCKED,
        ):
            return False

        # Respect explicit worker decisions
        if error and not error.is_recoverable:
            return False

        # Timeout is always retryable
        if failure_type == FailureType.TIMEOUT:
            return True

        # Heuristic checks on messages for transient patterns
        if error and error.error_message:
            msg = error.error_message.lower()
            transient_signals = [
                "timeout",
                "network",
                "connection",
                "locked",
                "temporary",
                "busy",
                "rate limit",
                "try again",
                "transient",
            ]
            if any(signal in msg for signal in transient_signals):
                return True

        # Default to True for tool errors and worker failures unless unrecoverable
        return True
