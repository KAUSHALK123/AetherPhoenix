# Retrieval-Augmented Generation (RAG) Pipeline Documentation

## Overview

The **Retrieval-Augmented Generation (RAG) Pipeline** provides a decoupled, structured retrieval system for AetherPhoenix. It allows AI agents (such as `PlannerAgent` and `WorkerAgent`) to query stored knowledge—including long-term vector embeddings, conversation memory, task history, and documents—and inject relevant context into their task execution without intertwining retrieval mechanics with agent reasoning.

---

## Architecture & Design Principles

```
┌─────────────────────────────────────────────────────────┐
│                       AI Agents                         │
│           (PlannerAgent / WorkerAgent / etc.)           │
└───────────────────────────┬─────────────────────────────┘
                            │ Queries / Context Enrichment
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  RAG Pipeline Service                   │
│               (app.memory.rag_pipeline)                 │
└───────┬───────────────────┬───────────────────┬─────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌─────────────────┐   ┌──────────────┐
│  Vector DB    │   │ Conversation    │   │ Task History │
│   Service     │   │ Memory Service  │   │   Service    │
└───────────────┘   └─────────────────┘   └──────────────┘
```

1. **Separation of Concerns**: Agents submit retrieval requests or receive enriched requests/tasks without managing database connections, vector embedding logic, or similarity scoring.
2. **Relevance Thresholding & Context Ranking**: Results are filtered by cosine similarity / relevance thresholds (`min_score`) and ranked in descending order. Irrelevant or low-scoring matches are excluded.
3. **Source Metadata Preservation**: Every context item preserves its source type (`vector_db`, `conversation_memory`, `task_history`, `document`), memory ID, category, session ID, and metadata tags.
4. **Data Sanitization & Privacy**: Sensitive patterns (API keys, passwords, bearer tokens) are automatically redacted before formatting context.
5. **Non-Authoritative Context**: Formatted context blocks include explicit disclaimers instructing agents that retrieved information is reference context and must be validated.

---

## Data Contracts (`shared/contracts/rag.py`)

### 1. `RetrievalQuery`
Represents parameters for a retrieval query:
- `query_text: str`: Natural language search query.
- `top_k: int = 5`: Maximum context items to return.
- `min_score: float = 0.0`: Minimum relevance threshold score (-1.0 to 1.0).
- `session_id: str | None`: Optional session ID filter.
- `category: str | None`: Optional memory category tag filter.
- `source_types: list[RAGSourceType] | None`: List of sources to search (`vector_db`, `conversation_memory`, `task_history`).
- `metadata_filter: dict[str, Any]`: Additional key-value dictionary filter matched against stored records.

### 2. `RetrievedContextItem`
Represents an individual retrieved item:
- `item_id: str`: Unique context item ID.
- `content: str`: Sanitized document snippet or memory content.
- `score: float`: Cosine similarity or relevance score.
- `source_type: RAGSourceType`: Originating backend system.
- `source_id: str | None`: Unique ID from the originating system (`memory_id`, `task_id`).
- `metadata: dict[str, Any]`: Associated metadata tags.
- `created_at: datetime`: Record creation timestamp.

### 3. `RAGContext`
Encapsulates the complete result of a retrieval operation:
- `query: str`: Original query string.
- `items: list[RetrievedContextItem]`: Ranked list of matching items.
- `formatted_context: str`: Markdown context block ready for prompt injection.
- `total_retrieved: int`: Count of matching items returned.
- `retrieval_metadata: dict[str, Any]`: Performance details (execution duration in ms, candidate count, score thresholds).

---

## Service API (`RAGPipelineService`)

Location: `backend/app/memory/rag_pipeline.py`

### Methods

- `async retrieve(query: RetrievalQuery | str, top_k: int = 5, min_score: float = 0.0, ...) -> RAGContext`:
  Executes similarity search, metadata filtering, score ranking, and context formatting across configured memory backends.
- `async enrich_planner_request(request: PlannerRequest, top_k: int = 5, min_score: float = 0.5) -> PlannerRequest`:
  Retrieves relevant context for the incoming planner request message and attaches `rag_context` and `retrieved_knowledge` to `request.context`.
- `async enrich_worker_task(task: Task, query_text: str | None = None, top_k: int = 5, min_score: float = 0.5) -> Task`:
  Retrieves relevant context for a worker task and attaches `rag_context` and `retrieved_knowledge` to `task.inputs`.

---

## Context Builder (`RAGContextBuilder`)

`RAGContextBuilder.build_formatted_context(items, query)` formats ranked context items into structured Markdown:

```markdown
### Relevant Context (Retrieved Knowledge)
*Note: Retrieved information is provided for reference context. Verify all information during planning and execution.*

#### Context Item 1 (Source: vector_db | Score: 0.880 | ID: mem_123 | Metadata: [category=preference])
The user prefers slide presentations with a dark mode glassmorphism theme.
```

---

## Usage Example

```python
from app.memory.rag_pipeline import get_rag_pipeline

rag_service = get_rag_pipeline()

# 1. Direct query
rag_context = await rag_service.retrieve(
    query="What slide presentation style does the user prefer?",
    top_k=3,
    min_score=0.1,
)

print(f"Retrieved {rag_context.total_retrieved} items in {rag_context.retrieval_metadata['execution_time_ms']}ms")
print(rag_context.formatted_context)

# 2. Enriching a PlannerRequest
enriched_request = await rag_service.enrich_planner_request(planner_request)
```

---

## Error Handling & Logging

- **Logging**: Integrates with `app.core.logging.get_logger`. Logs query parameters, match counts, retrieval duration, and any backend warnings.
- **Graceful Error Recovery**: Unhandled exceptions during vector search or memory lookup are caught, logged as errors, and return a clean fallback `RAGContext` with `total_retrieved=0` and error details in `retrieval_metadata`.
