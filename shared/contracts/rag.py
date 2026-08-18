from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class RAGSourceType(str, Enum):
    """Supported source types for RAG context items."""

    VECTOR_DB = "vector_db"
    CONVERSATION_MEMORY = "conversation_memory"
    TASK_HISTORY = "task_history"
    DOCUMENT = "document"
    KNOWLEDGE_BASE = "knowledge_base"


class RetrievalQuery(BaseModel):
    """
    Contract representing a search query submitted to the RAG pipeline.
    """

    query_text: str = Field(
        ...,
        description="The natural language query or task prompt for semantic retrieval.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of context items to retrieve.",
    )
    min_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Minimum relevance/similarity score threshold for filtering results.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID to restrict memory retrieval scope.",
    )
    category: str | None = Field(
        default=None,
        description="Optional memory category filter (e.g., 'preference', 'instruction').",
    )
    source_types: list[RAGSourceType] | list[str] | None = Field(
        default=None,
        description="Optional list of source types to query. Defaults to all sources if None.",
    )
    metadata_filter: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Key-value dictionary filter matched against record metadata.",
    )

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Retrieval query text cannot be empty.")
        return v.strip()


class RetrievedContextItem(BaseModel):
    """
    Contract representing a single retrieved knowledge or memory item with source metadata.
    """

    item_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the retrieved context item.",
    )
    content: str = Field(
        ...,
        description="Text content of the retrieved memory or document snippet.",
    )
    score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Relevance or cosine similarity score (higher is more relevant).",
    )
    source_type: RAGSourceType = Field(
        default=RAGSourceType.VECTOR_DB,
        description="Source system from which the item was retrieved.",
    )
    source_id: str | None = Field(
        default=None,
        description="Original source ID (e.g. memory_id, task_id, document_id).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved source metadata tags (e.g., session_id, role, category, timestamp).",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp of the underlying memory item.",
    )


class RAGContext(BaseModel):
    """
    Contract representing the full output of a RAG pipeline execution.
    Contains ranked items, formatted context string, and retrieval metadata.
    """

    query: str = Field(..., description="Original retrieval query text.")
    items: list[RetrievedContextItem] = Field(
        default_factory=list,
        description="Ranked list of relevant context items passing the relevance threshold.",
    )
    formatted_context: str = Field(
        default="",
        description="Structured markdown context block formatted for agent prompt injection.",
    )
    total_retrieved: int = Field(
        default=0,
        ge=0,
        description="Total number of items retrieved meeting the criteria.",
    )
    retrieval_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution details (search duration, threshold used, sources searched).",
    )
