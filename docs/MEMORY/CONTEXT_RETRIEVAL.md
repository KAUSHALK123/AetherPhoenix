# Context Retrieval Documentation

## Overview

The **Context Retrieval** service (`ContextRetrievalService`) provides a dedicated, intelligent memory filtering and knowledge selection component for AI agents (`PlannerAgent`, `WorkerAgent`, `SupervisorAgent`, `HealingAgent`).

Rather than passing the entire memory store or relying solely on simple keyword matches, `ContextRetrievalService` analyzes the current task details, workflow goal, user request, and agent role to construct targeted semantic queries, filter out low-relevance or unrelated memories, apply strict result limits (`max_items`), preserve source metadata, and sanitize sensitive information before injection into agent prompts.

---

## Architecture & Design Principles

```
┌─────────────────────────────────────────────────────────────┐
│                          AI Agents                          │
│     (PlannerAgent / WorkerAgent / HealingAgent / etc.)      │
└──────────────────────────────┬──────────────────────────────┘
                               │ Context Retrieval Request
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Context Retrieval Service                  │
│             (app.memory.context_retrieval)                  │
├─────────────────────────────────────────────────────────────┤
│ • Intelligent Query Construction                             │
│ • Agent-Specific Category & Relevance Weighting              │
│ • Workflow-Aware Task History Enrichment                    │
│ • Privacy Sanitization & Redaction                          │
│ • Context Limit Enforcement (max_items)                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG Pipeline Service                     │
│                (app.memory.rag_pipeline)                    │
└─────────────────────────────────────────────────────────────┘
```

1. **Separation of Concerns**: Agents request tailored context by providing their current task/workflow scope without needing to formulate SQL/vector queries or handle data structures directly.
2. **Workflow Awareness**: Incorporates current `workflow_id`, task graph history, and previous task execution results into context decisions.
3. **Agent-Specific Retrieval**: Tailors score boosts and category filters based on agent role (e.g., Planner prioritizes user preferences & project context; Worker prioritizes task instructions & tools; Healing prioritizes error logs & failed task histories).
4. **Context Size Control**: Enforces strict `max_items` limits and `min_relevance_score` thresholds to avoid prompt bloat.
5. **Source Metadata Preservation**: Preserves source origins (`vector_db`, `conversation_memory`, `task_history`, `document`), source IDs, creation timestamps, and tags.
6. **Graceful Error Recovery**: Failures in retrieval subsystems are caught, logged via `app.core.logging`, and fallback response objects are returned safely.

---

## Data Contracts (`shared/contracts/context_retrieval.py`)

### 1. `ContextRetrievalRequest`
Parameters submitted for context retrieval:
- `user_request: str | None`: Natural language user prompt.
- `workflow_id: str | None`: Active workflow UUID string.
- `workflow_goal: str | None`: High-level goal of current workflow.
- `task_id: str | None`: Task identifier being executed.
- `task_name: str | None`: Name of current task.
- `task_description: str | None`: Detailed task instructions.
- `agent_type: AgentType | str`: Target agent (`planner`, `worker`, `supervisor`, `healing`, `orchestrator`, `general`).
- `session_id: str | None`: Active conversation session ID.
- `max_items: int = 5`: Maximum context items to return.
- `min_relevance_score: float = 0.0`: Minimum relevance threshold score.
- `categories: list[MemoryCategory | str] | None`: Filter by memory categories.
- `source_types: list[RAGSourceType | str] | None`: Source memory backends to search.
- `metadata_filter: dict[str, Any]`: Structured key-value metadata filter.
- `include_previous_tasks: bool = True`: Include workflow task execution history.

### 2. `ContextRetrievalResponse`
Structured output returned by the service:
- `query_used: str`: Synthesized query text used for semantic search.
- `items: list[RetrievedContextItem]`: Ranked, filtered context items.
- `formatted_context: str`: Formatted Markdown block ready for prompt injection.
- `total_retrieved: int`: Count of relevant items returned.
- `filtered_count: int`: Count of candidate items excluded by relevance or limit.
- `metadata: dict[str, Any]`: Execution timing, agent type, and status details.

---

## Service API (`ContextRetrievalService`)

Location: `backend/app/memory/context_retrieval.py`

### Methods

- `async retrieve_context(request: ContextRetrievalRequest) -> ContextRetrievalResponse`:
  Core method executing query construction, candidate retrieval, category filtering, agent-specific score tuning, limit enforcement, and formatting.
- `construct_query(request: ContextRetrievalRequest) -> str`:
  Synthesizes a search query string combining user request, task parameters, workflow goal, and agent role.
- `async get_context_for_planner(...) -> ContextRetrievalResponse`:
  Helper tailored for `PlannerAgent` (prioritizes preferences, instructions, project context).
- `async get_context_for_worker(...) -> ContextRetrievalResponse`:
  Helper tailored for `WorkerAgent` (prioritizes task instructions and previous task executions).
- `async get_context_for_healing(...) -> ContextRetrievalResponse`:
  Helper tailored for `HealingAgent` (prioritizes failed task history and error patterns).

---

## Usage Example

```python
from app.memory.context_retrieval import get_context_retrieval_service
from shared.contracts.context_retrieval import ContextRetrievalRequest, AgentType

context_service = get_context_retrieval_service()

# Worker task context retrieval
response = await context_service.get_context_for_worker(
    task=current_task,
    workflow_goal="Automate monthly reporting",
    max_items=3,
)

print(f"Retrieved {response.total_retrieved} items in {response.metadata['execution_time_ms']}ms")
print(response.formatted_context)
```

---

## Logging & Error Handling

- **Logging**: All requests, query constructions, match counts, and execution durations are logged using `app.core.logging.get_logger`.
- **Safety**: Unhandled exceptions within vector stores or task histories are caught and returned in a fallback `ContextRetrievalResponse` with status `"error"`, preserving system stability.
