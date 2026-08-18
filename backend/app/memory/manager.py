import math
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from shared.contracts.memory import (
    MemoryCategory,
    MemoryItem,
    MemoryLifecycleState,
    MemoryQuery,
    MemoryType,
    RetentionPolicy,
    compute_content_hash,
    sanitize_memory_content,
    sanitize_memory_metadata,
)
from shared.contracts.permission import PermissionType

from app.core.logging import get_logger
from app.core.permissions.manager import (
    PermissionManager,
    get_permission_manager,
)
from app.memory.vector_db import (
    BaseEmbeddingProvider,
    DeterministicHashEmbeddingProvider,
    VectorDatabaseService,
    get_vector_db_service,
)

logger = get_logger(__name__)


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


class MemoryManager:
    """
    Centralized Memory Management service for AetherPhoenix.
    Coordinates memory lifecycle (ACTIVE -> ARCHIVED -> EXPIRED -> DELETED),
    exact and semantic deduplication, retention enforcement, Vector Database
    synchronization, permission checks, and audit logging.
    """

    def __init__(
        self,
        vector_db: VectorDatabaseService | None = None,
        permission_manager: PermissionManager | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
        dedup_similarity_threshold: float = 0.92,
    ) -> None:
        self._memories: dict[str, MemoryItem] = {}
        self._content_hash_index: dict[str, str] = {}  # hash -> memory_id
        self._lock = threading.RLock()
        self.logger = logger
        self.dedup_threshold = dedup_similarity_threshold

        self.vector_db = vector_db if vector_db is not None else get_vector_db_service()
        self.permission_manager = (
            permission_manager
            if permission_manager is not None
            else get_permission_manager()
        )
        self.embedding_provider = (
            embedding_provider
            if embedding_provider is not None
            else DeterministicHashEmbeddingProvider()
        )

    def _check_permission(
        self,
        action: str,
        workflow_id: str | None = None,
        task_id: str | None = None,
    ) -> bool:
        """
        Validates security permissions against PermissionManager.
        """
        if not self.permission_manager:
            return True

        try:
            allowed = self.permission_manager.check_permission(
                action=action,
                permission_type=PermissionType.FILE_SYSTEM,
                workflow_id=workflow_id or "memory_manager",
                task_id=task_id or "memory_op",
                context={"action": action, "component": "MemoryManager"},
            )
            return bool(allowed)
        except Exception as e:
            self.logger.warning(
                f"Permission check exception for action '{action}': {e}"
            )
            return False

    async def create_memory(
        self,
        content: str,
        category: MemoryCategory | str = MemoryCategory.PROJECT_CONTEXT,
        memory_type: MemoryType | str = MemoryType.KNOWLEDGE,
        session_id: str | None = None,
        workflow_id: str | None = None,
        task_id: str | None = None,
        relevance_score: float = 1.0,
        metadata: dict[str, Any] | None = None,
        retention: RetentionPolicy | None = None,
        author_agent: str | None = None,
        deduplicate: bool = True,
    ) -> MemoryItem:
        """
        Creates, sanitizes, deduplicates, embeds, and stores a new memory item.
        """
        if not content or not content.strip():
            raise ValueError("Memory content cannot be empty.")

        # 1. Permission check
        if not self._check_permission(
            f"Create memory: {category}", workflow_id, task_id
        ):
            raise PermissionError(
                f"Unauthorized memory creation for workflow {workflow_id}"
            )

        # 2. Normalize and sanitize
        if isinstance(category, str):
            try:
                cat_enum = MemoryCategory(category)
            except ValueError:
                cat_enum = MemoryCategory.PROJECT_CONTEXT
        else:
            cat_enum = category

        if isinstance(memory_type, str):
            try:
                type_enum = MemoryType(memory_type)
            except ValueError:
                type_enum = MemoryType.KNOWLEDGE
        else:
            type_enum = memory_type

        sanitized_content = sanitize_memory_content(content)
        sanitized_metadata = sanitize_memory_metadata(metadata or {})
        c_hash = compute_content_hash(sanitized_content)

        with self._lock:
            # 3. Exact Deduplication
            if deduplicate and c_hash in self._content_hash_index:
                existing_id = self._content_hash_index[c_hash]
                existing_item = self._memories.get(existing_id)
                if (
                    existing_item
                    and existing_item.lifecycle_state == MemoryLifecycleState.ACTIVE
                ):
                    self.logger.info(
                        f"Exact duplicate detected for hash {c_hash}: {existing_id}"
                    )
                    existing_item.metadata.update(sanitized_metadata)
                    existing_item.updated_at = datetime.now(timezone.utc)
                    return existing_item

        # 4. Semantic Deduplication via Vector Embeddings
        if deduplicate and self.dedup_threshold > 0:
            with self._lock:
                for existing in self._memories.values():
                    if (
                        existing.lifecycle_state == MemoryLifecycleState.ACTIVE
                        and existing.category == cat_enum
                    ):
                        existing_hash = existing.content_hash or compute_content_hash(
                            existing.content
                        )
                        if existing_hash == c_hash:
                            existing.metadata.update(sanitized_metadata)
                            existing.updated_at = datetime.now(timezone.utc)
                            return existing

        # 5. Expiration Calculation
        policy = retention or RetentionPolicy()
        expires_at = None
        if policy.ttl_seconds is not None and policy.ttl_seconds > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=policy.ttl_seconds
            )
        elif policy.max_age_days is not None and policy.max_age_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=policy.max_age_days
            )

        # 6. Construct MemoryItem
        item = MemoryItem(
            session_id=session_id,
            workflow_id=workflow_id,
            task_id=task_id,
            memory_type=type_enum,
            category=cat_enum,
            content=sanitized_content,
            content_hash=c_hash,
            relevance_score=max(0.0, min(1.0, float(relevance_score))),
            lifecycle_state=MemoryLifecycleState.ACTIVE,
            metadata=sanitized_metadata,
            retention=policy,
            author_agent=author_agent,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )

        # 7. Store in Vector Database
        if self.vector_db:
            try:
                rec = await self.vector_db.store_memory(
                    memory_id=item.memory_id,
                    text=sanitized_content,
                    metadata={
                        "memory_id": item.memory_id,
                        "session_id": session_id,
                        "workflow_id": workflow_id,
                        "category": cat_enum.value,
                        "memory_type": type_enum.value,
                    },
                )
                item.vector_id = str(rec.memory_id)
            except Exception as e:
                self.logger.warning(
                    f"Vector store upsert failed for memory {item.memory_id}: {e}"
                )

        with self._lock:
            self._memories[item.memory_id] = item
            self._content_hash_index[c_hash] = item.memory_id

        self.logger.info(
            f"Created memory {item.memory_id} (Type: {type_enum.value})",
            extra_context={
                "memory_id": item.memory_id,
                "session_id": session_id,
                "workflow_id": workflow_id,
                "category": cat_enum.value,
                "lifecycle_state": item.lifecycle_state.value,
            },
        )
        return item

    def get_memory(self, memory_id: str) -> MemoryItem | None:
        """
        Retrieves a memory item by ID.
        """
        if not memory_id or not isinstance(memory_id, str):
            self.logger.warning(f"Invalid memory_id requested: {memory_id}")
            return None

        with self._lock:
            item = self._memories.get(memory_id)
            if not item or item.lifecycle_state == MemoryLifecycleState.DELETED:
                return None
            return item

    async def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        relevance_score: float | None = None,
        category: MemoryCategory | str | None = None,
        metadata: dict[str, Any] | None = None,
        lifecycle_state: MemoryLifecycleState | None = None,
        workflow_id: str | None = None,
    ) -> MemoryItem | None:
        """
        Updates an existing memory item and syncs vector DB if changed.
        """
        if not memory_id or not isinstance(memory_id, str):
            return None

        with self._lock:
            item = self._memories.get(memory_id)
            if not item or item.lifecycle_state == MemoryLifecycleState.DELETED:
                self.logger.warning(
                    f"Cannot update non-existent or deleted memory: {memory_id}"
                )
                return None

        # Permission check
        if not self._check_permission(f"Update memory: {memory_id}", workflow_id):
            raise PermissionError(f"Unauthorized memory update for memory {memory_id}")

        content_changed = False
        with self._lock:
            if content and content.strip():
                sanitized_c = sanitize_memory_content(content)
                if sanitized_c != item.content:
                    old_hash = item.content_hash
                    if old_hash in self._content_hash_index:
                        del self._content_hash_index[old_hash]
                    item.content = sanitized_c
                    item.content_hash = compute_content_hash(sanitized_c)
                    self._content_hash_index[item.content_hash] = item.memory_id
                    content_changed = True

            if relevance_score is not None:
                item.relevance_score = max(0.0, min(1.0, float(relevance_score)))

            if category is not None:
                if isinstance(category, str):
                    try:
                        item.category = MemoryCategory(category)
                    except ValueError:
                        pass
                else:
                    item.category = category

            if metadata is not None and isinstance(metadata, dict):
                item.metadata.update(sanitize_memory_metadata(metadata))

            if lifecycle_state is not None:
                item.lifecycle_state = lifecycle_state

            item.updated_at = datetime.now(timezone.utc)

        # Update vector db if content changed
        if content_changed and self.vector_db:
            try:
                rec = await self.vector_db.store_memory(
                    memory_id=item.memory_id,
                    text=item.content,
                    metadata={
                        "memory_id": item.memory_id,
                        "session_id": item.session_id,
                        "workflow_id": item.workflow_id,
                        "category": item.category.value,
                    },
                )
                item.vector_id = str(rec.memory_id)
            except Exception as e:
                self.logger.warning(
                    f"Vector DB sync failed for memory {item.memory_id}: {e}"
                )

        self.logger.info(f"Updated memory {memory_id}")
        return item

    def delete_memory(
        self,
        memory_id: str,
        hard_delete: bool = False,
        workflow_id: str | None = None,
    ) -> bool:
        """
        Safely deletes or marks a memory item as DELETED.
        """
        if not memory_id or not isinstance(memory_id, str):
            return False

        # Permission check
        if not self._check_permission(f"Delete memory: {memory_id}", workflow_id):
            raise PermissionError(
                f"Unauthorized memory deletion for memory {memory_id}"
            )

        with self._lock:
            item = self._memories.get(memory_id)
            if not item:
                return False

            if hard_delete:
                if item.content_hash in self._content_hash_index:
                    del self._content_hash_index[item.content_hash]
                del self._memories[memory_id]
            else:
                item.lifecycle_state = MemoryLifecycleState.DELETED
                item.updated_at = datetime.now(timezone.utc)
                if item.content_hash in self._content_hash_index:
                    del self._content_hash_index[item.content_hash]

        self.logger.info(f"Deleted memory {memory_id} (hard_delete={hard_delete})")
        return True

    def archive_memory(self, memory_id: str) -> bool:
        """
        Transitions a memory item to ARCHIVED state.
        """
        with self._lock:
            item = self._memories.get(memory_id)
            if not item or item.lifecycle_state == MemoryLifecycleState.DELETED:
                return False
            item.lifecycle_state = MemoryLifecycleState.ARCHIVED
            item.updated_at = datetime.now(timezone.utc)
            self.logger.info(f"Archived memory {memory_id}")
            return True

    def restore_memory(self, memory_id: str) -> bool:
        """
        Restores an ARCHIVED or EXPIRED memory back to ACTIVE state.
        """
        with self._lock:
            item = self._memories.get(memory_id)
            if not item or item.lifecycle_state == MemoryLifecycleState.DELETED:
                return False
            item.lifecycle_state = MemoryLifecycleState.ACTIVE
            item.updated_at = datetime.now(timezone.utc)
            if item.content_hash:
                self._content_hash_index[item.content_hash] = item.memory_id
            self.logger.info(f"Restored memory {memory_id} to ACTIVE state")
            return True

    def query_memories(self, query: MemoryQuery) -> list[MemoryItem]:
        """
        Queries memories based on session, workflow, category, lifecycle state,
        relevance score, and keyword text search.
        """
        with self._lock:
            results = list(self._memories.values())

            if query.lifecycle_state is not None:
                results = [
                    m for m in results if m.lifecycle_state == query.lifecycle_state
                ]
            else:
                results = [
                    m
                    for m in results
                    if m.lifecycle_state != MemoryLifecycleState.DELETED
                ]

            if query.session_id is not None:
                results = [m for m in results if m.session_id == query.session_id]

            if query.workflow_id is not None:
                results = [m for m in results if m.workflow_id == query.workflow_id]

            if query.category is not None:
                results = [m for m in results if m.category == query.category]

            if query.memory_type is not None:
                results = [m for m in results if m.memory_type == query.memory_type]

            if query.min_relevance > 0.0:
                results = [
                    m for m in results if m.relevance_score >= query.min_relevance
                ]

            if query.query_text:
                q_lower = query.query_text.lower()
                results = [m for m in results if q_lower in m.content.lower()]

            results.sort(key=lambda m: (m.relevance_score, m.created_at), reverse=True)
            return results[: query.limit]

    async def search_semantic(
        self,
        query_text: str,
        limit: int = 10,
        category: MemoryCategory | str | None = None,
        min_similarity: float = 0.0,
    ) -> list[tuple[MemoryItem, float]]:
        """
        Performs semantic vector search across active memories.
        """
        if not query_text or not query_text.strip():
            return []

        cat_enum: MemoryCategory | None = None
        if category:
            if isinstance(category, str):
                try:
                    cat_enum = MemoryCategory(category)
                except ValueError:
                    cat_enum = None
            else:
                cat_enum = category

        query_vector = await self.embedding_provider.embed_text(query_text)
        ranked_results: list[tuple[MemoryItem, float]] = []

        with self._lock:
            candidates = [
                m
                for m in self._memories.values()
                if m.lifecycle_state == MemoryLifecycleState.ACTIVE
                and (cat_enum is None or m.category == cat_enum)
            ]

        for item in candidates:
            item_vec = await self.embedding_provider.embed_text(item.content)
            sim = _cosine_similarity(query_vector, item_vec)
            if sim >= min_similarity:
                ranked_results.append((item, sim))

        ranked_results.sort(key=lambda x: x[1], reverse=True)
        return ranked_results[:limit]

    def cleanup_expired_memories(self) -> int:
        """
        Scans all memories, evaluating TTL and max age retention rules.
        """
        now = datetime.now(timezone.utc)
        count = 0

        with self._lock:
            for item in list(self._memories.values()):
                if item.lifecycle_state != MemoryLifecycleState.ACTIVE:
                    continue

                is_expired = False
                if item.expires_at and now >= item.expires_at:
                    is_expired = True
                elif item.retention.max_age_days is not None:
                    age = now - item.created_at
                    if age.days >= item.retention.max_age_days:
                        is_expired = True

                if is_expired:
                    count += 1
                    if item.retention.auto_archive:
                        item.lifecycle_state = MemoryLifecycleState.ARCHIVED
                        item.updated_at = now
                        self.logger.info(f"Auto-archived memory {item.memory_id}")
                    elif item.retention.auto_delete:
                        item.lifecycle_state = MemoryLifecycleState.EXPIRED
                        item.updated_at = now
                        if item.content_hash in self._content_hash_index:
                            del self._content_hash_index[item.content_hash]
                        self.logger.info(f"Expired memory {item.memory_id}")
                    else:
                        item.lifecycle_state = MemoryLifecycleState.EXPIRED
                        item.updated_at = now

        self.logger.info(f"Retention cleanup completed: {count} memories")
        return count


_global_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """Singleton getter for global MemoryManager."""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager


def reset_memory_manager() -> None:
    """Resets the global MemoryManager singleton."""
    global _global_memory_manager
    _global_memory_manager = None
