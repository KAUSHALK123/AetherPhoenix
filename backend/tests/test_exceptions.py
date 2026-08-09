"""
Unit Tests — Shared Exceptions & Error Handling
================================================
Tests the centralized exception hierarchy and error response schemas.

Coverage:
  - Base exception attributes (code, message, details)
  - Exception inheritance chain
  - Every concrete exception family (Runtime, Validation, Permission, Tool)
  - Default error codes
  - Custom error codes and details
  - ErrorDetail schema serialization / deserialization
  - ErrorResponse schema serialization / deserialization
  - ErrorResponse.from_exception() factory method
  - Timestamp and request_id auto-population
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.core.exceptions import (
    AetherPhoenixException,
    AgentRuntimeException,
    InputValidationException,
    PermissionDeniedException,
    PermissionException,
    RuntimeException,
    SchemaValidationException,
    ToolException,
    ToolExecutionException,
    ToolNotFoundException,
    UnauthorizedException,
    ValidationException,
    WorkflowRuntimeException,
)
from app.schemas.error import ErrorDetail, ErrorResponse

# ---------------------------------------------------------------------------
# Base Exception
# ---------------------------------------------------------------------------


class TestAetherPhoenixException:
    """Tests for the root AetherPhoenixException base class."""

    def test_default_code(self) -> None:
        """Default code is AETHER_PHOENIX_ERROR when not provided."""
        exc = AetherPhoenixException(message="base error")
        assert exc.code == "AETHER_PHOENIX_ERROR"

    def test_custom_code(self) -> None:
        """Custom code is stored correctly."""
        exc = AetherPhoenixException(message="custom", code="CUSTOM_CODE")
        assert exc.code == "CUSTOM_CODE"

    def test_message_stored(self) -> None:
        """Message attribute is accessible."""
        exc = AetherPhoenixException(message="something went wrong")
        assert exc.message == "something went wrong"

    def test_message_equals_str(self) -> None:
        """str(exc) returns the message (via Exception.__str__)."""
        exc = AetherPhoenixException(message="hello")
        assert str(exc) == "hello"

    def test_details_defaults_to_none(self) -> None:
        """Details defaults to None when not provided."""
        exc = AetherPhoenixException(message="no details")
        assert exc.details is None

    def test_details_stored(self) -> None:
        """Details can be any type."""
        exc = AetherPhoenixException(
            message="error", details={"field": "goal", "received": None}
        )
        assert exc.details == {"field": "goal", "received": None}

    def test_is_exception(self) -> None:
        """AetherPhoenixException is a standard Python Exception."""
        exc = AetherPhoenixException(message="test")
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """Can be raised and caught via its own type."""
        with pytest.raises(AetherPhoenixException) as exc_info:
            raise AetherPhoenixException(message="raised")
        assert exc_info.value.message == "raised"

    def test_repr(self) -> None:
        """__repr__ includes class name, code, message, details."""
        exc = AetherPhoenixException(message="msg", code="CODE", details="ctx")
        r = repr(exc)
        assert "AetherPhoenixException" in r
        assert "CODE" in r
        assert "msg" in r
        assert "ctx" in r


# ---------------------------------------------------------------------------
# Runtime Exceptions
# ---------------------------------------------------------------------------


class TestRuntimeException:
    """Tests for RuntimeException and its subclasses."""

    def test_default_code(self) -> None:
        exc = RuntimeException(message="runtime failure")
        assert exc.code == "RUNTIME_ERROR"

    def test_is_aether_phoenix_exception(self) -> None:
        exc = RuntimeException(message="failure")
        assert isinstance(exc, AetherPhoenixException)

    def test_can_be_raised_and_caught_as_base(self) -> None:
        with pytest.raises(AetherPhoenixException):
            raise RuntimeException(message="runtime")

    def test_custom_code_and_details(self) -> None:
        exc = RuntimeException(
            message="disk full", code="DISK_FULL", details="path=/tmp"
        )
        assert exc.code == "DISK_FULL"
        assert exc.details == "path=/tmp"


class TestAgentRuntimeException:
    """Tests for AgentRuntimeException."""

    def test_default_code(self) -> None:
        exc = AgentRuntimeException(message="agent crashed")
        assert exc.code == "AGENT_RUNTIME_ERROR"

    def test_inherits_from_runtime_exception(self) -> None:
        exc = AgentRuntimeException(message="agent crashed")
        assert isinstance(exc, RuntimeException)
        assert isinstance(exc, AetherPhoenixException)

    def test_caught_as_runtime_exception(self) -> None:
        with pytest.raises(RuntimeException):
            raise AgentRuntimeException(message="planner failed")


class TestWorkflowRuntimeException:
    """Tests for WorkflowRuntimeException."""

    def test_default_code(self) -> None:
        exc = WorkflowRuntimeException(message="workflow broken")
        assert exc.code == "WORKFLOW_RUNTIME_ERROR"

    def test_inherits_from_runtime_exception(self) -> None:
        exc = WorkflowRuntimeException(message="broken")
        assert isinstance(exc, RuntimeException)

    def test_caught_as_base(self) -> None:
        with pytest.raises(AetherPhoenixException):
            raise WorkflowRuntimeException(message="unrecoverable")


# ---------------------------------------------------------------------------
# Validation Exceptions
# ---------------------------------------------------------------------------


class TestValidationException:
    """Tests for ValidationException and its subclasses."""

    def test_default_code(self) -> None:
        exc = ValidationException(message="invalid input")
        assert exc.code == "VALIDATION_ERROR"

    def test_is_aether_phoenix_exception(self) -> None:
        exc = ValidationException(message="invalid")
        assert isinstance(exc, AetherPhoenixException)

    def test_details_carries_field_info(self) -> None:
        exc = ValidationException(message="Field required", details={"field": "goal"})
        assert exc.details["field"] == "goal"


class TestSchemaValidationException:
    """Tests for SchemaValidationException."""

    def test_default_code(self) -> None:
        exc = SchemaValidationException(message="schema mismatch")
        assert exc.code == "SCHEMA_VALIDATION_ERROR"

    def test_inherits_from_validation_exception(self) -> None:
        exc = SchemaValidationException(message="bad schema")
        assert isinstance(exc, ValidationException)
        assert isinstance(exc, AetherPhoenixException)

    def test_caught_as_validation_exception(self) -> None:
        with pytest.raises(ValidationException):
            raise SchemaValidationException(message="bad schema")


class TestInputValidationException:
    """Tests for InputValidationException."""

    def test_default_code(self) -> None:
        exc = InputValidationException(message="bad request body")
        assert exc.code == "INPUT_VALIDATION_ERROR"

    def test_inherits_from_validation_exception(self) -> None:
        exc = InputValidationException(message="bad input")
        assert isinstance(exc, ValidationException)

    def test_caught_as_base(self) -> None:
        with pytest.raises(AetherPhoenixException):
            raise InputValidationException(message="missing field")


# ---------------------------------------------------------------------------
# Permission Exceptions
# ---------------------------------------------------------------------------


class TestPermissionException:
    """Tests for PermissionException and its subclasses."""

    def test_default_code(self) -> None:
        exc = PermissionException(message="access denied")
        assert exc.code == "PERMISSION_ERROR"

    def test_is_aether_phoenix_exception(self) -> None:
        exc = PermissionException(message="denied")
        assert isinstance(exc, AetherPhoenixException)


class TestPermissionDeniedException:
    """Tests for PermissionDeniedException."""

    def test_default_code(self) -> None:
        exc = PermissionDeniedException(message="user rejected permission")
        assert exc.code == "PERMISSION_DENIED"

    def test_inherits_from_permission_exception(self) -> None:
        exc = PermissionDeniedException(message="denied")
        assert isinstance(exc, PermissionException)
        assert isinstance(exc, AetherPhoenixException)

    def test_caught_as_permission_exception(self) -> None:
        with pytest.raises(PermissionException):
            raise PermissionDeniedException(message="denied")

    def test_details_carry_tool_name(self) -> None:
        exc = PermissionDeniedException(
            message="PowerShell execution denied",
            details={"tool": "powershell"},
        )
        assert exc.details["tool"] == "powershell"


class TestUnauthorizedException:
    """Tests for UnauthorizedException."""

    def test_default_code(self) -> None:
        exc = UnauthorizedException(message="missing token")
        assert exc.code == "UNAUTHORIZED"

    def test_inherits_from_permission_exception(self) -> None:
        exc = UnauthorizedException(message="no token")
        assert isinstance(exc, PermissionException)

    def test_caught_as_base(self) -> None:
        with pytest.raises(AetherPhoenixException):
            raise UnauthorizedException(message="expired token")


# ---------------------------------------------------------------------------
# Tool Exceptions
# ---------------------------------------------------------------------------


class TestToolException:
    """Tests for ToolException and its subclasses."""

    def test_default_code(self) -> None:
        exc = ToolException(message="tool failed")
        assert exc.code == "TOOL_ERROR"

    def test_is_aether_phoenix_exception(self) -> None:
        exc = ToolException(message="failed")
        assert isinstance(exc, AetherPhoenixException)


class TestToolNotFoundException:
    """Tests for ToolNotFoundException."""

    def test_default_code(self) -> None:
        exc = ToolNotFoundException(message="browser tool not found")
        assert exc.code == "TOOL_NOT_FOUND"

    def test_inherits_from_tool_exception(self) -> None:
        exc = ToolNotFoundException(message="missing tool")
        assert isinstance(exc, ToolException)
        assert isinstance(exc, AetherPhoenixException)

    def test_caught_as_tool_exception(self) -> None:
        with pytest.raises(ToolException):
            raise ToolNotFoundException(message="git not installed")

    def test_details_carry_tool_name(self) -> None:
        exc = ToolNotFoundException(
            message="Tool not available",
            details={"tool": "playwright", "required_version": ">=1.40"},
        )
        assert exc.details["tool"] == "playwright"


class TestToolExecutionException:
    """Tests for ToolExecutionException."""

    def test_default_code(self) -> None:
        exc = ToolExecutionException(message="browser crash")
        assert exc.code == "TOOL_EXECUTION_ERROR"

    def test_inherits_from_tool_exception(self) -> None:
        exc = ToolExecutionException(message="crash")
        assert isinstance(exc, ToolException)

    def test_caught_as_base(self) -> None:
        with pytest.raises(AetherPhoenixException):
            raise ToolExecutionException(message="execution failed")


# ---------------------------------------------------------------------------
# Cross-Family Propagation
# ---------------------------------------------------------------------------


class TestExceptionPropagation:
    """Verify that any platform exception can be caught via the base class."""

    @pytest.mark.parametrize(
        "exc_class,kwargs",
        [
            (RuntimeException, {"message": "runtime"}),
            (AgentRuntimeException, {"message": "agent"}),
            (WorkflowRuntimeException, {"message": "workflow"}),
            (ValidationException, {"message": "validation"}),
            (SchemaValidationException, {"message": "schema"}),
            (InputValidationException, {"message": "input"}),
            (PermissionException, {"message": "permission"}),
            (PermissionDeniedException, {"message": "denied"}),
            (UnauthorizedException, {"message": "unauthorized"}),
            (ToolException, {"message": "tool"}),
            (ToolNotFoundException, {"message": "not found"}),
            (ToolExecutionException, {"message": "exec failed"}),
        ],
    )
    def test_all_caught_as_base(self, exc_class: type, kwargs: dict) -> None:
        """Every concrete exception is catchable as AetherPhoenixException."""
        with pytest.raises(AetherPhoenixException):
            raise exc_class(**kwargs)

    @pytest.mark.parametrize(
        "exc_class,kwargs",
        [
            (RuntimeException, {"message": "runtime"}),
            (AgentRuntimeException, {"message": "agent"}),
            (WorkflowRuntimeException, {"message": "workflow"}),
            (ValidationException, {"message": "validation"}),
            (SchemaValidationException, {"message": "schema"}),
            (InputValidationException, {"message": "input"}),
            (PermissionException, {"message": "permission"}),
            (PermissionDeniedException, {"message": "denied"}),
            (UnauthorizedException, {"message": "unauthorized"}),
            (ToolException, {"message": "tool"}),
            (ToolNotFoundException, {"message": "not found"}),
            (ToolExecutionException, {"message": "exec failed"}),
        ],
    )
    def test_code_always_present(self, exc_class: type, kwargs: dict) -> None:
        """Every concrete exception carries a non-empty code."""
        exc = exc_class(**kwargs)
        assert exc.code
        assert isinstance(exc.code, str)


# ---------------------------------------------------------------------------
# ErrorDetail Schema
# ---------------------------------------------------------------------------


class TestErrorDetail:
    """Tests for the ErrorDetail Pydantic model."""

    def test_required_fields(self) -> None:
        detail = ErrorDetail(code="VALIDATION_ERROR", message="Invalid field")
        assert detail.code == "VALIDATION_ERROR"
        assert detail.message == "Invalid field"

    def test_details_defaults_to_none(self) -> None:
        detail = ErrorDetail(code="RUNTIME_ERROR", message="Crash")
        assert detail.details is None

    def test_details_accepts_dict(self) -> None:
        detail = ErrorDetail(
            code="TOOL_ERROR",
            message="Failed",
            details={"tool": "browser", "exit_code": 1},
        )
        assert detail.details["tool"] == "browser"

    def test_details_accepts_string(self) -> None:
        detail = ErrorDetail(code="TOOL_ERROR", message="Failed", details="exit code 1")
        assert detail.details == "exit code 1"

    def test_serializes_to_dict(self) -> None:
        detail = ErrorDetail(code="PERMISSION_DENIED", message="Denied")
        d = detail.model_dump()
        assert d["code"] == "PERMISSION_DENIED"
        assert d["message"] == "Denied"
        assert "details" in d

    def test_deserializes_from_dict(self) -> None:
        data = {"code": "UNAUTHORIZED", "message": "No token", "details": None}
        detail = ErrorDetail.model_validate(data)
        assert detail.code == "UNAUTHORIZED"

    def test_missing_code_raises(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ErrorDetail.model_validate({"message": "no code"})

    def test_missing_message_raises(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ErrorDetail.model_validate({"code": "SOME_CODE"})


# ---------------------------------------------------------------------------
# ErrorResponse Schema
# ---------------------------------------------------------------------------


class TestErrorResponse:
    """Tests for the ErrorResponse Pydantic model."""

    def test_success_is_always_false(self) -> None:
        resp = ErrorResponse(error=ErrorDetail(code="RUNTIME_ERROR", message="Crash"))
        assert resp.success is False

    def test_timestamp_auto_populated(self) -> None:
        resp = ErrorResponse(error=ErrorDetail(code="RUNTIME_ERROR", message="Crash"))
        assert isinstance(resp.timestamp, datetime)

    def test_request_id_auto_populated(self) -> None:
        resp = ErrorResponse(error=ErrorDetail(code="RUNTIME_ERROR", message="Crash"))
        # Must be parseable as a UUID
        uuid.UUID(resp.request_id)

    def test_custom_request_id(self) -> None:
        custom_id = str(uuid.uuid4())
        resp = ErrorResponse(
            error=ErrorDetail(code="RUNTIME_ERROR", message="Crash"),
            request_id=custom_id,
        )
        assert resp.request_id == custom_id

    def test_serializes_to_dict(self) -> None:
        resp = ErrorResponse(
            error=ErrorDetail(code="VALIDATION_ERROR", message="Bad input")
        )
        d = resp.model_dump()
        assert d["success"] is False
        assert d["error"]["code"] == "VALIDATION_ERROR"
        assert "timestamp" in d
        assert "request_id" in d

    def test_deserializes_from_dict(self) -> None:
        data = {
            "success": False,
            "error": {"code": "TOOL_NOT_FOUND", "message": "Missing tool"},
            "timestamp": "2026-08-09T06:00:00+00:00",
            "request_id": str(uuid.uuid4()),
        }
        resp = ErrorResponse.model_validate(data)
        assert resp.error.code == "TOOL_NOT_FOUND"

    def test_from_exception_factory_basic(self) -> None:
        resp = ErrorResponse.from_exception(
            code="RUNTIME_ERROR", message="Something broke"
        )
        assert resp.success is False
        assert resp.error.code == "RUNTIME_ERROR"
        assert resp.error.message == "Something broke"
        assert resp.error.details is None

    def test_from_exception_factory_with_details(self) -> None:
        resp = ErrorResponse.from_exception(
            code="VALIDATION_ERROR",
            message="Field missing",
            details={"field": "goal"},
        )
        assert resp.error.details == {"field": "goal"}

    def test_from_exception_factory_with_request_id(self) -> None:
        rid = str(uuid.uuid4())
        resp = ErrorResponse.from_exception(
            code="PERMISSION_DENIED",
            message="Denied",
            request_id=rid,
        )
        assert resp.request_id == rid

    def test_from_exception_factory_auto_request_id(self) -> None:
        resp = ErrorResponse.from_exception(code="TOOL_ERROR", message="Fail")
        uuid.UUID(resp.request_id)  # must be valid UUID

    def test_error_nested_structure(self) -> None:
        resp = ErrorResponse(
            error=ErrorDetail(
                code="SCHEMA_VALIDATION_ERROR",
                message="Schema mismatch",
                details=["field_a", "field_b"],
            )
        )
        assert isinstance(resp.error, ErrorDetail)
        assert resp.error.details == ["field_a", "field_b"]
