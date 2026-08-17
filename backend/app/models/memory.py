import json
from datetime import timezone
from typing import Any

from shared.contracts.memory import ConversationMemoryEntry, MemoryCategory
from sqlalchemy import Column, DateTime, Float, String, Text

from app.database.base import Base


class ConversationMemoryModel(Base):
    """
    SQLAlchemy ORM model for storing conversation memories in SQLite/PostgreSQL.
    """

    __tablename__ = "conversation_memories"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(255), index=True, nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    relevance_score = Column(Float, default=1.0, index=True, nullable=False)
    category = Column(String(50), default="general_chat", index=True, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    def to_contract(self) -> ConversationMemoryEntry:
        """Converts ORM model to shared contract model."""
        parsed_metadata: dict[str, Any] = {}
        if self.metadata_json:
            try:
                parsed_metadata = json.loads(self.metadata_json)
            except Exception:
                parsed_metadata = {}

        category_enum = MemoryCategory.GENERAL_CHAT
        try:
            category_enum = MemoryCategory(self.category)
        except ValueError:
            pass

        created_dt = self.created_at
        if created_dt and created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)

        updated_dt = self.updated_at
        if updated_dt and updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=timezone.utc)

        return ConversationMemoryEntry(
            memory_id=self.id,
            session_id=self.session_id,
            role=self.role,
            content=self.content,
            relevance_score=self.relevance_score,
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
            category=entry.category.value
            if isinstance(entry.category, MemoryCategory)
            else str(entry.category),
            metadata_json=metadata_str,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
