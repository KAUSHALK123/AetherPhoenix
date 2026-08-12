# Centralized Logging Framework

## Overview

AetherPhoenix provides a centralized, structured logging framework designed to capture runtime activities, agent execution logs, errors, warnings, and system events.

The framework supports structured JSON logging for machine parsing, human-readable formatted text logging, context binding for workflow tracking, console output, and local file persistence without external dependencies.

---

## Key Components

The logging framework is located in `backend/app/core/logging/` and consists of:

1. **Logger Interface (`ILogger`)**: Abstract base class defining the standard interface for all logging components.
2. **Structured Logger (`StructuredLogger`)**: Concrete wrapper around Python's standard `logging.Logger` supporting contextual field binding.
3. **Formatters (`JSONLogFormatter` & `TextLogFormatter`)**:
   - `JSONLogFormatter`: Encodes log records as structured JSON strings containing timestamps (ISO 8601 UTC), log levels, logger names, line numbers, contextual fields, and exception tracebacks.
   - `TextLogFormatter`: Formats log records into readable text lines with embedded context dictionaries.
4. **Handlers (`ConsoleHandler` & `FileHandler`)**:
   - Console handler writes formatted logs to `sys.stdout`.
   - File handler writes formatted logs to a rotating file in the configured log directory (defaults to `./logs/aether_phoenix.log`).
5. **Configuration (`setup_logging`)**: Central initialization function invoked at application startup.
6. **Worker Execution Logger (`WorkerExecutionLogger`)**: Specialized execution logger for Worker Agent operations, tracking granular execution lifecycle, tool execution, durations, error information, correlation IDs, and sanitizing payloads.
7. **Sanitizer (`sanitize_log_data`)**: Recursive payload sanitizer masking sensitive values (passwords, tokens, API keys) and truncating oversized strings.

---

## Log Levels

The framework supports five standard log levels:

| Level | Usage |
|---|---|
| `DEBUG` | Detailed diagnostic messages used during development and debugging |
| `INFO` | General operational events (startup, workflow transitions, context creation) |
| `WARNING` / `WARN` | Non-fatal system warnings or unexpected recoverable conditions |
| `ERROR` | System component errors or task execution failures |
| `CRITICAL` | Severe system failures requiring immediate attention |

---

## Usage Guide

### Getting a Logger

To obtain a logger in any module or agent:

```python
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

logger.info("Task execution started")
```

### Context Binding

`StructuredLogger` supports binding contextual key-value pairs (such as `agent_id`, `workflow_id`, `task_id`, `session_id`). Calling `.bind()` creates a new logger instance with the contextual data attached:

```python
agent_logger = logger.bind(agent_id="planner_01", workflow_id="wf_123")

agent_logger.info("Planning workflow execution")
agent_logger.error("Planning failed", exc_info=True)
```

Output log entry (JSON format):

```json
{
  "timestamp": "2026-08-07T22:41:24.123456Z",
  "level": "INFO",
  "logger": "backend.app.agents.planner",
  "message": "Planning workflow execution",
  "module": "planner",
  "function": "execute",
  "line": 42,
  "context": {
    "agent_id": "planner_01",
    "workflow_id": "wf_123"
  }
}
```

### Worker Execution Logging (`WorkerExecutionLogger`)

Worker Agent operations utilize `WorkerExecutionLogger` to emit traceable, structured execution events throughout the execution lifecycle.

#### Execution Event Schema (`WorkerExecutionLog`)

Execution events are structured according to `WorkerExecutionLog`:

| Field | Type | Description |
|---|---|---|
| `execution_id` | `UUID` | Unique execution run identifier per task attempt |
| `correlation_id` | `str \| None` | Cross-cutting trace or session identifier for request tracking |
| `workflow_id` | `UUID` | ID of the parent workflow |
| `task_id` | `UUID` | ID of the executed task |
| `task_name` | `str` | Name of the executed task |
| `tool_name` | `str` | Name of the resolved tool |
| `phase` | `ExecutionPhase` | Granular execution phase (`TASK_START`, `TOOL_SELECTION`, `TOOL_EXECUTION`, `OUTPUT_COLLECTION`, `TASK_COMPLETE`, `TASK_FAILED`) |
| `status` | `ExecutionStatus` | Current phase status (`STARTED`, `IN_PROGRESS`, `TOOL_STARTED`, `TOOL_COMPLETED`, `TOOL_FAILED`, `COMPLETED`, `FAILED`, `CANCELLED`) |
| `duration_ms` | `float` | Elapsed execution duration in milliseconds |
| `inputs` | `dict[str, Any]` | Sanitized task or tool input payload |
| `outputs` | `dict[str, Any]` | Sanitized task or tool output result |
| `error_code` | `str \| None` | Standardized error code if phase or task failed |
| `error_message` | `str \| None` | Human-readable error description |
| `timestamp` | `datetime` | UTC timestamp of the log event |
| `metadata` | `dict[str, Any]` | Supplementary contextual metadata |

#### Worker Execution Example

```python
from app.core.logging import WorkerExecutionLogger

exec_logger = WorkerExecutionLogger.from_task(
    task=task,
    correlation_id="trace_abc_123",
)

exec_logger.log_task_start(inputs={"file_path": "data.csv"})
exec_logger.log_tool_selected(tool_name="csv_parser")
exec_logger.log_tool_start(tool_name="csv_parser", inputs={"file_path": "data.csv"})
exec_logger.log_tool_complete(tool_name="csv_parser", duration_ms=45.2, outputs={"rows": 100})
exec_logger.log_task_complete(duration_ms=110.5, artifacts_count=1)
```

#### Sensitive Data Sanitization

All input and output payloads emitted via `WorkerExecutionLogger` are passed through `sanitize_log_data()`:
- Keys containing sensitive keywords (`api_key`, `password`, `secret`, `token`, `auth`, `credentials`, `private_key`, `bearer`, etc.) are masked as `"***REDACTED***"`.
- String contents exceeding 500 characters are automatically truncated.

---

## Configuration

Logging behavior is configured via `backend/app/core/config.py` / Environment Variables:

| Setting | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Minimum log severity level (`DEBUG`, `INFO`, `WARN`, `ERROR`) |
| `LOG_DIR` | `logs` | Local directory path for log file output |
| `LOG_FILE` | `aether_phoenix.log` | Log file name |
| `LOG_FORMAT_JSON` | `True` | Set `True` for JSON logging, `False` for human-readable text |
| `LOG_CONSOLE_ENABLED` | `True` | Enable/disable console stdout output |
| `LOG_FILE_ENABLED` | `True` | Enable/disable file logging output |

---

## Testing

Unit tests for the logging framework and worker execution logging system are located in:
- `backend/tests/test_logging.py`
- `backend/tests/core/test_execution_logger.py`

Run the test suite with:

```bash
$env:PYTHONPATH="c:\Users\dhany\majorproject\AetherPhoenix;c:\Users\dhany\majorproject\AetherPhoenix\backend"
backend\.venv\Scripts\python.exe -m pytest backend/tests
```
