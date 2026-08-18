import json
from datetime import datetime, timezone
from typing import Any

from shared.contracts.memory import ConversationMemoryEntry, MemoryCategory
from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ConversationMemoryModel(Base):
    """
    SQLAlchemy ORM model for storing conversation memories in SQLite/PostgreSQL.
    """

    __tablename__ = "conversation_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float] = mapped_column(
        Float, default=1.0, index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(
        String(50), default="general_chat", index=True, nullable=False
    )
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def to_contract(self) -> ConversationMemoryEntry:
        """Converts ORM model to shared contract model."""
        parsed_metadata: dict[str, Any] = {}
        if self.metadata_json:
            try:
                parsed_metadata = json.loads(str(self.metadata_json))
            except Exception:
                parsed_metadata = {}

        category_enum = MemoryCategory.GENERAL_CHAT
        try:
            category_enum = MemoryCategory(str(self.category))
        except ValueError:
            pass

        created_dt = self.created_at
        if created_dt and created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)

        updated_dt = self.updated_at
        if updated_dt and updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=timezone.utc)

        return ConversationMemoryEntry(
            memory_id=str(self.id),
            session_id=str(self.session_id),
            role=str(self.role),
            content=str(self.content),
            relevance_score=float(self.relevance_score),
            category=category_enum,
            metadata=parsed_metadata,
            created_at=created_dt,
            updated_at=updated_dt,
        )

    @classmethod
    def from_contract(cls, entry: ConversationMemoryEntry) -> "ConversationMemoryModel":
        """Converts shared contract model to ORM model."""
        metadata_str = json.dumps(entry.metadata) if entry.metadata else "{}"
        return cls(
            id=entry.memory_id,
            session_id=entry.session_id,
            role=entry.role,
            content=entry.content,
            relevance_score=entry.relevance_score,
            category=(
                entry.category.value
                if isinstance(entry.category, MemoryCategory)
                else str(entry.category)
            ),
            metadata_json=metadata_str,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
