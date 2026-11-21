"""
Phoenix Agents: Full Benchmark Runner with Configurable Seeds & Repeats
========================================================================
Supports:
  --repeats R (number of independent randomized benchmark runs)
  --seed-base S (base integer seed for reproducibility)
  --mode {synthetic,real_exception} (fault injection mode)
  --output-dir (destination directory for raw JSON/CSV outputs)

Logs to every output file:
  seed, git commit, OS, CPU, RAM, Python version, installed package count, mode.
"""

import argparse
import asyncio
import copy
import csv
import datetime
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = BASE_DIR / "backend"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from experiments.fault_injection import FaultInjector
from experiments.compute_trace_latencies import compute_latencies


def get_git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(BASE_DIR)).decode().strip()
    except Exception:
        return "UNKNOWN"


def get_system_metadata(seed: int, mode: str) -> Dict[str, Any]:
    cpu_model = platform.processor() or "Unknown CPU"
    cpu_cores = os.cpu_count() or 1
    total_ram_gb = 16.0
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            total_ram_gb = round(float(out), 2)
    except Exception:
        pass

    try:
        pip_freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"]).decode().splitlines()
        pkg_count = len(pip_freeze)
    except Exception:
        pkg_count = 0

    return {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_commit": get_git_commit_hash(),
        "seed": seed,
        "mode": mode,
        "os": platform.platform(),
        "os_version": platform.version(),
        "python_version": sys.version,
        "cpu_processor": cpu_model,
        "logical_cpu_cores": cpu_cores,
        "total_ram_gb": total_ram_gb,
        "installed_packages_count": pkg_count,
    }


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.95996  # 95% confidence
    p_hat = successes / total
    denom = 1.0 + (z ** 2) / total
    center = (p_hat + (z ** 2) / (2.0 * total)) / denom
    margin = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / total) + ((z ** 2) / (4.0 * (total ** 2))))
    return round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)


async def run_single_repeat(repeat_idx: int, seed: int, mode: str, output_dir: Path) -> Dict[str, Any]:
    meta = get_system_metadata(seed=seed, mode=mode)
    meta["repeat_index"] = repeat_idx

    injector = FaultInjector(mode=mode, seed=seed)

    # 1. 125-trial fault suite (5 classes x 25 trials)
    classes = [
        ("TIMEOUT", True),
        ("MISSING_RESOURCE", True),
        ("TOOL_ADAPTER_FAILURE", True),
        ("PERMISSION_DENIED", False),
        ("STATE_INCONSISTENCY", False),
    ]

    suite_results = []
    trace_path = output_dir / f"trace_rep_{repeat_idx}_seed_{seed}.jsonl"
    os.environ["PHOENIX_TRACE"] = "1"
    os.environ["PHOENIX_TRACE_FILE"] = str(trace_path)
    os.environ["PHOENIX_SEED"] = str(seed)
    os.environ["PHOENIX_RUN_ID"] = f"run_rep_{repeat_idx}"

    from app.agents.healing.self_healing_loop import SelfHealingLoop
    from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
    from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata, WorkflowStatus
    import uuid

    class_stats: Dict[str, Dict[str, Any]] = {}

    for fc, is_rec in classes:
        success_count = 0
        total_trials = 25
        for i in range(total_trials):
            wf_id = uuid.uuid4()
            t_id = uuid.uuid4()
            task = Task(
                task_id=t_id,
                workflow_id=wf_id,
                task_name=f"BenchTask_{fc}_{i}",
                description=f"Evaluation task for {fc}",
                category=TaskCategory.WEB_SCRAPING,
                priority=TaskPriority.HIGH,
                status=TaskStatus.FAILED,
                required_tool="test_tool",
                expected_output="Extracted data",
            )
            state = SharedWorkflowState(
                metadata=WorkflowMetadata(workflow_id=wf_id, goal=f"Bench {fc}", status=WorkflowStatus.RUNNING),
                tasks={t_id: task},
            )
            fault = await injector.generate_fault(fc, task=task)
            loop = SelfHealingLoop()
            res = await loop.process_failure(task, fault, state)
            if res.success:
                success_count += 1
            suite_results.append({
                "trial": i,
                "fault_class": fc,
                "expected_recoverable": is_rec,
                "success": res.success,
                "root_cause": res.root_cause,
                "strategy": res.recovery_strategy,
            })

        ci_low, ci_high = wilson_score_interval(success_count, total_trials)
        class_stats[fc] = {
            "successes": success_count,
            "total": total_trials,
            "rate": round(success_count / total_trials, 4),
            "ci_95": [ci_low, ci_high],
        }

    # Compute trace latencies
    latencies = compute_latencies(str(trace_path))

    report = {
        "metadata": meta,
        "class_stats": class_stats,
        "latencies": latencies,
        "total_trials": len(suite_results),
        "raw_results": suite_results,
    }

    raw_file = output_dir / f"raw_rep_{repeat_idx}_seed_{seed}.json"
    raw_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


async def main():
    parser = argparse.ArgumentParser(description="Phoenix Agents Multi-Seed Benchmark Suite")
    parser.add_argument("--repeats", type=int, default=1, help="Number of benchmark repeats")
    parser.add_argument("--seed-base", type=int, default=42, help="Base seed")
    parser.add_argument("--mode", choices=["synthetic", "real_exception"], default="synthetic", help="Fault injection mode")
    parser.add_argument("--output-dir", default="experiments/results/raw", help="Output directory")

    args = parser.parse_args()
    out_dir = BASE_DIR / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting benchmark runs: repeats={args.repeats}, seed_base={args.seed_base}, mode={args.mode}")
    all_reports = []

    for r in range(args.repeats):
        current_seed = args.seed_base + r
        print(f"\n--- Running Repeat {r + 1}/{args.repeats} (Seed: {current_seed}) ---")
        rep = await run_single_repeat(r, current_seed, args.mode, out_dir)
        all_reports.append(rep)
        print(f"Repeat {r + 1} completed. Class recovery stats:")
        for fc, st in rep["class_stats"].items():
            print(f"  {fc:25}: {st['successes']}/{st['total']} ({st['rate']*100:.1f}%, 95% CI: [{st['ci_95'][0]*100:.1f}%, {st['ci_95'][1]*100:.1f}%])")

    summary_file = BASE_DIR / "experiments/results/all_repeats_summary.json"
    summary_file.write_text(json.dumps(all_reports, indent=2), encoding="utf-8")
    print(f"\nAll repeats finished. Saved summary to {summary_file}")


if __name__ == "__main__":
    asyncio.run(main())
