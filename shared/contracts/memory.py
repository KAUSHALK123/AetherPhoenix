import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MemoryCategory(str, Enum):
    """Categories of stored conversation memory."""

    PREFERENCE = "preference"
    INSTRUCTION = "instruction"
    DECISION = "decision"
    PROJECT_CONTEXT = "project_context"
    CLARIFICATION = "clarification"
    GENERAL_CHAT = "general_chat"


# Patterns for detecting sensitive information (API keys, passwords, tokens)
SENSITIVE_PATTERNS = [
    (
        r"(?i)(api[_-]?key|secret|password|access[_-]?token|bearer[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?",
        r"\1: [REDACTED]",
    ),
    (r"(?i)(sk-[a-zA-Z0-9]{20,})", "[REDACTED_API_KEY]"),
]

SENSITIVE_KEYS = {
    "password",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "bearer_token",
    "private_key",
}


def sanitize_memory_content(content: str) -> str:
    """Sanitizes sensitive patterns in content string."""
    sanitized = content
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized


def sanitize_memory_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Sanitizes metadata dictionary removing or masking sensitive fields."""
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if key.lower() in SENSITIVE_KEYS:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str):
            sanitized[key] = sanitize_memory_content(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_memory_metadata(value)
        else:
            sanitized[key] = value
    return sanitized


class ConversationMemoryEntry(BaseModel):
    """
    Represents a structured conversation memory entry stored for future context retrieval.
    """

    memory_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the memory entry.",
    )
    session_id: str = Field(
        ...,
        description="Identifier of the conversation/session to which this memory belongs.",
    )
    role: str = Field(
        ...,
        description="Role associated with the memory (e.g. 'user', 'assistant', 'system').",
    )
    content: str = Field(
        ...,
        description="The textual content of the memory.",
    )
    relevance_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relevance score of this memory (0.0 to 1.0) for future planning.",
    )
    category: MemoryCategory = Field(
        default=MemoryCategory.GENERAL_CHAT,
        description="Classification category of the memory content.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible metadata tags or structured context attributes.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the memory was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the memory was last updated.",
    )

    @field_validator("content")
    @classmethod
    def validate_and_sanitize_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Memory content cannot be empty.")
        return sanitize_memory_content(v)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, v: Any) -> dict[str, Any]:
        if v is None:
            return {}
        if isinstance(v, dict):
            return sanitize_memory_metadata(v)
        return {}


class MemoryQuery(BaseModel):
    """
    Represents parameters for querying conversation memory.
    """

    session_id: str | None = Field(
        default=None,
        description="Optional session ID filter.",
    )
    category: MemoryCategory | None = Field(
        default=None,
        description="Optional category filter.",
    )
    min_relevance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold.",
    )
    query_text: str | None = Field(
        default=None,
        description="Optional search text substring.",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of memory entries to return.",
    )
