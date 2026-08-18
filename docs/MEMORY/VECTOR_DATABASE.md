# Vector Database Foundation Documentation

## Overview

The **Vector Database** module provides the storage and retrieval foundation required for semantic memory in AetherPhoenix.

It converts text memory entries into dense vector embeddings, stores them with associated memory IDs and metadata, and performs rank-ordered cosine similarity searches for semantic retrieval across long-term preferences, past user instructions, and workflow context.

---

## Architecture & Interfaces

### 1. Data Contracts (`shared/contracts/vector.py`)

- **`VectorRecord`**: Represents an embedded memory record with `memory_id`, `vector: list[float]`, `document: str`, `metadata: dict[str, Any]`, and `created_at`.
- **`VectorSearchResult`**: Represents a similarity query result with `memory_id`, `score: float` (Cosine similarity from -1.0 to 1.0), `document: str`, and `metadata: dict[str, Any]`.

---

### 2. Embedding Abstraction (`BaseEmbeddingProvider`)

| Provider | Description |
|---|---|
| `DeterministicHashEmbeddingProvider` | Default lightweight provider producing normalized float vectors (default dimension 128) via feature hashing & n-gram tokenization. Requires zero external API keys or heavy binary ML frameworks. |
| `MockEmbeddingProvider` | Configurable provider for testing fixed vector dimensions or custom embeddings. |

---

### 3. Vector Storage Abstraction (`BaseVectorStoreProvider`)

| Provider | Description |
|---|---|
| `InMemoryVectorStoreProvider` | Default thread-safe in-memory vector database with exact cosine similarity scoring and dictionary metadata filtering. |

---

## Service API (`VectorDatabaseService`)

Location: `backend/app/memory/vector_db.py`

### Methods

- `store_memory(memory_id: UUID | str, text: str, metadata: dict | None = None) -> VectorRecord`:
  Generates vector embedding for document text and stores vector record.
- `search_similar(query_text: str, top_k: int = 5, filter_metadata: dict | None = None, min_score: float = 0.0) -> list[VectorSearchResult]`:
  Embeds `query_text` and performs rank-ordered similarity search with optional metadata filtering.
- `get_memory_vector(memory_id: UUID | str) -> VectorRecord | None`:
  Retrieves stored vector record by memory ID.
- `delete_memory_vector(memory_id: UUID | str) -> bool`:
  Deletes vector record by memory ID.
- `clear() -> None`:
  Clears all vector records from storage.

---

## Usage Example

```python
from app.memory.vector_db import get_vector_db_service

service = get_vector_db_service()

# Store user preferences
await service.store_memory(
    memory_id="pref_001",
    text="I prefer slide presentations with around 10 slides.",
    metadata={"category": "user_preference"},
)

# Search for relevant preferences later
results = await service.search_similar(
    query_text="Make a presentation about electric cars.",
    top_k=3,
    filter_metadata={"category": "user_preference"},
)

for res in results:
    print(f"Match memory_id={res.memory_id}, Score={res.score:.3f}, Text='{res.document}'")
```
