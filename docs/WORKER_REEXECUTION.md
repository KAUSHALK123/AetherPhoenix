# Worker Re-execution Support

**Version:** 1.0  
**Status:** Approved & Implemented  
**Owner:** AI Runtime & Healing Team  

---

## Overview

The **Worker Re-execution** mechanism handles controlled task re-executions for approved recovery and retry plans in AetherPhoenix.

When the Healing Agent determines that a failed task is recoverable, it generates an approved recovery plan. The Worker receives the re-execution request through the existing execution infrastructure (`WorkflowEngine` → `WorkerAgent`), rather than Healing executing tools directly.

```
Failure
  ↓
Root Cause Analysis
  ↓
Recovery Plan (Healing Agent)
  ↓
Retry Engine (WorkerReexecutionRequest)
  ↓
Workflow Engine (Task Enqueued)
  ↓
Worker Agent (Permission Revalidated & Tool Executed)
  ↓
Supervisor Agent (Validation & Result Handling)
```

---

## Key Design Principles

1. **Original Task Preservation**: The original `task_id` is strictly preserved across all re-execution attempts.
2. **Attempt Tracking**: Each re-execution attempt generates a unique `attempt_id` (UUID) and tracks incrementing `attempt_number`.
3. **Execution History Integrity**: Prior attempt logs, outputs, timestamps, and parameters are snapshotted into `task.attempt_history` and never deleted.
4. **No Direct Tool Invocation**: Healing never executes tools directly; all tasks pass through `WorkflowEngine` and `WorkerAgent`.
5. **Permission Revalidation**: Required permissions are re-checked against `PermissionManager` on every attempt before calling tool adapters.

---

## Re-execution Contracts

### `WorkerReexecutionRequest`
```python
class WorkerReexecutionRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    attempt_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    workflow_id: UUID
    attempt_number: int = Field(default=1, ge=1)
    recovery_plan_id: Optional[UUID] = None
    recovery_strategy: Optional[str] = None
    modified_parameters: Dict[str, Any] = Field(default_factory=dict)
    original_task_snapshot: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### `WorkerReexecutionResult`
```python
class WorkerReexecutionResult(BaseModel):
    reexecution_id: UUID = Field(default_factory=uuid4)
    attempt_id: UUID
    task_id: UUID
    workflow_id: UUID
    attempt_number: int
    execution_result: ExecutionResult
    previous_attempt_ids: List[UUID] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

---

## Re-execution Flow

1. **Request Formulation**: `WorkerReexecutionManager.create_reexecution_request(...)` snapshots prior attempt state into `task.attempt_history`, sets `task.current_attempt_id`, and applies approved recovery modifications (e.g. fallback tools or parameter tweaks).
2. **Workflow Queueing**: `RetryEngine` enqueues the updated task into `WorkflowEngine`.
3. **Worker Dispatch**: `WorkerAgent` receives the task, revalidates permissions, and calls the registered `ToolAdapter`.
4. **Result & Event Emission**: Emits `WORKER_REEXECUTION_STARTED` and `WORKER_REEXECUTION_COMPLETED` (or `WORKER_REEXECUTION_FAILED`) events, returning `WorkerReexecutionResult` for Supervisor validation.

---

## Security & Safety Rules

- **Permission Manager Enforced**: If permissions are denied or revoked during re-execution, execution fails with `PERMISSION_DENIED`.
- **Infinite Loop Prevention**: Re-executions respect `RetryEngine` signature tracking and maximum retry limits (`default_max_retries=3`).
