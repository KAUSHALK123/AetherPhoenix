import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator
from uuid import UUID, uuid4

from shared.contracts.execution_log import (
    ExecutionPhase,
    ExecutionStatus,
    WorkerExecutionLog,
)
from shared.contracts.task import Task

from app.core.logging.logger import StructuredLogger, get_logger
from app.core.logging.sanitizer import sanitize_log_data

logger = get_logger("AetherPhoenix.WorkerExecution")


class WorkerExecutionLogger:
    """
    Dedicated Execution Logger for Worker Agent operations.
    Wraps StructuredLogger to emit granular, traceable execution logs
    with context binding (execution_id, correlation_id, workflow_id,
    task_id, tool_name).
    """

    def __init__(
        self,
        workflow_id: UUID,
        task_id: UUID,
        task_name: str,
        tool_name: str,
        correlation_id: str | None = None,
        execution_id: UUID | None = None,
    ) -> None:
        self.execution_id = execution_id or uuid4()
        self.correlation_id = correlation_id or str(uuid4())
        self.workflow_id = workflow_id
        self.task_id = task_id
        self.task_name = task_name
        self.tool_name = tool_name

        self.context_data: dict[str, Any] = {
            "execution_id": str(self.execution_id),
            "correlation_id": self.correlation_id,
            "workflow_id": str(self.workflow_id),
            "task_id": str(self.task_id),
            "task_name": self.task_name,
            "tool_name": self.tool_name,
        }

        self.logger: StructuredLogger = logger.bind(**self.context_data)

    @classmethod
    def from_task(
        cls,
        task: Task,
        workflow_id: UUID | None = None,
        correlation_id: str | None = None,
        execution_id: UUID | None = None,
    ) -> "WorkerExecutionLogger":
        """Factory to build WorkerExecutionLogger directly from a Task."""
        wf_id = workflow_id or task.workflow_id
        tool = task.required_tool or "default_tool"
        return cls(
            workflow_id=wf_id,
            task_id=task.task_id,
            task_name=task.task_name,
            tool_name=tool,
            correlation_id=correlation_id,
            execution_id=execution_id,
        )

    def _create_log_event(
        self,
        phase: ExecutionPhase,
        status: ExecutionStatus,
        duration_ms: float = 0.0,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkerExecutionLog:
        """Constructs a WorkerExecutionLog object with sanitized payloads."""
        sanit_inputs = sanitize_log_data(inputs) if inputs else {}
        sanit_outputs = sanitize_log_data(outputs) if outputs else {}
        sanit_meta = sanitize_log_data(metadata) if metadata else {}

        return WorkerExecutionLog(
            execution_id=self.execution_id,
            correlation_id=self.correlation_id,
            workflow_id=self.workflow_id,
            task_id=self.task_id,
            task_name=self.task_name,
            tool_name=self.tool_name,
            phase=phase,
            status=status,
            duration_ms=round(duration_ms, 2),
            inputs=sanit_inputs,
            outputs=sanit_outputs,
            error_code=error_code,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc),
            metadata=sanit_meta,
        )

    def log_task_start(
        self, inputs: dict[str, Any] | None = None
    ) -> WorkerExecutionLog:
        """Logs task execution start."""
        event = self._create_log_event(
            phase=ExecutionPhase.TASK_START,
            status=ExecutionStatus.STARTED,
            inputs=inputs,
        )
        self.logger.info(
            f"Worker Task started: '{self.task_name}' (tool: '{self.tool_name}')",
            phase=event.phase.value,
            status=event.status.value,
            inputs=event.inputs,
        )
        return event

    def log_tool_selected(
        self, tool_name: str | None = None
    ) -> WorkerExecutionLog:
        """Logs tool selection phase."""
        selected_tool = tool_name or self.tool_name
        self.tool_name = selected_tool
        event = self._create_log_event(
            phase=ExecutionPhase.TOOL_SELECTION,
            status=ExecutionStatus.IN_PROGRESS,
            metadata={"selected_tool": selected_tool},
        )
        self.logger.info(
            f"Tool selected: '{selected_tool}' for task '{self.task_name}'",
            phase=event.phase.value,
            status=event.status.value,
            selected_tool=selected_tool,
        )
        return event

    def log_tool_start(
        self,
        tool_name: str | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> WorkerExecutionLog:
        """Logs tool execution start."""
        t_name = tool_name or self.tool_name
        event = self._create_log_event(
            phase=ExecutionPhase.TOOL_EXECUTION,
            status=ExecutionStatus.TOOL_STARTED,
            inputs=inputs,
        )
        self.logger.info(
            f"Executing tool '{t_name}'",
            phase=event.phase.value,
            status=event.status.value,
            inputs=event.inputs,
        )
        return event

    def log_tool_complete(
        self,
        tool_name: str | None = None,
        duration_ms: float = 0.0,
        outputs: dict[str, Any] | None = None,
    ) -> WorkerExecutionLog:
        """Logs successful tool execution."""
        t_name = tool_name or self.tool_name
        event = self._create_log_event(
            phase=ExecutionPhase.TOOL_EXECUTION,
            status=ExecutionStatus.TOOL_COMPLETED,
            duration_ms=duration_ms,
            outputs=outputs,
        )
        self.logger.info(
            f"Tool '{t_name}' completed in {duration_ms:.2f}ms",
            phase=event.phase.value,
            status=event.status.value,
            duration_ms=round(duration_ms, 2),
            outputs=event.outputs,
        )
        return event

    def log_tool_failure(
        self,
        tool_name: str | None = None,
        duration_ms: float = 0.0,
        error_code: str = "TOOL_EXECUTION_ERROR",
        error_message: str = "Tool execution failed",
    ) -> WorkerExecutionLog:
        """Logs tool execution failure."""
        t_name = tool_name or self.tool_name
        event = self._create_log_event(
            phase=ExecutionPhase.TOOL_EXECUTION,
            status=ExecutionStatus.TOOL_FAILED,
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
        )
        self.logger.error(
            f"Tool '{t_name}' failed after {duration_ms:.2f}ms: "
            f"[{error_code}] {error_message}",
            phase=event.phase.value,
            status=event.status.value,
            duration_ms=round(duration_ms, 2),
            error_code=error_code,
            error_message=error_message,
        )
        return event

    def log_task_complete(
        self,
        duration_ms: float,
        outputs: dict[str, Any] | None = None,
        artifacts_count: int = 0,
    ) -> WorkerExecutionLog:
        """Logs overall task execution completion."""
        event = self._create_log_event(
            phase=ExecutionPhase.TASK_COMPLETE,
            status=ExecutionStatus.COMPLETED,
            duration_ms=duration_ms,
            outputs=outputs,
            metadata={"artifacts_count": artifacts_count},
        )
        self.logger.info(
            f"Task '{self.task_name}' completed in {duration_ms:.2f}ms "
            f"({artifacts_count} artifacts)",
            phase=event.phase.value,
            status=event.status.value,
            duration_ms=round(duration_ms, 2),
            artifacts_count=artifacts_count,
        )
        return event

    def log_task_failure(
        self,
        duration_ms: float,
        error_code: str = "TASK_EXECUTION_ERROR",
        error_message: str = "Task execution failed",
    ) -> WorkerExecutionLog:
        """Logs overall task execution failure."""
        event = self._create_log_event(
            phase=ExecutionPhase.TASK_FAILED,
            status=ExecutionStatus.FAILED,
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
        )
        self.logger.error(
            f"Task '{self.task_name}' failed after {duration_ms:.2f}ms: "
            f"[{error_code}] {error_message}",
            phase=event.phase.value,
            status=event.status.value,
            duration_ms=round(duration_ms, 2),
            error_code=error_code,
            error_message=error_message,
        )
        return event

    @contextmanager
    def track_execution(
        self, inputs: dict[str, Any] | None = None
    ) -> Generator["WorkerExecutionLogger", None, None]:
        """
        Context manager to track task start, duration, and outcome.
        """
        start_time = time.time()
        self.log_task_start(inputs=inputs)
        try:
            yield self
            duration_ms = (time.time() - start_time) * 1000.0
            self.log_task_complete(duration_ms=duration_ms)
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000.0
            err_code = getattr(exc, "code", "EXECUTION_ERROR")
            self.log_task_failure(
                duration_ms=duration_ms,
                error_code=str(err_code),
                error_message=str(exc),
            )
            raise
