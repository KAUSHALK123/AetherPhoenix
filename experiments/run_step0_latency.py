import asyncio
import os
import shutil
import statistics
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import sys
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.healing.self_healing_loop import SelfHealingLoop
from app.core.permissions.models import ExecutionMode
from app.tools.registry import ToolRegistry
from shared.contracts.execution import ExecutionResult, TaskError
from shared.contracts.permission import RiskLevel
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.tool import Tool, ToolHealth, ToolState
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata


def compute_distribution_stats(vals: List[float]) -> Dict[str, Any]:
    if not vals:
        return {"mean": 0.0, "std": 0.0, "median": 0.0, "iqr": 0.0, "min": 0.0, "max": 0.0, "n": 0}
    n = len(vals)
    mean_val = statistics.mean(vals)
    std_val = statistics.stdev(vals) if n > 1 else 0.0
    median_val = statistics.median(vals)
    sorted_vals = sorted(vals)
    q1 = sorted_vals[int(n * 0.25)]
    q3 = sorted_vals[int(n * 0.75)]
    iqr_val = q3 - q1
    return {
        "mean": round(mean_val, 4),
        "std": round(std_val, 4),
        "median": round(median_val, 4),
        "iqr": round(iqr_val, 4),
        "min": round(min(vals), 4),
        "max": round(max(vals), 4),
        "n": n,
    }


def get_configured_tool_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(Tool(
        name="browser_tool",
        status=ToolState.UNAVAILABLE,
        health=ToolHealth.FAILED,
        adapter="BrowserAdapter",
    ))
    reg.register(Tool(
        name="web_research_tool",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="WebResearchAdapter",
    ))
    reg.register(Tool(
        name="web_research",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="WebResearchAdapter",
    ))
    return reg


async def main():
    os.environ["PHOENIX_TRACE"] = "0"
    reg = get_configured_tool_registry()
    loop = SelfHealingLoop(tool_registry=reg, max_retries=3, max_healing_attempts=3)

    print("Re-running Step 0b Latencies in ONE run with PHOENIX_TRACE=0...")

    # 1. Measure T_R and T_rec across the recoverable faults (Timeout, Missing Resource, Tool/Adapter)
    # 75 faults x 30 repeats = 2250 observations
    t_r_list = []
    t_rec_list = []

    recoverable_classes = ["TIMEOUT", "MISSING_RESOURCE", "TOOL_ADAPTER_FAILURE"]
    for rep in range(30):
        for fc in recoverable_classes:
            for idx in range(25):
                t_id = uuid.uuid4()
                wf_id = uuid.uuid4()
                task = Task(
                    task_id=t_id,
                    workflow_id=wf_id,
                    task_name=f"LatTrial_{fc}_{idx}",
                    description="Latency trial",
                    required_tool="browser_tool" if fc == "TOOL_ADAPTER_FAILURE" else "web_research_tool",
                    expected_output="done",
                    category=TaskCategory.WEB_RESEARCH,
                    priority=TaskPriority.HIGH,
                    status=TaskStatus.FAILED,
                    risk_level=RiskLevel.LOW,
                )
                state = SharedWorkflowState(
                    metadata=WorkflowMetadata(workflow_id=wf_id, goal="Latency test", execution_mode=ExecutionMode.SAFE),
                    tasks={t_id: task},
                    running_tasks=[t_id],
                )

                if fc == "TIMEOUT":
                    fault = TimeoutError("Request timed out after 30000ms")
                elif fc == "MISSING_RESOURCE":
                    fault = FileNotFoundError("[Errno 2] No such file or directory: 'artifact.json'")
                else:
                    fault = TaskError(error_code="TOOL_UNAVAILABLE", error_message="Browser service is unavailable")

                # Delimiting intervals exactly:
                # Interval T_rec starts at task dispatch to recovery loop
                t_dispatch_start = time.perf_counter_ns()

                # Interval T_R starts immediately before SelfHealingLoop.process_failure
                t_r_start = time.perf_counter_ns()
                res = await loop.process_failure(task, fault, state)
                t_r_end = time.perf_counter_ns()

                # Execution and supervisor validation on mock adapter
                if res.success:
                    task.retry_count += 1
                    task.status = TaskStatus.COMPLETED
                else:
                    task.status = TaskStatus.FAILED

                t_dispatch_end = time.perf_counter_ns()

                t_r_ms = (t_r_end - t_r_start) / 1e6
                t_rec_ms = (t_dispatch_end - t_dispatch_start) / 1e6

                t_r_list.append(t_r_ms)
                t_rec_list.append(t_rec_ms)

    # 2. Fail-fast baseline: immediate task failure (125 faults x 30 repeats = 3750 observations)
    t_norec_list = []
    for rep in range(30):
        for idx in range(125):
            t_id = uuid.uuid4()
            wf_id = uuid.uuid4()
            task = Task(
                task_id=t_id,
                workflow_id=wf_id,
                task_name=f"FailFast_{idx}",
                description="Fail-fast baseline",
                required_tool="web_research_tool",
                expected_output="done",
                category=TaskCategory.WEB_RESEARCH,
                priority=TaskPriority.HIGH,
                status=TaskStatus.RUNNING,
            )
            t_start = time.perf_counter_ns()
            task.status = TaskStatus.FAILED
            t_end = time.perf_counter_ns()
            t_norec_list.append((t_end - t_start) / 1e6)

    # 3. Real filesystem latency: 100 trials of NTFS directory creation + artifact writing
    base_tmp = BASE_DIR / "experiments/temp_real_fs_bench"
    real_fs_list = []
    for i in range(100):
        target_dir = base_tmp / f"dir_{i}" / "sub"
        target_file = target_dir / "output.dat"
        t0 = time.perf_counter_ns()
        os.makedirs(target_dir, exist_ok=True)
        target_file.write_bytes(b"phoenix verified output artifact data")
        assert target_file.exists()
        t1 = time.perf_counter_ns()
        real_fs_list.append((t1 - t0) / 1e6)
        shutil.rmtree(base_tmp, ignore_errors=True)

    st_tr = compute_distribution_stats(t_r_list)
    st_trec = compute_distribution_stats(t_rec_list)
    st_tnorec = compute_distribution_stats(t_norec_list)
    st_fs = compute_distribution_stats(real_fs_list)

    print("\n--- RESULTS (ONE RUN, TRACING OFF) ---")
    print(f"T_R:       mean={st_tr['mean']:.4f} ms, std={st_tr['std']:.4f}, median={st_tr['median']:.4f}, iqr={st_tr['iqr']:.4f}, min={st_tr['min']:.4f}, max={st_tr['max']:.4f}, n={st_tr['n']}")
    print(f"T_rec:     mean={st_trec['mean']:.4f} ms, std={st_trec['std']:.4f}, median={st_trec['median']:.4f}, iqr={st_trec['iqr']:.4f}, min={st_trec['min']:.4f}, max={st_trec['max']:.4f}, n={st_trec['n']}")
    print(f"T_no_rec:  mean={st_tnorec['mean']:.4f} ms, std={st_tnorec['std']:.4f}, median={st_tnorec['median']:.4f}, iqr={st_tnorec['iqr']:.4f}, min={st_tnorec['min']:.4f}, max={st_tnorec['max']:.4f}, n={st_tnorec['n']}")
    print(f"Real FS:   mean={st_fs['mean']:.4f} ms, std={st_fs['std']:.4f}, median={st_fs['median']:.4f}, iqr={st_fs['iqr']:.4f}, min={st_fs['min']:.4f}, max={st_fs['max']:.4f}, n={st_fs['n']}")

    import json
    out = {
        "T_R": st_tr,
        "T_rec": st_trec,
        "T_no_rec": st_tnorec,
        "Real_FS": st_fs,
    }
    with open(BASE_DIR / "experiments/results/step0_latencies.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
