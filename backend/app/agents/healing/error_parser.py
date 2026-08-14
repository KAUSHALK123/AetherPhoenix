import logging
from enum import Enum
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field
from shared.contracts.execution import (
    ExecutionResult,
    FailureType,
    TaskError,
    TaskFailureReport,
)

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Normalized categories of task execution errors."""

    BROWSER = "BROWSER"
    DESKTOP = "DESKTOP"
    GIT = "GIT"
    PYTHON = "PYTHON"
    POWERSHELL = "POWERSHELL"
    OCR = "OCR"
    VISION = "VISION"
    FILESYSTEM = "FILESYSTEM"
    NETWORK = "NETWORK"
    PERMISSIONS = "PERMISSIONS"
    PLUGINS = "PLUGINS"
    TOOL = "TOOL"
    UNKNOWN = "UNKNOWN"


class ParsedError(BaseModel):
    """Structured normalized error object produced by ErrorParser."""

    category: ErrorCategory = Field(default=ErrorCategory.UNKNOWN)
    normalized_code: str = Field(default="UNKNOWN_ERROR")
    raw_message: str = Field(default="")
    stack_trace: Optional[str] = None
    is_transient: bool = Field(default=False)
    original_failure_type: Optional[str] = None


class ErrorParser:
    """Error Parser component responsible for normalizing raw errors."""

    def parse(
        self,
        error_input: Union[
            TaskFailureReport,
            ExecutionResult,
            TaskError,
            Exception,
            str,
            Dict[str, Any],
        ],
        task: Optional[Any] = None,
    ) -> ParsedError:
        """Parses various error inputs into a unified ParsedError contract."""
        raw_message = ""
        stack_trace = None
        error_code = ""
        failure_type_str = None

        if isinstance(error_input, TaskFailureReport):
            raw_message = error_input.message
            failure_type_str = (
                error_input.failure_type.value
                if hasattr(error_input.failure_type, "value")
                else str(error_input.failure_type)
            )
            ctx = error_input.execution_context or {}
            err_dict = ctx.get("error") or {}
            error_code = err_dict.get("error_code", failure_type_str)
            stack_trace = err_dict.get("stack_trace")

        elif isinstance(error_input, ExecutionResult):
            if error_input.error:
                raw_message = error_input.error.error_message
                error_code = error_input.error.error_code
                stack_trace = error_input.error.stack_trace
            else:
                raw_message = f"Execution failed for task {error_input.task_id}"

        elif isinstance(error_input, TaskError):
            raw_message = error_input.error_message
            error_code = error_input.error_code
            stack_trace = error_input.stack_trace

        elif isinstance(error_input, Exception):
            raw_message = str(error_input)
            error_code = error_input.__class__.__name__

        elif isinstance(error_input, dict):
            raw_message = (
                error_input.get("message")
                or error_input.get("error_message")
                or str(error_input)
            )
            error_code = (
                error_input.get("error_code") or error_input.get("code") or ""
            )
            stack_trace = error_input.get("stack_trace")

        else:
            raw_message = str(error_input)

        msg_lower = raw_message.lower()
        code_upper = error_code.upper() if error_code else ""

        category = ErrorCategory.UNKNOWN
        normalized_code = "EXECUTION_ERROR"
        is_transient = False

        # 1. Permissions
        if (
            code_upper == "PERMISSION_DENIED"
            or failure_type_str == FailureType.PERMISSION_DENIED.value
            or "permission denied" in msg_lower
            or "access denied" in msg_lower
            or "unauthorized" in msg_lower
        ):
            category = ErrorCategory.PERMISSIONS
            normalized_code = "PERMISSION_DENIED"
            is_transient = False

        # 2. Tool Unavailable
        elif (
            code_upper in ("TOOL_NOT_FOUND", "TOOL_DISABLED", "TOOL_UNAVAILABLE")
            or failure_type_str == FailureType.TOOL_UNAVAILABLE.value
            or "tool not found" in msg_lower
            or "tool disabled" in msg_lower
        ):
            category = ErrorCategory.TOOL
            normalized_code = "TOOL_UNAVAILABLE"
            is_transient = False

        # 3. Timeout / Network
        elif (
            code_upper in ("TIMEOUT", "BROWSER_TIMEOUT", "NETWORK_TIMEOUT")
            or failure_type_str == FailureType.TIMEOUT.value
            or "timeout" in msg_lower
            or "timed out" in msg_lower
        ):
            if code_upper == "NETWORK_TIMEOUT":
                category = ErrorCategory.NETWORK
                normalized_code = "NETWORK_TIMEOUT"
            elif (
                "playwright" in msg_lower
                or "chromium" in msg_lower
                or "browser" in msg_lower
            ):
                category = ErrorCategory.BROWSER
                normalized_code = "BROWSER_TIMEOUT"
            else:
                category = ErrorCategory.NETWORK
                normalized_code = "NETWORK_TIMEOUT"
            is_transient = True

        elif (
            "network" in msg_lower
            or "connection refused" in msg_lower
            or "dns" in msg_lower
            or "socket" in msg_lower
        ):
            category = ErrorCategory.NETWORK
            normalized_code = "NETWORK_ERROR"
            is_transient = True

        # 4. Filesystem
        elif (
            "file" in msg_lower
            or "path" in msg_lower
            or "directory" in msg_lower
            or "enoent" in msg_lower
            or "permission error" in msg_lower
            or "file locked" in msg_lower
        ):
            category = ErrorCategory.FILESYSTEM
            normalized_code = "FILESYSTEM_ERROR"
            is_transient = "locked" in msg_lower or "busy" in msg_lower

        # 5. Browser / Playwright
        elif (
            "playwright" in msg_lower
            or "browser" in msg_lower
            or "chromium" in msg_lower
        ):
            category = ErrorCategory.BROWSER
            normalized_code = "BROWSER_ERROR"
            is_transient = True

        # 6. PowerShell / Desktop / Git
        elif "powershell" in msg_lower or "ps1" in msg_lower:
            category = ErrorCategory.POWERSHELL
            normalized_code = "POWERSHELL_ERROR"
            is_transient = False

        elif "git" in msg_lower or "repository" in msg_lower:
            category = ErrorCategory.GIT
            normalized_code = "GIT_ERROR"
            is_transient = False

        elif (
            "pyautogui" in msg_lower
            or "pywinauto" in msg_lower
            or "desktop" in msg_lower
        ):
            category = ErrorCategory.DESKTOP
            normalized_code = "DESKTOP_ERROR"
            is_transient = True

        elif "ocr" in msg_lower or "tesseract" in msg_lower:
            category = ErrorCategory.OCR
            normalized_code = "OCR_ERROR"
            is_transient = False

        elif "vision" in msg_lower or "image" in msg_lower:
            category = ErrorCategory.VISION
            normalized_code = "VISION_ERROR"
            is_transient = False

        elif (
            failure_type_str == FailureType.DEPENDENCY_FAILED.value
            or "dependency" in msg_lower
        ):
            category = ErrorCategory.UNKNOWN
            normalized_code = "DEPENDENCY_FAILED"
            is_transient = False

        elif (
            failure_type_str == FailureType.WORKFLOW_BLOCKED.value
            or "blocked" in msg_lower
        ):
            category = ErrorCategory.UNKNOWN
            normalized_code = "WORKFLOW_BLOCKED"
            is_transient = False

        else:
            category = ErrorCategory.UNKNOWN
            normalized_code = code_upper or "EXECUTION_ERROR"
            is_transient = any(
                sig in msg_lower
                for sig in ["temporary", "transient", "retry", "busy", "lock"]
            )

        logger.debug(
            f"ParsedError produced: category={category.value}, "
            f"code={normalized_code}, transient={is_transient}"
        )

        return ParsedError(
            category=category,
            normalized_code=normalized_code,
            raw_message=raw_message,
            stack_trace=stack_trace,
            is_transient=is_transient,
            original_failure_type=failure_type_str,
        )
