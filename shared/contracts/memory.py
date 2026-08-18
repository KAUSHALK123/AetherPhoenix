import hashlib
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


class MemoryLifecycleState(str, Enum):
    """Lifecycle states of a stored memory item."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    DELETED = "deleted"
    PENDING_REVIEW = "pending_review"


class MemoryType(str, Enum):
    """Functional classifications of stored memory."""

    USER_PREFERENCE = "user_preference"
    CONVERSATION = "conversation"
    TASK_RESULT = "task_result"
    KNOWLEDGE = "knowledge"
    ARTIFACT_REF = "artifact_ref"
    AGENT_FACT = "agent_fact"


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


def compute_content_hash(content: str) -> str:
    """Computes a SHA-256 hash of normalized content for exact duplicate detection."""
    normalized = " ".join(content.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class RetentionPolicy(BaseModel):
    """Retention configuration for stored memories."""

    ttl_seconds: int | None = Field(
        default=None,
        description="Time-to-live in seconds before memory expires. None = indefinite.",
    )
    max_age_days: int | None = Field(
        default=None,
        description="Maximum age in days before auto-archiving.",
    )
    auto_archive: bool = Field(
        default=False,
        description="Whether to archive instead of deleting on expiry.",
    )
    auto_delete: bool = Field(
        default=True,
        description="Whether to permanently remove on expiration cleanup.",
    )


class MemoryItem(BaseModel):
    """
    Core memory entity for the centralized Memory Management subsystem.
    """

    memory_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the memory item.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID to scope memory to a specific session.",
    )
    workflow_id: str | None = Field(
        default=None,
        description="Optional workflow ID associated with the memory.",
    )
    task_id: str | None = Field(
        default=None,
        description="Optional task ID that generated the memory.",
    )
    memory_type: MemoryType = Field(
        default=MemoryType.KNOWLEDGE,
        description="Classification type of the memory.",
    )
    category: MemoryCategory = Field(
        default=MemoryCategory.PROJECT_CONTEXT,
        description="Category classification.",
    )
    content: str = Field(
        ...,
        description="Primary textual content of the memory.",
    )
    content_hash: str = Field(
        default="",
        description="SHA-256 hash of normalized content for deduplication.",
    )
    relevance_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relevance or importance score (0.0 to 1.0).",
    )
    lifecycle_state: MemoryLifecycleState = Field(
        default=MemoryLifecycleState.ACTIVE,
        description="Current lifecycle state (ACTIVE, ARCHIVED, EXPIRED, DELETED).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured key-value metadata.",
    )
    retention: RetentionPolicy = Field(
        default_factory=RetentionPolicy,
        description="Retention and expiration policy for this memory.",
    )
    author_agent: str | None = Field(
        default=None,
        description="Name of the agent or user creating the memory.",
    )
    vector_id: str | None = Field(
        default=None,
        description="ID of associated vector embedding in vector store.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the memory was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the memory was last updated.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the memory is set to expire.",
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
    workflow_id: str | None = Field(
        default=None,
        description="Optional workflow ID filter.",
    )
    memory_type: MemoryType | None = Field(
        default=None,
        description="Optional memory type filter.",
    )
    category: MemoryCategory | None = Field(
        default=None,
        description="Optional category filter.",
    )
    lifecycle_state: MemoryLifecycleState | None = Field(
        default=MemoryLifecycleState.ACTIVE,
        description="Optional lifecycle state filter.",
    )
    min_relevance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold.",
    )
    query_text: str | None = Field(
        default=None,
        description="Optional search text substring or semantic query.",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of memory entries to return.",
    )
