from datetime import datetime, timezone
from typing import Any

from shared.contracts.memory import (
    ConversationMemoryEntry,
    MemoryCategory,
    MemoryQuery,
    sanitize_memory_content,
    sanitize_memory_metadata,
)

from app.core.logging import get_logger
from app.memory.storage import BaseMemoryStorage, InMemoryMemoryStorage

logger = get_logger(__name__)


class ConversationMemoryService:
    """
    High-level service interface for managing conversation memories.
    Handles memory storage, retrieval, relevance filtering, updates, deletion,
    logging, and sensitive data sanitization.
    """

    def __init__(
        self,
        storage: BaseMemoryStorage | None = None,
    ) -> None:
        self.storage = storage if storage is not None else InMemoryMemoryStorage()
        self.logger = logger

    def store_memory(
        self,
        session_id: str,
        role: str,
        content: str,
        category: MemoryCategory | str = MemoryCategory.GENERAL_CHAT,
        relevance_score: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMemoryEntry:
        """
        Stores a structured conversation memory entry.
        """
        if not session_id or not session_id.strip():
            raise ValueError("session_id cannot be empty.")
        if not role or not role.strip():
            raise ValueError("role cannot be empty.")
        if not content or not content.strip():
            raise ValueError("content cannot be empty.")

        if isinstance(category, str):
            try:
                cat_enum = MemoryCategory(category)
            except ValueError:
                cat_enum = MemoryCategory.GENERAL_CHAT
        else:
            cat_enum = category

        sanitized_content = sanitize_memory_content(content)
        sanitized_meta = sanitize_memory_metadata(metadata or {})

        entry = ConversationMemoryEntry(
            session_id=session_id,
            role=role,
            content=sanitized_content,
            relevance_score=max(0.0, min(1.0, float(relevance_score))),
            category=cat_enum,
            metadata=sanitized_meta,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        saved_entry = self.storage.save(entry)
        self.logger.info(
            f"Stored memory {saved_entry.memory_id} for session {session_id}",
            extra_context={
                "memory_id": saved_entry.memory_id,
                "session_id": session_id,
                "role": role,
                "category": saved_entry.category.value,
                "relevance_score": saved_entry.relevance_score,
            },
        )
        return saved_entry

    def get_memory(self, memory_id: str) -> ConversationMemoryEntry | None:
        """
        Retrieves a memory entry by ID. Handles invalid memory IDs gracefully.
        """
        if not memory_id or not isinstance(memory_id, str):
            self.logger.warning(f"Invalid memory_id requested: {memory_id}")
            return None

        entry = self.storage.get_by_id(memory_id)
        if not entry:
            self.logger.warning(f"Memory entry not found for memory_id: {memory_id}")
            return None

        self.logger.debug(f"Retrieved memory entry {memory_id}")
        return entry

    def get_session_memories(
        self, session_id: str, limit: int = 50
    ) -> list[ConversationMemoryEntry]:
        """
        Retrieves all stored memory entries for a given session.
        """
        if not session_id or not isinstance(session_id, str):
            self.logger.warning(f"Invalid session_id requested: {session_id}")
            return []

        entries = self.storage.get_by_session(session_id, limit=limit)
        self.logger.info(
            f"Retrieved {len(entries)} memory entries for session {session_id}"
        )
        return entries

    def get_relevant_memories(
        self,
        session_id: str | None = None,
        category: MemoryCategory | str | None = None,
        min_relevance: float = 0.0,
        query_text: str | None = None,
        limit: int = 50,
    ) -> list[ConversationMemoryEntry]:
        """
        Retrieves relevant memory entries filtered by category,
        relevance threshold, search text, or session.
        """
        cat_enum: MemoryCategory | None = None
        if category:
            if isinstance(category, str):
                try:
                    cat_enum = MemoryCategory(category)
                except ValueError:
                    cat_enum = None
            elif isinstance(category, MemoryCategory):
                cat_enum = category

        query = MemoryQuery(
            session_id=session_id,
            category=cat_enum,
            min_relevance=max(0.0, min(1.0, float(min_relevance))),
            query_text=query_text,
            limit=limit,
        )

        entries = self.storage.search(query)
        self.logger.info(
            f"Searched relevant memories: found {len(entries)} entries",
            extra_context={
                "session_id": session_id,
                "category": cat_enum.value if cat_enum else None,
                "min_relevance": min_relevance,
                "query_text": query_text,
            },
        )
        return entries

    def update_memory(
        self, memory_id: str, updates: dict[str, Any]
    ) -> ConversationMemoryEntry | None:
        """
        Updates an existing memory entry.
        """
        if not memory_id or not isinstance(memory_id, str):
            self.logger.warning(f"Cannot update invalid memory_id: {memory_id}")
            return None

        updated_entry = self.storage.update(memory_id, updates)
        if not updated_entry:
            self.logger.warning(
                f"Memory update failed: memory_id {memory_id} not found"
            )
            return None

        self.logger.info(f"Updated memory entry {memory_id}")
        return updated_entry

    def delete_memory(self, memory_id: str) -> bool:
        """
        Deletes a memory entry by ID.
        """
        if not memory_id or not isinstance(memory_id, str):
            self.logger.warning(f"Cannot delete invalid memory_id: {memory_id}")
            return False

        success = self.storage.delete(memory_id)
        if success:
            self.logger.info(f"Deleted memory entry {memory_id}")
        else:
            self.logger.warning(f"Deletion failed: memory_id {memory_id} not found")
        return success

    def clear_session_memories(self, session_id: str) -> int:
        """
        Deletes all memory entries for a given session.
        """
        if not session_id or not isinstance(session_id, str):
            self.logger.warning(f"Cannot clear invalid session_id: {session_id}")
            return 0

        count = self.storage.delete_by_session(session_id)
        self.logger.info(f"Cleared {count} memory entries for session {session_id}")
        return count
