"""
AetherPhoenix — Centralized Exception Hierarchy
================================================
Provides reusable, structured exception types for every module in the platform.

All exceptions carry:
  - code     : a namespaced string identifier (e.g. "VALIDATION_ERROR")
  - message  : a human-readable description safe to surface to callers
  - details  : optional supplementary context (stack trace fragment, field name, …)

Design rules (from 07_IMPLEMENTATION_GUIDE.md):
  - Catch expected exceptions; log unexpected ones.
  - Return structured errors — never expose raw stack traces to users.
  - No retry logic here (Infrastructure only per issue constraints).
"""

from __future__ import annotations

from typing import Any


class AetherPhoenixException(Exception):
    """
    Base exception for the entire AetherPhoenix platform.

    All domain-specific exceptions must inherit from this class so that
    a single except clause can catch any platform-level error while
    preserving structured metadata.

    Parameters
    ----------
    message:
        Human-readable error description.
    code:
        Namespaced string error code (e.g. ``"RUNTIME_ERROR"``).
        Defaults to ``"AETHER_PHOENIX_ERROR"``.
    details:
        Optional supplementary context: field name, upstream response, etc.

    Raises
    ------
    AetherPhoenixException
        Always raised directly or via a subclass.
    """

    def __init__(
        self,
        message: str,
        code: str = "AETHER_PHOENIX_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.code: str = code
        self.details: Any = details

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"code={self.code!r}, "
            f"message={self.message!r}, "
            f"details={self.details!r})"
        )


# ---------------------------------------------------------------------------
# Runtime Exceptions
# ---------------------------------------------------------------------------


class RuntimeException(AetherPhoenixException):
    """
    Raised when an unexpected failure occurs during runtime execution.

    Suitable for wrapping lower-level errors that escape expected paths
    (e.g. OS errors, network failures, unhandled agent state transitions).

    HTTP mapping: 500 Internal Server Error.

    Parameters
    ----------
    message:
        Description of the runtime failure.
    code:
        Error code. Defaults to ``"RUNTIME_ERROR"``.
    details:
        Optional context (e.g. the original exception message).
    """

    def __init__(
        self,
        message: str,
        code: str = "RUNTIME_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class AgentRuntimeException(RuntimeException):
    """
    Raised when an agent (Planner, Worker, Supervisor, Healing) fails
    during its internal execution cycle.

    HTTP mapping: 500 Internal Server Error.

    Parameters
    ----------
    message:
        Description of the agent failure.
    code:
        Error code. Defaults to ``"AGENT_RUNTIME_ERROR"``.
    details:
        Optional context (e.g. agent name, workflow id).
    """

    def __init__(
        self,
        message: str,
        code: str = "AGENT_RUNTIME_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class WorkflowRuntimeException(RuntimeException):
    """
    Raised when a workflow-level failure occurs that is not recoverable
    by the Healing Agent.

    HTTP mapping: 500 Internal Server Error.

    Parameters
    ----------
    message:
        Description of the workflow failure.
    code:
        Error code. Defaults to ``"WORKFLOW_RUNTIME_ERROR"``.
    details:
        Optional context (e.g. workflow id, failed task id).
    """

    def __init__(
        self,
        message: str,
        code: str = "WORKFLOW_RUNTIME_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


# ---------------------------------------------------------------------------
# Validation Exceptions
# ---------------------------------------------------------------------------


class ValidationException(AetherPhoenixException):
    """
    Raised when input data or a Pydantic schema fails validation.

    Aligns with HTTP 422 Unprocessable Entity as defined in
    ``05_API_SPEC.md``.

    Parameters
    ----------
    message:
        Description of what failed validation.
    code:
        Error code. Defaults to ``"VALIDATION_ERROR"``.
    details:
        Optional context (e.g. field name, received value, constraint).
    """

    def __init__(
        self,
        message: str,
        code: str = "VALIDATION_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class SchemaValidationException(ValidationException):
    """
    Raised when a Pydantic model cannot be constructed from the
    provided data.

    HTTP mapping: 422 Unprocessable Entity.

    Parameters
    ----------
    message:
        Description of the schema mismatch.
    code:
        Error code. Defaults to ``"SCHEMA_VALIDATION_ERROR"``.
    details:
        Optional context (e.g. Pydantic validation error list).
    """

    def __init__(
        self,
        message: str,
        code: str = "SCHEMA_VALIDATION_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class InputValidationException(ValidationException):
    """
    Raised when user-supplied input (API request body, query params, etc.)
    does not meet the required constraints.

    HTTP mapping: 400 Bad Request.

    Parameters
    ----------
    message:
        Description of the invalid input.
    code:
        Error code. Defaults to ``"INPUT_VALIDATION_ERROR"``.
    details:
        Optional context (e.g. field name, expected format).
    """

    def __init__(
        self,
        message: str,
        code: str = "INPUT_VALIDATION_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


# ---------------------------------------------------------------------------
# Permission Exceptions
# ---------------------------------------------------------------------------


class PermissionException(AetherPhoenixException):
    """
    Raised when an operation is rejected due to insufficient permissions.

    Aligns with HTTP 403 Forbidden as defined in ``05_API_SPEC.md``.

    Parameters
    ----------
    message:
        Description of the permission failure.
    code:
        Error code. Defaults to ``"PERMISSION_ERROR"``.
    details:
        Optional context (e.g. required permission, requested resource).
    """

    def __init__(
        self,
        message: str,
        code: str = "PERMISSION_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class PermissionDeniedException(PermissionException):
    """
    Raised when the user explicitly denies a permission request, or when
    the Permission Manager rejects an operation.

    HTTP mapping: 403 Forbidden.

    Parameters
    ----------
    message:
        Description of the denied permission.
    code:
        Error code. Defaults to ``"PERMISSION_DENIED"``.
    details:
        Optional context (e.g. tool name, required scope).
    """

    def __init__(
        self,
        message: str,
        code: str = "PERMISSION_DENIED",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class UnauthorizedException(PermissionException):
    """
    Raised when a request is made without valid authentication credentials.

    HTTP mapping: 401 Unauthorized.

    Parameters
    ----------
    message:
        Description of the authentication failure.
    code:
        Error code. Defaults to ``"UNAUTHORIZED"``.
    details:
        Optional context (e.g. token expiry, missing header).
    """

    def __init__(
        self,
        message: str,
        code: str = "UNAUTHORIZED",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


# ---------------------------------------------------------------------------
# Tool Exceptions
# ---------------------------------------------------------------------------


class ToolException(AetherPhoenixException):
    """
    Raised when a tool plugin fails during execution.

    Tools are plugin-based execution capabilities (Browser, Git, PowerShell,
    OCR, etc.) as defined in ``00_ARCHITECTURE_PRINCIPLES.md`` Principle 11.

    HTTP mapping: 500 Internal Server Error.

    Parameters
    ----------
    message:
        Description of the tool failure.
    code:
        Error code. Defaults to ``"TOOL_ERROR"``.
    details:
        Optional context (e.g. tool name, exit code, stderr output).
    """

    def __init__(
        self,
        message: str,
        code: str = "TOOL_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class ToolNotFoundException(ToolException):
    """
    Raised when a required tool plugin is not installed or not discoverable
    by the Capability Manager.

    HTTP mapping: 404 Not Found.

    Parameters
    ----------
    message:
        Description of which tool could not be found.
    code:
        Error code. Defaults to ``"TOOL_NOT_FOUND"``.
    details:
        Optional context (e.g. tool name, required version).
    """

    def __init__(
        self,
        message: str,
        code: str = "TOOL_NOT_FOUND",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class ToolExecutionException(ToolException):
    """
    Raised when a tool plugin is available but fails during its
    execution cycle.

    HTTP mapping: 500 Internal Server Error.

    Parameters
    ----------
    message:
        Description of the execution failure.
    code:
        Error code. Defaults to ``"TOOL_EXECUTION_ERROR"``.
    details:
        Optional context (e.g. tool name, input payload, error output).
    """

    def __init__(
        self,
        message: str,
        code: str = "TOOL_EXECUTION_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Base
    "AetherPhoenixException",
    # Runtime
    "RuntimeException",
    "AgentRuntimeException",
    "WorkflowRuntimeException",
    # Validation
    "ValidationException",
    "SchemaValidationException",
    "InputValidationException",
    # Permission
    "PermissionException",
    "PermissionDeniedException",
    "UnauthorizedException",
    # Tool
    "ToolException",
    "ToolNotFoundException",
    "ToolExecutionException",
]
