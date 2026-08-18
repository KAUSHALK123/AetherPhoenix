import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from shared.contracts.memory import (
    ConversationMemoryEntry,
    MemoryCategory,
    MemoryQuery,
    sanitize_memory_content,
    sanitize_memory_metadata,
)
from sqlalchemy.orm import Session

from app.models.memory import ConversationMemoryModel


class BaseMemoryStorage(ABC):
    """
    Abstract interface for conversation memory storage providers.
    """

    @abstractmethod
    def save(self, entry: ConversationMemoryEntry) -> ConversationMemoryEntry:
        """Persists a new memory entry."""
        pass

    @abstractmethod
    def get_by_id(self, memory_id: str) -> ConversationMemoryEntry | None:
        """Retrieves a single memory entry by ID."""
        pass

    @abstractmethod
    def get_by_session(
        self, session_id: str, limit: int = 50
    ) -> list[ConversationMemoryEntry]:
        """Retrieves memory entries for a given session."""
        pass

    @abstractmethod
    def search(self, query: MemoryQuery) -> list[ConversationMemoryEntry]:
        """Searches memory entries matching filter parameters."""
        pass

    @abstractmethod
    def update(
        self, memory_id: str, updates: dict[str, Any]
    ) -> ConversationMemoryEntry | None:
        """Updates fields of an existing memory entry."""
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Deletes a memory entry by ID."""
        pass

    @abstractmethod
    def delete_by_session(self, session_id: str) -> int:
        """Deletes all memory entries for a specific session ID."""
        pass


class InMemoryMemoryStorage(BaseMemoryStorage):
    """
    In-memory storage provider for fast testing and session-scoped memory.
    """

    def __init__(self) -> None:
        self._memories: dict[str, ConversationMemoryEntry] = {}
        self._lock = threading.RLock()

    def save(self, entry: ConversationMemoryEntry) -> ConversationMemoryEntry:
        with self._lock:
            self._memories[entry.memory_id] = entry
            return entry

    def get_by_id(self, memory_id: str) -> ConversationMemoryEntry | None:
        with self._lock:
            return self._memories.get(memory_id)

    def get_by_session(
        self, session_id: str, limit: int = 50
    ) -> list[ConversationMemoryEntry]:
        with self._lock:
            session_memories = [
                m for m in self._memories.values() if m.session_id == session_id
            ]
            session_memories.sort(key=lambda m: m.created_at, reverse=False)
            return session_memories[:limit]

    def search(self, query: MemoryQuery) -> list[ConversationMemoryEntry]:
        with self._lock:
            results = list(self._memories.values())

            if query.session_id is not None:
                results = [m for m in results if m.session_id == query.session_id]

            if query.category is not None:
                results = [m for m in results if m.category == query.category]

            if query.min_relevance > 0.0:
                results = [
                    m for m in results if m.relevance_score >= query.min_relevance
                ]

            if query.query_text:
                q_text = query.query_text.lower()
                results = [m for m in results if q_text in m.content.lower()]

            results.sort(key=lambda m: (m.relevance_score, m.created_at), reverse=True)
            return results[: query.limit]

    def update(
        self, memory_id: str, updates: dict[str, Any]
    ) -> ConversationMemoryEntry | None:
        with self._lock:
            entry = self._memories.get(memory_id)
            if not entry:
                return None

            entry_dict = entry.model_dump()

            if "content" in updates and updates["content"]:
                entry_dict["content"] = sanitize_memory_content(updates["content"])
            if "relevance_score" in updates:
                entry_dict["relevance_score"] = float(updates["relevance_score"])
            if "category" in updates:
                cat = updates["category"]
                if isinstance(cat, str):
                    try:
                        entry_dict["category"] = MemoryCategory(cat)
                    except ValueError:
                        pass
                elif isinstance(cat, MemoryCategory):
                    entry_dict["category"] = cat
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                updated_meta = entry.metadata.copy()
                updated_meta.update(sanitize_memory_metadata(updates["metadata"]))
                entry_dict["metadata"] = updated_meta
            if "role" in updates:
                entry_dict["role"] = str(updates["role"])

            entry_dict["updated_at"] = datetime.now(timezone.utc)

            updated_entry = ConversationMemoryEntry(**entry_dict)
            self._memories[memory_id] = updated_entry
            return updated_entry

    def delete(self, memory_id: str) -> bool:
        with self._lock:
            if memory_id in self._memories:
                del self._memories[memory_id]
                return True
            return False

    def delete_by_session(self, session_id: str) -> int:
        with self._lock:
            to_delete = [
                mid for mid, m in self._memories.items() if m.session_id == session_id
            ]
            for mid in to_delete:
                del self._memories[mid]
            return len(to_delete)


class SQLAlchemyMemoryStorage(BaseMemoryStorage):
    """
    SQLAlchemy-backed storage provider for persistent database memory.
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    def save(self, entry: ConversationMemoryEntry) -> ConversationMemoryEntry:
        model = ConversationMemoryModel.from_contract(entry)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model.to_contract()

    def get_by_id(self, memory_id: str) -> ConversationMemoryEntry | None:
        model = (
            self.db.query(ConversationMemoryModel)
            .filter(ConversationMemoryModel.id == memory_id)
            .first()
        )
        if not model:
            return None
        return model.to_contract()

    def get_by_session(
        self, session_id: str, limit: int = 50
    ) -> list[ConversationMemoryEntry]:
        models = (
            self.db.query(ConversationMemoryModel)
            .filter(ConversationMemoryModel.session_id == session_id)
            .order_by(ConversationMemoryModel.created_at.asc())
            .limit(limit)
            .all()
        )
        return [m.to_contract() for m in models]

    def search(self, query: MemoryQuery) -> list[ConversationMemoryEntry]:
        db_query = self.db.query(ConversationMemoryModel)

        if query.session_id is not None:
            db_query = db_query.filter(
                ConversationMemoryModel.session_id == query.session_id
            )

        if query.category is not None:
            category_val = (
                query.category.value
                if isinstance(query.category, MemoryCategory)
                else str(query.category)
            )
            db_query = db_query.filter(ConversationMemoryModel.category == category_val)

        if query.min_relevance > 0.0:
            db_query = db_query.filter(
                ConversationMemoryModel.relevance_score >= query.min_relevance
            )

        if query.query_text:
            db_query = db_query.filter(
                ConversationMemoryModel.content.ilike(f"%{query.query_text}%")
            )

        models = (
            db_query.order_by(
                ConversationMemoryModel.relevance_score.desc(),
                ConversationMemoryModel.created_at.desc(),
            )
            .limit(query.limit)
            .all()
        )
        return [m.to_contract() for m in models]

    def update(
        self, memory_id: str, updates: dict[str, Any]
    ) -> ConversationMemoryEntry | None:
        model = (
            self.db.query(ConversationMemoryModel)
            .filter(ConversationMemoryModel.id == memory_id)
            .first()
        )
        if not model:
            return None

        if "content" in updates and updates["content"]:
            model.content = sanitize_memory_content(updates["content"])
        if "relevance_score" in updates:
            model.relevance_score = float(updates["relevance_score"])
        if "category" in updates:
            cat = updates["category"]
            model.category = cat.value if isinstance(cat, MemoryCategory) else str(cat)
        if "role" in updates:
            model.role = str(updates["role"])
        if "metadata" in updates and isinstance(updates["metadata"], dict):
            current_meta = (
                json.loads(str(model.metadata_json)) if model.metadata_json else {}
            )
            current_meta.update(sanitize_memory_metadata(updates["metadata"]))
            model.metadata_json = json.dumps(current_meta)

        model.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(model)
        return model.to_contract()

    def delete(self, memory_id: str) -> bool:
        model = (
            self.db.query(ConversationMemoryModel)
            .filter(ConversationMemoryModel.id == memory_id)
            .first()
        )
        if not model:
            return False

        self.db.delete(model)
        self.db.commit()
        return True

    def delete_by_session(self, session_id: str) -> int:
        count = (
            self.db.query(ConversationMemoryModel)
            .filter(ConversationMemoryModel.session_id == session_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return count
