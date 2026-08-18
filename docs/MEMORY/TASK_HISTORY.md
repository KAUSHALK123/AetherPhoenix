# Task History Documentation

## Overview

The **Task History** module provides historical record management for tasks and workflows within the AetherPhoenix AI Desktop Assistant.

It records execution lifecycles (creation, execution start, completion, failure, retries, and timestamps), enabling detailed debugging, auditing, supervisor recovery, self-healing, and long-term conversation memory.

---

## Architecture & Data Contracts

### 1. `TaskHistoryRecord` (`shared/contracts/task_history.py`)

Represents an atomic snapshot entry of a task execution attempt or status transition.

| Field | Type | Description |
|---|---|---|
| `history_id` | `UUID` | Unique record identifier |
| `task_id` | `UUID` | ID of the target task |
| `workflow_id` | `UUID` | Parent workflow ID |
| `parent_task_id` | `UUID \| None` | Parent task ID in task graph |
| `task_name` | `str` | Name of the task |
| `task_category` | `TaskCategory \| str` | Category (BROWSER, DESKTOP, etc.) |
| `assigned_agent` | `str` | Agent executing the task (`WorkerAgent`, etc.) |
| `required_tool` | `str \| None` | Tool required for execution |
| `status` | `TaskStatus` | Task lifecycle state (`CREATED`, `RUNNING`, `COMPLETED`, `FAILED`, `HEALING`) |
| `retry_count` | `int` | Number of retries attempted |
| `attempt_number` | `int` | Specific attempt number |
| `inputs` | `dict[str, Any]` | Inputs passed to the task |
| `outputs` | `dict[str, Any]` | Outputs produced by successful execution |
| `error` | `TaskError \| None` | Error details if execution failed |
| `execution_time_ms` | `float` | Duration of execution in milliseconds |
| `created_at` | `datetime` | Creation timestamp |
| `started_at` | `datetime \| None` | Execution start timestamp |
| `completed_at` | `datetime \| None` | Completion timestamp |
| `metadata` | `dict[str, Any]` | Additional contextual metadata |

---

### 2. `WorkflowHistoryRecord` (`shared/contracts/task_history.py`)

Represents top-level lifecycle metadata and task records for an entire workflow execution.

| Field | Type | Description |
|---|---|---|
| `workflow_id` | `UUID` | Unique workflow identifier |
| `conversation_id` | `UUID \| None` | Associated user conversation ID |
| `user_id` | `str \| None` | Associated user ID |
| `goal` | `str` | User prompt / workflow goal |
| `status` | `str` | Workflow status (`CREATED`, `RUNNING`, `COMPLETED`, `FAILED`) |
| `total_tasks` | `int` | Total count of tasks |
| `completed_tasks` | `int` | Count of completed tasks |
| `failed_tasks` | `int` | Count of failed tasks |
| `tasks_history` | `list[TaskHistoryRecord]` | List of task history entries |
| `created_at` | `datetime` | Creation timestamp |
| `started_at` | `datetime \| None` | Start timestamp |
| `completed_at` | `datetime \| None` | Completion timestamp |

---

## Service API (`TaskHistoryService`)

Location: `backend/app/memory/task_history.py`

### Recording Methods

- `record_task_created(task: Task, metadata=None) -> TaskHistoryRecord`
- `record_task_started(task: Task, agent_name="WorkerAgent", inputs=None, metadata=None) -> TaskHistoryRecord`
- `record_task_completed(task_id: UUID, result: ExecutionResult, metadata=None) -> TaskHistoryRecord`
- `record_task_failed(task_id: UUID, error: TaskError | Exception | str, metadata=None) -> TaskHistoryRecord`
- `record_retry_attempt(task_id: UUID, attempt_number: int, reason=None, metadata=None) -> TaskHistoryRecord`
- `record_workflow_status(workflow_id: UUID, goal="", status="RUNNING", metadata=None) -> WorkflowHistoryRecord`

### Query & Filtering Methods

- `get_task_history(task_id: UUID) -> list[TaskHistoryRecord]`
- `get_workflow_history(workflow_id: UUID) -> WorkflowHistoryRecord | None`
- `get_workflow_task_records(workflow_id: UUID) -> list[TaskHistoryRecord]`
- `filter_history(workflow_id=None, status=None, agent_name=None, category=None, start_time=None, end_time=None, limit=None) -> list[TaskHistoryRecord]`
- `clear_history() -> None`

---

## Integrations

- **Runtime Kernel & Context**: Automatically tracks workflow initialization, session contexts, and completion states.
- **Worker Agent**: Automatically records task execution start, tool execution, execution results (outputs, duration), and exceptions.
- **Supervisor Agent**: Automatically records validation failures and self-healing retry triggers.
