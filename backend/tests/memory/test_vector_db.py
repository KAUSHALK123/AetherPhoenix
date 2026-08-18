from uuid import uuid4

import pytest

from app.memory.vector_db import (
    DeterministicHashEmbeddingProvider,
    InMemoryVectorStoreProvider,
    MockEmbeddingProvider,
    VectorDatabaseService,
    reset_vector_db_service,
)


@pytest.fixture
def service():
    """Provides a clean default VectorDatabaseService for each test."""
    return reset_vector_db_service()


@pytest.mark.asyncio
async def test_embedding_provider_generation():
    """Verifies embedding generation dimension and determinism."""
    provider = DeterministicHashEmbeddingProvider(dimension=64)
    assert provider.dimension == 64

    vec1 = await provider.embed_text("I prefer presentations with 10 slides.")
    assert len(vec1) == 64

    vec2 = await provider.embed_text("I prefer presentations with 10 slides.")
    assert vec1 == vec2  # Deterministic

    vec_batch = await provider.embed_batch(["text one", "text two"])
    assert len(vec_batch) == 2
    assert len(vec_batch[0]) == 64


@pytest.mark.asyncio
async def test_store_and_retrieve_memory(service):
    """
    Verifies storing a text memory into vector storage and retrieving by memory ID.
    """
    mem_id = uuid4()

    text = "The user prefers modern sleek dark mode UI."
    metadata = {"category": "preference", "user_id": "user_123"}

    rec = await service.store_memory(memory_id=mem_id, text=text, metadata=metadata)
    assert rec.memory_id == mem_id
    assert rec.document == text
    assert rec.metadata == metadata
    assert len(rec.vector) > 0

    retrieved = await service.get_memory_vector(mem_id)
    assert retrieved is not None
    assert retrieved.document == text
    assert retrieved.metadata.get("category") == "preference"


@pytest.mark.asyncio
async def test_similarity_search(service):
    """Verifies semantic similarity ranking across stored vector memories."""
    m1 = uuid4()
    m2 = uuid4()
    m3 = uuid4()

    await service.store_memory(m1, "I prefer slide presentations with 10 slides.")
    await service.store_memory(m2, "My favorite food is spicy Italian pizza.")
    await service.store_memory(m3, "Electric cars use lithium batteries.")

    # Search for presentation preferences
    results = await service.search_similar(
        "Make a presentation about electric cars.", top_k=3
    )
    assert len(results) > 0
    # Search for pizza
    food_results = await service.search_similar("spicy pizza food", top_k=1)
    assert len(food_results) == 1
    assert food_results[0].memory_id == m2


@pytest.mark.asyncio
async def test_similarity_search_with_metadata_filter(service):
    """Verifies similarity search with metadata key-value filtering."""
    m1 = uuid4()
    m2 = uuid4()

    await service.store_memory(
        m1,
        "Python is a programming language.",
        metadata={"domain": "tech", "level": "backend"},
    )
    await service.store_memory(
        m2,
        "Python snakes live in tropical forests.",
        metadata={"domain": "nature", "level": "wildlife"},
    )

    # Search with domain='tech' filter
    results = await service.search_similar(
        "Python programming code",
        filter_metadata={"domain": "tech"},
    )
    assert len(results) == 1
    assert results[0].memory_id == m1

    # Search with non-existent filter
    empty_results = await service.search_similar(
        "Python",
        filter_metadata={"domain": "finance"},
    )
    assert len(empty_results) == 0


@pytest.mark.asyncio
async def test_similarity_search_no_results_or_high_min_score(service):
    """
    Verifies behavior when min_score is higher than matches or query text is empty.
    """
    m1 = uuid4()
    await service.store_memory(m1, "Some memory text.")

    # Empty query text
    empty_q = await service.search_similar("")
    assert empty_q == []

    # High min_score threshold
    strict = await service.search_similar("Unrelated query", min_score=0.9999)
    assert len(strict) == 0


@pytest.mark.asyncio
async def test_duplicate_memory_update(service):
    """
    Verifies updating an existing memory vector by re-storing with the same memory ID.
    """
    mem_id = uuid4()

    await service.store_memory(mem_id, "Original preference text v1")
    v1 = await service.get_memory_vector(mem_id)
    assert v1.document == "Original preference text v1"

    # Update memory
    await service.store_memory(mem_id, "Updated preference text v2")
    v2 = await service.get_memory_vector(mem_id)
    assert v2.document == "Updated preference text v2"

    count = await service.vector_store_provider.count()
    assert count == 1


@pytest.mark.asyncio
async def test_delete_memory_vector(service):
    """Verifies deleting a stored memory vector by memory ID."""
    mem_id = uuid4()
    await service.store_memory(mem_id, "Temporary vector text")

    deleted = await service.delete_memory_vector(mem_id)
    assert deleted is True

    assert await service.get_memory_vector(mem_id) is None
    # Deleting non-existent
    assert await service.delete_memory_vector(mem_id) is False


@pytest.mark.asyncio
async def test_empty_text_storage_error(service):
    """Verifies ValueError when attempting to store empty memory text."""
    with pytest.raises(ValueError, match="Cannot embed or store empty memory text"):
        await service.store_memory(uuid4(), "")


@pytest.mark.asyncio
async def test_mock_embedding_provider_integration():
    """Verifies custom MockEmbeddingProvider behavior in vector service."""
    mock_provider = MockEmbeddingProvider(
        dimension=4, fixed_vector=[1.0, 0.0, 0.0, 0.0]
    )
    store = InMemoryVectorStoreProvider()
    service = VectorDatabaseService(
        embedding_provider=mock_provider, vector_store_provider=store
    )

    m1 = uuid4()
    rec = await service.store_memory(m1, "Mock text")
    assert rec.vector == [1.0, 0.0, 0.0, 0.0]

    results = await service.search_similar("Query text")
    assert len(results) == 1
    assert results[0].score == 1.0
