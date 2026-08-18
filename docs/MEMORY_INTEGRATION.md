# Memory & Knowledge Agent Integration (Issue #8 / #162)

> **Document Status**: Production Ready  
> **Target Subsystem**: `backend/app/memory/integration_hub.py`  
> **Module**: AetherPhoenix Memory & Knowledge Subsystem (Sprint 7)

---

## 1. Subsystem Architecture

The **Memory Integration Hub** (`MemoryIntegrationHub`) unifies all Sprint 7 memory components:
- **Conversation Memory** (`ConversationMemoryService`)
- **Task History** (`TaskHistoryService`)
- **Vector Database** (`VectorDatabaseService`)
- **RAG Pipeline** (`RAGPipelineService`)
- **Memory Management** (`MemoryManager`)

It connects these backends to the primary agent ecosystem:
- **Planner Agent**: Automatic context enrichment (`rag_context`, `retrieved_knowledge`) from previous sessions and permanent knowledge base.
- **Worker Agent**: Task input enrichment with relevant context, automatic result persistence (`TaskStatus.COMPLETED` -> `MemoryItem` + `TaskHistoryRecord`).
- **Supervisor Agent**: Automatic capturing of critical lifecycle milestone events (`WORKFLOW_COMPLETED`, `WORKFLOW_FAILED`, `TASK_FAILED`).
- **Healing Agent**: Diagnostic resolution recording into `TaskHistoryService` retry history and knowledge persistence to prevent recurring planning pitfalls.

---

## 2. End-to-End Information Flow

```
User Request
     │
     ▼
[ Planner Agent ] ◄─────── [ RAG Pipeline / Memory Hub ] (Context Retrieval)
     │
     ▼ (generates plan)
[ Worker Agent ]  ◄─────── [ Enriched Task Inputs ]
     │
     ▼ (executes task)
[ Task Result ]   ───────► [ Memory Manager ] (Stored Knowledge)
     │
     ▼ (monitors)
[ Supervisor ]    ───────► [ Milestone Event Capture ]
     │
     ▼ (if failure occurs)
[ Healing Agent ] ───────► [ Task History Retries & Diagnostic Memories ]
```

---

## 3. Usage Examples

### 3.1 Preparing a Planner Request
```python
from app.memory import get_memory_integration_hub
from shared.contracts.planner import PlannerRequest

hub = get_memory_integration_hub()

request = PlannerRequest(
    session_id="session_123",
    message="Provision a Kubernetes cluster on AWS"
)

# Automatically queries RAG, injects relevant past context, and logs incoming prompt
enriched_request = await hub.prepare_planner_request(request)
```

### 3.2 Recording Worker Execution Results
```python
saved_memory = await hub.record_worker_result(
    task=worker_task,
    output_data={"cluster_id": "k8s-prod-01", "endpoint": "https://k8s.internal"},
    status=TaskStatus.COMPLETED,
    execution_summary="Successfully deployed AWS Kubernetes cluster."
)
```

### 3.3 Recording Healing Resolutions
```python
await hub.record_healing_result(
    task_id=task.task_id,
    workflow_id=task.workflow_id,
    task_error=task_error,
    healing_result=healing_result
)
```
