import json
import statistics
import sys
from pathlib import Path


def compute_latencies(trace_path="experiments/results/trace.jsonl"):
    path = Path(trace_path)
    if not path.exists():
        print(f"Trace file not found: {trace_path}")
        return {}

    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    tasks, t_r_list, t_rec_list, t_norec_list = {}, [], [], []

    for ev in events:
        key = (ev.get("run_id"), ev.get("task_id"), ev.get("attempt", 1))
        tasks.setdefault(key, {})[ev.get("stage")] = ev.get("timestamp_ns")
        tasks[key]["config"] = ev.get("config", "healing")

    for key, stages in tasks.items():
        if "stage1_error_parsing_start" in stages and "stage5_recovery_execution_end" in stages:
            t_r_list.append((stages["stage5_recovery_execution_end"] - stages["stage1_error_parsing_start"]) / 1e6)
        elif "failure_detected" in stages and "re_enqueue" in stages:
            t_r_list.append((stages["re_enqueue"] - stages["failure_detected"]) / 1e6)

        if "task_dispatch" in stages and "task_completion" in stages:
            duration = (stages["task_completion"] - stages["task_dispatch"]) / 1e6
            if stages.get("config") == "no_recovery":
                t_norec_list.append(duration)
            else:
                t_rec_list.append(duration)

    def stats(vals):
        return {"mean": statistics.mean(vals), "median": statistics.median(vals), "n": len(vals)} if vals else {}

    res = {"T_R": stats(t_r_list), "T_rec": stats(t_rec_list), "T_no_rec": stats(t_norec_list)}
    for name, s in res.items():
        print(f"{name}: mean={s.get('mean', 0.0):.3f}ms, median={s.get('median', 0.0):.3f}ms (n={s.get('n', 0)})")
    return res


if __name__ == "__main__":
    compute_latencies(sys.argv[1] if len(sys.argv) > 1 else "experiments/results/trace.jsonl")
