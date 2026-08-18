# Memory Management Subsystem (Issue #7 / #161)

> **Document Status**: Production Ready  
> **Target Subsystem**: `backend/app/memory/manager.py`  
> **Module**: AetherPhoenix Memory & Knowledge Management

---

## 1. Subsystem Overview

The **Memory Management Service** provides centralized lifecycle control, deduplication, categorization, semantic retrieval, and security enforcement for long-term and short-term agent memory.

### Key Capabilities
- **Lifecycle Management**: Complete state machine transitions (`ACTIVE` -> `ARCHIVED` -> `EXPIRED` -> `DELETED`).
- **Exact & Semantic Deduplication**: Fast SHA-256 content hashing for exact matches combined with cosine similarity vector thresholds for near-duplicates.
- **Retention Policies**: Configurable TTL (seconds) and max-age (days) with automated cleanup (`auto_archive` vs `auto_delete`).
- **Security & Sensitive Data Masking**: Automatic redaction of API keys, passwords, bearer tokens, and private secrets prior to persistence.
- **Vector Database Integration**: Automated bidirectional synchronization with `VectorDatabaseService` (`InMemoryVectorStoreProvider` / external vector stores).
- **Permission Authorization**: Enforces strict operation checks via `PermissionManager` before creating, updating, or deleting memories.

---

## 2. Memory Lifecycle States

```
                +-----------------+
                |   create_memory |
                +--------+--------+
                         |
                         v
                   [  ACTIVE  ]
                   /     |    \
     archive_memory      |     \  cleanup (expired)
            /            |      \
           v             |       v
     [ ARCHIVED ]        |   [ EXPIRED ]
           \             |       /
      restore_memory     |  restore_memory
             \           |     /
              +----> [ ACTIVE ]
                         |
                         | delete_memory
                         v
                   [  DELETED  ]
```

---

## 3. Core Contract Models

Defined in `shared/contracts/memory.py`:

```python
class MemoryItem(BaseModel):
    memory_id: str
    session_id: str | None
    workflow_id: str | None
    task_id: str | None
    memory_type: MemoryType          # USER_PREFERENCE, CONVERSATION, KNOWLEDGE, TASK_RESULT, etc.
    category: MemoryCategory        # PREFERENCE, INSTRUCTION, DECISION, PROJECT_CONTEXT, etc.
    content: str
    content_hash: str
    relevance_score: float          # 0.0 to 1.0
    lifecycle_state: MemoryLifecycleState  # ACTIVE, ARCHIVED, EXPIRED, DELETED
    metadata: dict[str, Any]
    retention: RetentionPolicy      # ttl_seconds, max_age_days, auto_archive, auto_delete
    author_agent: str | None
    vector_id: str | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
```

---

## 4. Usage Examples

### 4.1 Creating and Storing Memory
```python
from app.memory import get_memory_manager
from shared.contracts.memory import MemoryCategory, MemoryType, RetentionPolicy

memory_manager = get_memory_manager()

item = await memory_manager.create_memory(
    content="User prefers TypeScript and dark-mode themes",
    category=MemoryCategory.PREFERENCE,
    memory_type=MemoryType.USER_PREFERENCE,
    session_id="session_123",
    relevance_score=0.95,
    retention=RetentionPolicy(max_age_days=90, auto_archive=True),
    author_agent="PlannerAgent",
)
```

### 4.2 Semantic Memory Search
```python
results = await memory_manager.search_semantic(
    query_text="user frontend preferences styling",
    limit=5,
    min_similarity=0.7,
)

for memory, score in results:
    print(f"[{score:.2f}] {memory.content}")
```

### 4.3 Retention Cleanup
```python
expired_count = memory_manager.cleanup_expired_memories()
print(f"Processed {expired_count} expired memory records.")
```
