from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from shared.contracts.memory import (
    MemoryCategory,
    MemoryLifecycleState,
    MemoryQuery,
    MemoryType,
    RetentionPolicy,
    compute_content_hash,
)

from app.memory.manager import (
    MemoryManager,
    get_memory_manager,
    reset_memory_manager,
)
from app.memory.vector_db import (
    DeterministicHashEmbeddingProvider,
    InMemoryVectorStoreProvider,
    VectorDatabaseService,
)


@pytest.fixture
def vector_db():
    provider = InMemoryVectorStoreProvider()
    embedding = DeterministicHashEmbeddingProvider(dimension=64)
    return VectorDatabaseService(
        embedding_provider=embedding, vector_store_provider=provider
    )


@pytest.fixture
def permission_manager():
    mock = MagicMock()
    mock.check_permission.return_value = True
    return mock


@pytest.fixture
def memory_manager(vector_db, permission_manager):
    embedding = DeterministicHashEmbeddingProvider(dimension=64)
    return MemoryManager(
        vector_db=vector_db,
        permission_manager=permission_manager,
        embedding_provider=embedding,
        dedup_similarity_threshold=0.95,
    )


@pytest.mark.asyncio
async def test_create_and_get_memory(memory_manager):
    item = await memory_manager.create_memory(
        content="User prefers Python for scripts",
        category=MemoryCategory.PREFERENCE,
        memory_type=MemoryType.USER_PREFERENCE,
        session_id="sess_123",
        workflow_id="wf_456",
        relevance_score=0.9,
        metadata={"source": "chat"},
        author_agent="PlannerAgent",
    )

    assert item.memory_id is not None
    assert item.content == "User prefers Python for scripts"
    assert item.category == MemoryCategory.PREFERENCE
    assert item.memory_type == MemoryType.USER_PREFERENCE
    assert item.lifecycle_state == MemoryLifecycleState.ACTIVE
    assert item.metadata["source"] == "chat"
    assert item.author_agent == "PlannerAgent"
    assert item.vector_id is not None

    retrieved = memory_manager.get_memory(item.memory_id)
    assert retrieved is not None
    assert retrieved.memory_id == item.memory_id
    assert retrieved.content == item.content


@pytest.mark.asyncio
async def test_create_memory_empty_content_raises_error(memory_manager):
    with pytest.raises(ValueError, match="cannot be empty"):
        await memory_manager.create_memory(content="   ")


@pytest.mark.asyncio
async def test_sensitive_data_sanitization(memory_manager):
    item = await memory_manager.create_memory(
        content="Connecting with api_key = 'abcdef12345678' and password='secret'",
        metadata={"api_key": "raw_secret_value", "env": "prod"},
    )

    assert "abcdef12345678" not in item.content
    assert "[REDACTED]" in item.content
    assert item.metadata["api_key"] == "[REDACTED]"
    assert item.metadata["env"] == "prod"


@pytest.mark.asyncio
async def test_exact_deduplication(memory_manager):
    item1 = await memory_manager.create_memory(
        content="Deploy instructions: always run tests before commit",
        category=MemoryCategory.INSTRUCTION,
        metadata={"version": 1},
    )

    item2 = await memory_manager.create_memory(
        content="Deploy instructions: always run tests before commit",
        category=MemoryCategory.INSTRUCTION,
        metadata={"version": 2},
    )

    assert item1.memory_id == item2.memory_id
    assert item2.metadata["version"] == 2


@pytest.mark.asyncio
async def test_update_memory(memory_manager):
    item = await memory_manager.create_memory(
        content="Initial configuration draft",
        relevance_score=0.5,
    )

    updated = await memory_manager.update_memory(
        memory_id=item.memory_id,
        content="Final verified configuration setup",
        relevance_score=0.95,
        metadata={"status": "verified"},
    )

    assert updated is not None
    assert updated.content == "Final verified configuration setup"
    assert updated.relevance_score == 0.95
    assert updated.metadata["status"] == "verified"

    new_hash = compute_content_hash("Final verified configuration setup")
    assert updated.content_hash == new_hash


@pytest.mark.asyncio
async def test_delete_memory_soft_and_hard(memory_manager):
    item = await memory_manager.create_memory(content="Temporary memory to delete")

    # Soft delete
    deleted = memory_manager.delete_memory(item.memory_id, hard_delete=False)
    assert deleted is True

    retrieved = memory_manager.get_memory(item.memory_id)
    assert retrieved is None

    # Hard delete
    item2 = await memory_manager.create_memory(content="Hard delete target")
    hard_deleted = memory_manager.delete_memory(item2.memory_id, hard_delete=True)
    assert hard_deleted is True
    assert item2.memory_id not in memory_manager._memories


@pytest.mark.asyncio
async def test_archive_and_restore_memory(memory_manager):
    item = await memory_manager.create_memory(content="Completed project retrospective")

    # Archive
    archived = memory_manager.archive_memory(item.memory_id)
    assert archived is True
    assert item.lifecycle_state == MemoryLifecycleState.ARCHIVED

    # Restore
    restored = memory_manager.restore_memory(item.memory_id)
    assert restored is True
    assert item.lifecycle_state == MemoryLifecycleState.ACTIVE


@pytest.mark.asyncio
async def test_query_memories_filtering(memory_manager):
    await memory_manager.create_memory(
        content="Setup Docker container for backend",
        session_id="session_A",
        workflow_id="wf_1",
        category=MemoryCategory.PROJECT_CONTEXT,
        memory_type=MemoryType.KNOWLEDGE,
        relevance_score=0.8,
    )
    await memory_manager.create_memory(
        content="User dislikes dark mode",
        session_id="session_A",
        workflow_id="wf_1",
        category=MemoryCategory.PREFERENCE,
        memory_type=MemoryType.USER_PREFERENCE,
        relevance_score=0.9,
    )
    await memory_manager.create_memory(
        content="Different session note",
        session_id="session_B",
        workflow_id="wf_2",
        category=MemoryCategory.GENERAL_CHAT,
        relevance_score=0.4,
    )

    results = memory_manager.query_memories(MemoryQuery(session_id="session_A"))
    assert len(results) == 2

    pref_results = memory_manager.query_memories(
        MemoryQuery(category=MemoryCategory.PREFERENCE)
    )
    assert len(pref_results) == 1
    assert "dark mode" in pref_results[0].content

    high_rel = memory_manager.query_memories(MemoryQuery(min_relevance=0.85))
    assert len(high_rel) == 1


@pytest.mark.asyncio
async def test_semantic_search(memory_manager):
    await memory_manager.create_memory(
        content="Microservices architecture deployment and kubernetes management",
        category=MemoryCategory.PROJECT_CONTEXT,
    )
    await memory_manager.create_memory(
        content="Breakfast recipes for chocolate pancakes",
        category=MemoryCategory.GENERAL_CHAT,
    )

    results = await memory_manager.search_semantic(
        query_text="container kubernetes deployment architecture",
        limit=5,
    )

    assert len(results) > 0
    top_item, score = results[0]
    assert "Microservices architecture" in top_item.content
    assert score > 0.0


@pytest.mark.asyncio
async def test_retention_policy_and_expiration(memory_manager):
    item = await memory_manager.create_memory(
        content="Ephemeral memory with short TTL",
        retention=RetentionPolicy(ttl_seconds=1, auto_delete=True),
    )

    item.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)

    cleaned_count = memory_manager.cleanup_expired_memories()
    assert cleaned_count == 1
    assert item.lifecycle_state == MemoryLifecycleState.EXPIRED

    item2 = await memory_manager.create_memory(
        content="Old knowledge memory to auto-archive",
        retention=RetentionPolicy(max_age_days=30, auto_archive=True),
    )
    item2.created_at = datetime.now(timezone.utc) - timedelta(days=35)

    cleaned_count2 = memory_manager.cleanup_expired_memories()
    assert cleaned_count2 == 1
    assert item2.lifecycle_state == MemoryLifecycleState.ARCHIVED


@pytest.mark.asyncio
async def test_permission_denied_raises_error(memory_manager, permission_manager):
    permission_manager.check_permission.return_value = False

    with pytest.raises(PermissionError, match="Unauthorized memory creation"):
        await memory_manager.create_memory(content="Restricted memory creation")


@pytest.mark.asyncio
async def test_singleton_get_and_reset():
    reset_memory_manager()
    mgr1 = get_memory_manager()
    mgr2 = get_memory_manager()
    assert mgr1 is mgr2
    reset_memory_manager()
