import json
import os
import time
from typing import Any, Dict, List, Optional

_TRACE_BUFFER: List[Dict[str, Any]] = []


def is_trace_enabled() -> bool:
    """Check if Phoenix nanosecond tracing is enabled via PHOENIX_TRACE=1."""
    return os.environ.get("PHOENIX_TRACE") == "1"


def record_trace(
    stage: str,
    workflow_id: Any = None,
    task_id: Any = None,
    attempt: int = 1,
    fault_class: Optional[str] = None,
    run_id: Optional[str] = None,
    seed: Optional[int] = None,
    config: Optional[str] = None,
    trace_file: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Records an opt-in nanosecond execution trace event into an in-memory buffer.
    Never performs disk I/O inside timed regions to prevent latency distortions.
    Trace fields: run_id, seed, config, workflow_id, task_id, fault_class, attempt, stage, timestamp_ns.
    """
    if not is_trace_enabled():
        return None

    try:
        seed_val = int(seed if seed is not None else os.environ.get("PHOENIX_SEED", 42))
    except (ValueError, TypeError):
        seed_val = 42

    entry: Dict[str, Any] = {
        "run_id": str(run_id or os.environ.get("PHOENIX_RUN_ID", "default_run")),
        "seed": seed_val,
        "config": str(config or os.environ.get("PHOENIX_CONFIG", "healing")),
        "workflow_id": str(workflow_id) if workflow_id is not None else "",
        "task_id": str(task_id) if task_id is not None else "",
        "fault_class": str(fault_class or os.environ.get("PHOENIX_FAULT_CLASS", "UNKNOWN")),
        "attempt": int(attempt),
        "stage": stage,
        "timestamp_ns": time.perf_counter_ns(),
    }
    if extra:
        entry["extra"] = extra
    if trace_file:
        entry["_target_file"] = trace_file

    _TRACE_BUFFER.append(entry)
    return entry


def get_trace_buffer() -> List[Dict[str, Any]]:
    """Returns a copy of all trace events currently in memory."""
    return list(_TRACE_BUFFER)


def clear_trace_buffer() -> None:
    """Clears all in-memory trace events."""
    global _TRACE_BUFFER
    _TRACE_BUFFER.clear()


def flush_trace_buffer(trace_file: Optional[str] = None) -> int:
    """
    Flushes all buffered trace events to disk in a single batch I/O operation.
    Must be called outside timed regions (e.g. after a trial completes).
    Returns the number of events flushed.
    """
    global _TRACE_BUFFER
    if not _TRACE_BUFFER:
        return 0

    target_file = trace_file or os.environ.get(
        "PHOENIX_TRACE_FILE", "experiments/results/trace.jsonl"
    )

    count = len(_TRACE_BUFFER)
    try:
        dir_path = os.path.dirname(os.path.abspath(target_file))
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(target_file, "a", encoding="utf-8") as f:
            for item in _TRACE_BUFFER:
                # Remove internal routing metadata if present
                clean_item = {k: v for k, v in item.items() if not k.startswith("_")}
                f.write(json.dumps(clean_item) + "\n")
    except Exception:
        pass
    finally:
        _TRACE_BUFFER.clear()

    return count
