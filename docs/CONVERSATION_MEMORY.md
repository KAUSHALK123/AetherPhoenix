# Conversation Memory Subsystem

## Overview

The **Conversation Memory** component stores relevant user conversations and structured memory entries, making them accessible to the Planner Agent for future context retrieval.

It allows AetherPhoenix to retain long-term useful information across user sessions (such as user preferences, past instructions, decision points, project context, and clarification answers) while keeping current conversation context separate from persistent memory storage.

---

## Architecture & Design Principles

1. **Storage Abstraction**: Storage operations are abstracted behind `BaseMemoryStorage`. Implementations include:
   - `SQLAlchemyMemoryStorage`: Persistent storage backed by SQLite/PostgreSQL (`conversation_memories` table).
   - `InMemoryMemoryStorage`: Fast, thread-safe memory storage for testing and session-scoped executions.
2. **Decoupled Planner Access**: Memory storage logic is decoupled from Planner execution logic. The Planner accesses memory context using `PlannerMemoryContextAdapter`.
3. **Structured Classification**: Memory entries are classified using `MemoryCategory`:
   - `PREFERENCE`: User formatting, theme, or tool preferences.
   - `INSTRUCTION`: Persistent guidance or constraints specified by the user.
   - `DECISION`: Decisions made during task decomposition or execution.
   - `PROJECT_CONTEXT`: Domain or project background details.
   - `CLARIFICATION`: Past user answers to clarification questions.
   - `GENERAL_CHAT`: Standard conversation entries.
4. **Privacy & Sanitization**: Automatic checking and redacting of sensitive patterns (e.g. passwords, API keys, bearer tokens) before storage.

---

## Data Models

### `ConversationMemoryEntry`

| Field | Type | Description |
|---|---|---|
| `memory_id` | `str` (UUID) | Unique identifier of the memory entry. |
| `session_id` | `str` | Session identifier to which the memory belongs. |
| `role` | `str` | Message role (e.g. `'user'`, `'assistant'`, `'system'`). |
| `content` | `str` | Textual content of the memory (sanitized). |
| `relevance_score` | `float` (0.0 to 1.0) | Weight for context retrieval relevance. |
| `category` | `MemoryCategory` | Classification tag. |
| `metadata` | `dict[str, Any]` | Flexible contextual key-value pairs (sanitized). |
| `created_at` | `datetime` (UTC) | Creation timestamp. |
| `updated_at` | `datetime` (UTC) | Last update timestamp. |

---

## Core Operations

- **`store_memory(...)`**: Insert a new structured memory entry.
- **`get_memory(memory_id)`**: Retrieve a specific memory entry by ID.
- **`get_session_memories(session_id, limit)`**: Retrieve all stored memories for a session.
- **`get_relevant_memories(session_id, category, min_relevance, query_text, limit)`**: Search relevant memories matching criteria.
- **`update_memory(memory_id, updates)`**: Update fields of an existing memory entry.
- **`delete_memory(memory_id)`**: Delete a specific memory entry by ID.
- **`clear_session_memories(session_id)`**: Clear all memories for a session.

---

## Integration with Planner Agent

The `PlannerMemoryContextAdapter` collects relevant conversation memories and injects structured context into `PlannerRequest.context["conversation_memory"]`:

```python
from app.memory.conversation_memory import ConversationMemoryService
from app.memory.planner_integration import PlannerMemoryContextAdapter

service = ConversationMemoryService()
adapter = PlannerMemoryContextAdapter(service)

# Retrieve formatted planner context
context = adapter.get_planner_context(session_id="session-123", min_relevance=0.5)
```

---

## Verification & Testing

Unit tests for Conversation Memory are located at:
- `backend/tests/memory/test_conversation_memory.py`
- `backend/tests/planner/test_planner_memory_integration.py`

Run test suite:
```bash
backend\.venv\Scripts\pytest.exe backend/tests/memory backend/tests/planner
```
