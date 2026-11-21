import json
import os
import time
from typing import Any, Dict, Optional


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
    Records an opt-in nanosecond execution trace event.
    Trace fields: run_id, seed, config, workflow_id, task_id, fault_class, attempt, stage, timestamp_ns.
    """
    if not is_trace_enabled():
        return None

    target_file = trace_file or os.environ.get(
        "PHOENIX_TRACE_FILE", "experiments/results/trace.jsonl"
    )

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

    try:
        dir_path = os.path.dirname(os.path.abspath(target_file))
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    return entry
