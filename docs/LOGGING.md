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

### Passing Extra Context Parameters Directly

You can also pass extra context parameters directly to individual log calls:

```python
logger.info("Processing step", step_index=2, status="SUCCESS")
```

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

Unit tests for the logging framework are located in `backend/tests/test_logging.py`. Run the suite with:

```bash
$env:PYTHONPATH="c:\Users\akshitha\Desktop\AetherPhoenix;c:\Users\akshitha\Desktop\AetherPhoenix\backend"
python -m pytest backend/tests -k "not trio"
```
