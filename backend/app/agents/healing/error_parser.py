from __future__ import annotations

import traceback
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field
from shared.contracts.execution import (
    ExecutionResult,
    FailureType,
    TaskError,
    TaskFailureReport,
)

from app.agents.healing.models import (
    ErrorCategory,
    ErrorSeverity,
    ErrorSource,
    NormalizedError,
)
from app.core.exceptions import (
    AetherPhoenixException,
    AgentRuntimeException,
    PermissionDeniedException,
    PermissionException,
    ToolExecutionException,
    ToolNotFoundException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ParsedError(BaseModel):
    """Structured normalized error object produced by ErrorParser."""

    category: ErrorCategory = Field(default=ErrorCategory.UNKNOWN)
    normalized_code: str = Field(default="UNKNOWN_ERROR")
    raw_message: str = Field(default="")
    stack_trace: Optional[str] = None
    is_transient: bool = Field(default=False)
    original_failure_type: Optional[str] = None


class ErrorParser:
    """
    Error Parser component for the Healing Agent.

    Parses raw errors from diverse layers into a normalized, structured model
    (:class:`NormalizedError`) containing source/category/severity
    classifications, retryability, context, and original error information.
    """

    def parse(
        self,
        raw_error: Any,
        context: Optional[Dict[str, Any]] = None,
        task: Optional[Any] = None,
        *args: Any,
        **kwargs: Any,
    ) -> NormalizedError:
        """
        Main entrypoint for parsing raw error inputs.

        Parameters
        ----------
        raw_error:
            The raw error input (Exception, TaskFailureReport, ExecutionResult,
            TaskError, Dict, str, or unknown object).
        context:
            Optional supplementary context dictionary provided by caller.

        Returns
        -------
        NormalizedError
            A fully normalized, classified, and structured error instance.
        """
        try:
            merged_context = {**(context or {})}
            if task is not None:
                merged_context["task"] = task
            return self._parse_safe(raw_error, merged_context)
        except Exception as parse_exc:
            logger.error(
                "ErrorParser encountered an unexpected exception while "
                f"parsing raw error: {parse_exc}",
                exc_info=True,
            )
            # Safe fallback: never crash during raw error normalization
            return NormalizedError(
                source=ErrorSource.UNKNOWN,
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.HIGH,
                is_retryable=False,
                message=f"Failed to parse raw error safely: {str(raw_error)}",
                code="PARSER_FALLBACK_UNKNOWN",
                context={
                    **(context or {}),
                    "parser_error": str(parse_exc),
                },
                original_error=raw_error,
            )

    def _parse_safe(
        self,
        raw_error: Any,
        caller_context: Dict[str, Any],
    ) -> NormalizedError:
        """Internal safe implementation of parsing logic."""
        if raw_error is None:
            return NormalizedError(
                source=ErrorSource.UNKNOWN,
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.HIGH,
                is_retryable=False,
                message="Received None as raw error input.",
                code="NULL_ERROR_INPUT",
                context=caller_context,
                original_error=None,
            )

        # 1. Extract message, code, stack trace, and initial context metadata
        (
            extracted_msg,
            extracted_code,
            extracted_stack,
            extracted_ctx,
        ) = self._extract_metadata(raw_error)

        merged_context = {**extracted_ctx, **caller_context}
        if extracted_stack and "stack_trace" not in merged_context:
            merged_context["stack_trace"] = extracted_stack

        # 2. Perform classification
        source, category, severity, is_retryable = self._classify(
            raw_error=raw_error,
            message=extracted_msg,
            code=extracted_code,
            context=merged_context,
        )

        logger.debug(
            f"Parsed error -> category={category.value}, source={source.value}, "
            f"severity={severity.value}, is_retryable={is_retryable}"
        )

        return NormalizedError(
            source=source,
            category=category,
            severity=severity,
            is_retryable=is_retryable,
            message=extracted_msg,
            code=extracted_code,
            context=merged_context,
            original_error=raw_error,
        )

    def _extract_metadata(
        self,
        raw_error: Any,
    ) -> Tuple[str, str, Optional[str], Dict[str, Any]]:
        """Extracts message, code, stack trace, and context from raw errors."""
        message = ""
        code = "UNKNOWN_ERROR"
        stack_trace: Optional[str] = None
        context: Dict[str, Any] = {}

        # Type 1: TaskFailureReport (from Supervisor)
        if isinstance(raw_error, TaskFailureReport):
            message = (
                raw_error.message or f"Task Failure: {raw_error.failure_type.value}"
            )
            code = raw_error.failure_type.value
            context.update(raw_error.execution_context)
            context["task_id"] = str(raw_error.task_id)
            context["workflow_id"] = str(raw_error.workflow_id)
            context["failure_id"] = str(raw_error.failure_id)
            context["failure_type"] = raw_error.failure_type.value
            context["report_retryability"] = raw_error.retryability

        # Type 2: ExecutionResult (from Worker)
        elif isinstance(raw_error, ExecutionResult):
            context["task_id"] = str(raw_error.task_id)
            context["workflow_id"] = str(raw_error.workflow_id)
            context["execution_id"] = str(raw_error.execution_id)
            if raw_error.error:
                message = raw_error.error.error_message
                code = raw_error.error.error_code
                stack_trace = raw_error.error.stack_trace
                context["is_recoverable"] = raw_error.error.is_recoverable
            else:
                message = "Execution failed without detailed TaskError payload."
                code = "EXECUTION_RESULT_FAILED"

        # Type 3: TaskError
        elif isinstance(raw_error, TaskError):
            message = raw_error.error_message
            code = raw_error.error_code
            stack_trace = raw_error.stack_trace
            context["is_recoverable"] = raw_error.is_recoverable

        # Type 4: Custom AetherPhoenix Exception
        elif isinstance(raw_error, AetherPhoenixException):
            message = raw_error.message
            code = raw_error.code
            if isinstance(raw_error.details, dict):
                context.update(raw_error.details)
            elif raw_error.details is not None:
                context["details"] = str(raw_error.details)
            stack_trace = "".join(traceback.format_exception(raw_error))

        # Type 5: Base Exception
        elif isinstance(raw_error, Exception):
            message = f"{type(raw_error).__name__}: {str(raw_error)}"
            code = type(raw_error).__name__.upper()
            stack_trace = "".join(traceback.format_exception(raw_error))

            # Extract subprocess attributes if present (e.g. CalledProcessError)
            if hasattr(raw_error, "returncode"):
                context["exit_code"] = getattr(raw_error, "returncode")
            if hasattr(raw_error, "cmd"):
                context["cmd"] = str(getattr(raw_error, "cmd"))
            if hasattr(raw_error, "output"):
                context["output"] = str(getattr(raw_error, "output"))
            if hasattr(raw_error, "stderr"):
                context["stderr"] = str(getattr(raw_error, "stderr"))

        # Type 6: Dictionary
        elif isinstance(raw_error, dict):
            message = (
                str(raw_error.get("message"))
                or str(raw_error.get("error"))
                or str(raw_error.get("error_message"))
                or str(raw_error)
            )
            code = (
                str(raw_error.get("code"))
                or str(raw_error.get("error_code"))
                or "DICT_ERROR"
            )
            stack_trace = raw_error.get("stack_trace") or raw_error.get("traceback")
            context.update(
                {
                    k: v
                    for k, v in raw_error.items()
                    if k
                    not in ("message", "error", "code", "error_code", "stack_trace")
                }
            )

        # Type 7: String or Primitives
        else:
            message = str(raw_error)
            code = "RAW_STRING_ERROR"

        return message, code, stack_trace, context

    def _classify(
        self,
        raw_error: Any,
        message: str,
        code: str,
        context: Dict[str, Any],
    ) -> Tuple[ErrorSource, ErrorCategory, ErrorSeverity, bool]:
        """Classifies an error into (Source, Category, Severity, IsRetryable)."""
        msg_lower = message.lower()
        code_upper = code.upper()

        # 1. Timeout Errors
        if (
            isinstance(raw_error, TimeoutError)
            or "timeout" in msg_lower
            or "timed out" in msg_lower
            or "deadline exceeded" in msg_lower
            or "TIMEOUT" in code_upper
            or context.get("failure_type") == FailureType.TIMEOUT.value
        ):
            source = ErrorSource.SYSTEM
            if any(
                term in msg_lower or term in str(context).lower()
                for term in ("playwright", "browser", "page", "selector", "chrome")
            ):
                source = ErrorSource.BROWSER
            elif any(
                term in msg_lower or term in str(context).lower()
                for term in ("http", "connection", "socket", "url", "network", "dns")
            ):
                source = ErrorSource.NETWORK
            elif any(
                term in msg_lower or term in str(context).lower()
                for term in ("powershell", "cmd", "script")
            ):
                source = ErrorSource.POWERSHELL

            return source, ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM, True

        # 2. Permission Denied Errors
        if (
            isinstance(
                raw_error,
                (PermissionDeniedException, PermissionException, PermissionError),
            )
            or "permission denied" in msg_lower
            or "access denied" in msg_lower
            or "user rejected" in msg_lower
            or "unauthorized" in msg_lower
            or "forbidden" in msg_lower
            or "403" in msg_lower
            or "PERMISSION" in code_upper
            or context.get("failure_type") == FailureType.PERMISSION_DENIED.value
            or context.get("status_code") == 403
        ):
            return (
                ErrorSource.PERMISSION,
                ErrorCategory.PERMISSION_DENIED,
                ErrorSeverity.HIGH,
                False,
            )

        # 3. File Not Found Errors
        if (
            isinstance(raw_error, FileNotFoundError)
            or "file not found" in msg_lower
            or "no such file or directory" in msg_lower
            or "path does not exist" in msg_lower
            or "cannot find file" in msg_lower
            or "FILE_NOT_FOUND" in code_upper
        ):
            return (
                ErrorSource.FILESYSTEM,
                ErrorCategory.FILE_NOT_FOUND,
                ErrorSeverity.MEDIUM,
                False,
            )

        # 4. Tool Unavailable Errors
        if (
            isinstance(raw_error, ToolNotFoundException)
            or "tool unavailable" in msg_lower
            or "tool not found" in msg_lower
            or "tool plugin missing" in msg_lower
            or "unregistered tool" in msg_lower
            or "TOOL_UNAVAILABLE" in code_upper
            or "TOOL_NOT_FOUND" in code_upper
            or context.get("failure_type") == FailureType.TOOL_UNAVAILABLE.value
        ):
            return (
                ErrorSource.TOOL,
                ErrorCategory.TOOL_UNAVAILABLE,
                ErrorSeverity.HIGH,
                False,
            )

        # 5. Network Failures
        if (
            "connection refused" in msg_lower
            or "connection reset" in msg_lower
            or "dns lookup failed" in msg_lower
            or "network error" in msg_lower
            or "http error" in msg_lower
            or "http 502" in msg_lower
            or "http 503" in msg_lower
            or "http 504" in msg_lower
            or "host unreachable" in msg_lower
            or "socket error" in msg_lower
            or "httperror" in msg_lower
            or "NETWORK" in code_upper
        ):
            return (
                ErrorSource.NETWORK,
                ErrorCategory.NETWORK_ERROR,
                ErrorSeverity.MEDIUM,
                True,
            )

        # 6. Invalid Artifact Failures
        if (
            "invalid artifact" in msg_lower
            or "artifact validation failed" in msg_lower
            or "corrupted artifact" in msg_lower
            or "missing required artifact" in msg_lower
            or "output missing" in msg_lower
            or "ARTIFACT" in code_upper
            or context.get("failure_type")
            in (
                FailureType.ARTIFACT_VALIDATION_FAILED.value,
                FailureType.OUTPUT_MISSING.value,
            )
        ):
            return (
                ErrorSource.WORKER,
                ErrorCategory.INVALID_ARTIFACT,
                ErrorSeverity.MEDIUM,
                True,
            )

        # 7. Worker / Process / Tool Execution Errors
        if (
            isinstance(raw_error, (ToolExecutionException, AgentRuntimeException))
            or "EXECUTION" in code_upper
            or "TOOL_ERROR" in code_upper
            or "WORKER_FAILURE" in code_upper
            or context.get("exit_code") is not None
            or context.get("failure_type")
            in (FailureType.WORKER_FAILURE.value, FailureType.TOOL_ERROR.value)
        ):
            source = ErrorSource.WORKER
            if (
                "powershell" in msg_lower
                or "cmd" in msg_lower
                or "powershell" in str(context).lower()
            ):
                source = ErrorSource.POWERSHELL
            elif (
                "browser" in msg_lower
                or "playwright" in msg_lower
                or "browser" in str(context).lower()
            ):
                source = ErrorSource.BROWSER
            elif "tool" in msg_lower or "plugin" in msg_lower:
                source = ErrorSource.TOOL

            # Check if supervisor / context explicitly set retryability
            is_retryable = context.get(
                "report_retryability", context.get("is_recoverable", True)
            )
            return (
                source,
                ErrorCategory.EXECUTION_ERROR,
                ErrorSeverity.MEDIUM,
                is_retryable,
            )

        # 8. System Runtime Errors
        if (
            "system" in msg_lower
            or "memory" in msg_lower
            or "os error" in msg_lower
            or "RUNTIME" in code_upper
        ):
            return (
                ErrorSource.SYSTEM,
                ErrorCategory.SYSTEM_ERROR,
                ErrorSeverity.HIGH,
                False,
            )

        # 9. Unknown / Unmapped Errors
        return ErrorSource.UNKNOWN, ErrorCategory.UNKNOWN, ErrorSeverity.HIGH, False


__all__ = [
    "ErrorCategory",
    "ErrorParser",
    "ParsedError",
]
