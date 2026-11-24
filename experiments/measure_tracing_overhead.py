"""
Phoenix Agents: Tracing Overhead Benchmark
==========================================
Measures recovery handling latency T_R over 100 trials with:
  1. PHOENIX_TRACE OFF (tracing disabled)
  2. PHOENIX_TRACE ON (in-memory buffered nanosecond tracing)
Computes the exact overhead Delta T_tracing.
"""

import asyncio
import os
import statistics
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = BASE_DIR / "backend"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.healing.self_healing_loop import SelfHealingLoop
from app.core.tracing import clear_trace_buffer, flush_trace_buffer
from experiments.fault_injection import FaultInjector
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata, WorkflowStatus


async def run_trial(injector: FaultInjector, is_trace_on: bool, trial_idx: int) -> float:
    wf_id = uuid.uuid4()
    t_id = uuid.uuid4()

    task = Task(
        task_id=t_id,
        workflow_id=wf_id,
        task_name=f"BenchTask_{trial_idx}",
        description="Overhead measurement task",
        category=TaskCategory.WEB_SCRAPING,
        priority=TaskPriority.HIGH,
        status=TaskStatus.FAILED,
        required_tool="test_tool",
        expected_output="done",
    )
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=wf_id, goal="Overhead measurement", status=WorkflowStatus.RUNNING
        ),
        tasks={t_id: task},
    )

    fault = await injector.generate_fault("TIMEOUT", task=task)
    loop = SelfHealingLoop()

    t_start = time.perf_counter_ns()
    res = await loop.process_failure(task, fault, state)
    t_end = time.perf_counter_ns()

    if is_trace_on:
        flush_trace_buffer()
    else:
        clear_trace_buffer()

    assert res.success, f"Trial {trial_idx} failed unexpectedly"
    return (t_end - t_start) / 1e6  # milliseconds


async def benchmark_tracing_overhead(n_trials: int = 100) -> Dict[str, Any]:
    injector = FaultInjector(mode="synthetic", seed=42)

    # Warmup
    print(f"Warming up JIT/cache (10 trials)...")
    for w in range(10):
        await run_trial(injector, False, w)

    # 1. Tracing OFF
    print(f"\n[1/2] Running {n_trials} trials with PHOENIX_TRACE OFF...")
    os.environ["PHOENIX_TRACE"] = "0"
    times_off: List[float] = []
    for i in range(n_trials):
        dur = await run_trial(injector, False, i)
        times_off.append(dur)

    # 2. Tracing ON (Buffered Memory Tracing)
    print(f"[2/2] Running {n_trials} trials with PHOENIX_TRACE ON (Buffered)...")
    os.environ["PHOENIX_TRACE"] = "1"
    os.environ["PHOENIX_TRACE_FILE"] = str(BASE_DIR / "experiments/results/overhead_trace.jsonl")
    times_on: List[float] = []
    for i in range(n_trials):
        dur = await run_trial(injector, True, i)
        times_on.append(dur)

    # Reset
    os.environ["PHOENIX_TRACE"] = "0"

    def summarize(vals: List[float]) -> Dict[str, float]:
        return {
            "mean": statistics.mean(vals),
            "median": statistics.median(vals),
            "std": statistics.stdev(vals),
            "min": min(vals),
            "max": max(vals),
            "n": len(vals),
        }

    s_off = summarize(times_off)
    s_on = summarize(times_on)

    delta_mean = s_on["mean"] - s_off["mean"]
    delta_median = s_on["median"] - s_off["median"]
    pct_overhead = (delta_mean / s_off["mean"]) * 100.0 if s_off["mean"] > 0 else 0.0

    report = {
        "trials": n_trials,
        "tracing_off_ms": s_off,
        "tracing_on_ms": s_on,
        "delta_mean_ms": round(delta_mean, 4),
        "delta_median_ms": round(delta_median, 4),
        "overhead_percent": round(pct_overhead, 2),
    }

    print("\n" + "=" * 60)
    print("PHOENIX TRACING OVERHEAD MEASUREMENT RESULTS (100 Trials)")
    print("=" * 60)
    print(f"Tracing OFF (ms): Mean={s_off['mean']:.3f} ms | Median={s_off['median']:.3f} ms | Std={s_off['std']:.3f} ms")
    print(f"Tracing ON  (ms): Mean={s_on['mean']:.3f} ms | Median={s_on['median']:.3f} ms | Std={s_on['std']:.3f} ms")
    print(f"Delta (T_on - T_off): Mean overhead = {delta_mean:+.4f} ms ({pct_overhead:+.2f}%)")
    print(f"                      Median overhead = {delta_median:+.4f} ms")
    print("=" * 60)

    out_file = BASE_DIR / "experiments/results/tracing_overhead.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    import json
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved overhead report to {out_file}")

    return report


if __name__ == "__main__":
    asyncio.run(benchmark_tracing_overhead(100))
