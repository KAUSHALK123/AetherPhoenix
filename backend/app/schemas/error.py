"""
AetherPhoenix — Error Response Schemas
=======================================
Pydantic models for structured API error responses.

The shapes defined here align exactly with the failure response format
specified in ``05_API_SPEC.md``:

    {
        "success": false,
        "error": {
            "code": "<string>",
            "message": "<string>",
            "details": "<any>"
        },
        "timestamp": "<ISO-8601>",
        "request_id": "<uuid>"
    }

Design rules:
  - These are **output** models only — they are never used as request bodies.
  - ``details`` is intentionally typed as ``Any`` to accommodate diverse
    supplementary context (field names, upstream payloads, etc.).
  - ``request_id`` is optional so callers can omit it when no request
    context is available (e.g. background tasks).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    Inner error object nested inside every error response.

    Attributes
    ----------
    code:
        Namespaced string error code (e.g. ``"VALIDATION_ERROR"``).
        Consumers should switch on this field programmatically.
    message:
        Human-readable description of the error, safe to display to callers.
    details:
        Optional supplementary context. May be a string, dict, list, or
        ``None``. Never contains raw stack traces.
    """

    code: str = Field(
        ...,
        description="Namespaced error code identifier.",
        examples=["VALIDATION_ERROR", "PERMISSION_DENIED", "TOOL_NOT_FOUND"],
    )
    message: str = Field(
        ...,
        description="Human-readable error description.",
        examples=["Input validation failed for field 'goal'."],
    )
    details: Any = Field(
        default=None,
        description=(
            "Optional supplementary context (field name, upstream error, etc.)."
        ),
    )

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    """
    Top-level structured error response returned by every failing API endpoint.

    Matches the failure envelope defined in ``05_API_SPEC.md``.

    Attributes
    ----------
    success:
        Always ``False`` for error responses.
    error:
        Nested :class:`ErrorDetail` object.
    timestamp:
        ISO-8601 UTC timestamp of when the error was generated.
        Auto-populated if not provided.
    request_id:
        Optional UUID that correlates the response to a specific request.
        Auto-populated as a new UUID v4 if not provided.
    """

    success: bool = Field(
        default=False,
        description="Always False for error responses.",
    )
    error: ErrorDetail = Field(
        ...,
        description="Structured error detail object.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the error event.",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the originating request.",
    )

    model_config = {"populate_by_name": True}

    @classmethod
    def from_exception(
        cls,
        code: str,
        message: str,
        details: Any = None,
        request_id: str | None = None,
    ) -> "ErrorResponse":
        """
        Convenience factory to construct an :class:`ErrorResponse` directly
        from exception fields.

        Parameters
        ----------
        code:
            The exception error code (e.g. ``"VALIDATION_ERROR"``).
        message:
            Human-readable error message.
        details:
            Optional supplementary context.
        request_id:
            Optional request correlation ID. A new UUID is generated
            if not supplied.

        Returns
        -------
        ErrorResponse
            A fully populated error response model.
        """
        return cls(
            error=ErrorDetail(code=code, message=message, details=details),
            request_id=request_id or str(uuid4()),
        )


__all__ = [
    "ErrorDetail",
    "ErrorResponse",
]
