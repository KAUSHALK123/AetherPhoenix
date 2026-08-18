from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class VectorRecord(BaseModel):
    """
    Contract representing an embedded vector record associated with a memory ID.
    """

    memory_id: UUID | str = Field(
        default_factory=uuid4, description="Unique memory entry identifier"
    )
    vector: list[float] = Field(..., description="Dense float vector embedding")
    document: str = Field(default="", description="Original raw document text embedded")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata tags for filtering"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp",
    )


class VectorSearchResult(BaseModel):
    """
    Contract representing a ranked similarity search result.
    """

    memory_id: UUID | str = Field(..., description="Memory entry identifier")
    score: float = Field(
        ..., ge=-1.0, le=1.0, description="Similarity score (e.g., Cosine similarity)"
    )
    document: str = Field(default="", description="Associated raw document text")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Associated metadata attributes"
    )
