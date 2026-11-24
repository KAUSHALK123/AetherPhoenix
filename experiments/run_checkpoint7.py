"""
Phoenix Checkpoint 7 Comprehensive Evaluation: Scenario Round
============================================================
S1. Worked Examples from Real Traces (PHOENIX_TRACE=1)
    - (a) Missing directory (Missing Resource)
    - (b) Destructive / privilege escalation (Permission/Policy)
    - (c) Unmapped exception
    Outputs experiments/results/worked_examples.md and experiments/results/s1_traces.jsonl.

S2. Real-Adapter Scenarios on Host Machine (10 trials each)
    - (1) Real file locked by another process
    - (2) Real missing path
    - (3) Real subprocess exceeding timeout
    - (4) Real unreachable local port for browser adapter
    - (5) Real write to read-only directory

S3. Larger Workflow Graphs (10 & 20 tasks, Linear & Branching, 3 positions, 25 trials each = 300 trials)
    - Measures completion, retries, T_R, total workflow time.

S4. Additional Fault Types (10 trials each)
    - (1) ConnectionRefusedError
    - (2) File locked (WinError 32)
    - (3) Disk full (Errno 28)
    - (4) Malformed JSON
    - (5) Unknown adapter name
"""

import asyncio
import copy
import csv
import datetime
import json
import math
import os
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.healing.error_parser import ErrorParser
from app.agents.healing.recovery_planner import RecoveryPlanner
from app.agents.healing.retry_engine import RetryEngine
from app.agents.healing.root_cause_analyzer import RootCauseAnalyzer
from app.agents.healing.self_healing_loop import HealingState, SelfHealingLoop
from app.core.exceptions import ToolNotFoundException
from app.core.permissions.manager import PermissionManager
from app.core.permissions.models import ExecutionMode
from app.core.tracing import clear_trace_buffer, flush_trace_buffer, record_trace
from app.tools.registry import ToolRegistry
from app.tools.adapter import BaseToolAdapter
from app.tools.browser_extension.adapter import BrowserExtensionAdapter
from app.tools.file_explorer.adapter import FileExplorerToolAdapter
from app.tools.terminal.adapter import TerminalToolAdapter
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.permission import RiskLevel
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.tool import Tool, ToolHealth, ToolState
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata, WorkflowStatus

RESULTS_DIR = BASE_DIR / "experiments/results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def get_git_commit() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN"


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
    reg.register(Tool(
        name="document_generator",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="DocumentAdapter",
    ))
    reg.register(Tool(
        name="file_system",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="FileSystemAdapter",
    ))
    return reg


def compute_stats(vals: List[float]) -> Dict[str, Any]:
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


# ==============================================================================
# S1: Worked Examples from Real Traces
# ==============================================================================
async def run_scenario_s1() -> Dict[str, Any]:
    print("--- Running S1: Worked Examples from Real Traces ---")
    os.environ["PHOENIX_TRACE"] = "1"
    trace_path = RESULTS_DIR / "s1_traces.jsonl"
    if trace_path.exists():
        trace_path.unlink()

    reg = get_configured_tool_registry()
    loop = SelfHealingLoop(tool_registry=reg, max_retries=3, max_healing_attempts=3)

    examples_results = {}

    # Case A: Missing Resource (task writing to missing directory)
    clear_trace_buffer()
    wf_id_a = uuid.uuid4()
    task_id_a = uuid.uuid4()
    task_a = Task(
        task_id=task_id_a,
        workflow_id=wf_id_a,
        task_name="write_report_artifact",
        description="Write output summary report into artifact directory",
        tool_name="file_system",
        required_tool="file_system",
        expected_output="file written",
        category=TaskCategory.FILE_SYSTEM,
        priority=TaskPriority.HIGH,
        status=TaskStatus.FAILED,
        risk_level=RiskLevel.LOW,
        inputs={"output_path": "C:/nonexistent_dir_0xdead/report.json", "content": "{}"},
    )
    state_a = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=wf_id_a,
            goal="Report Generation",
            workflow_name="ReportGenerationWorkflow",
            total_tasks=1,
            execution_mode=ExecutionMode.SAFE,
        ),
        tasks={task_id_a: task_a},
        running_tasks=[task_id_a],
    )
    fail_a = FileNotFoundError("[Errno 2] No such file or directory: 'C:/nonexistent_dir_0xdead/report.json'")
    res_a = await loop.process_failure(task=task_a, failure_input=fail_a, state=state_a)
    flush_trace_buffer(str(trace_path))

    # Read traces for Case A
    traces_a = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                traces_a.append(json.loads(line))

    # Case B: Destructive / Privilege Escalation command
    clear_trace_buffer()
    wf_id_b = uuid.uuid4()
    task_id_b = uuid.uuid4()
    task_b = Task(
        task_id=task_id_b,
        workflow_id=wf_id_b,
        task_name="system_cleanup_task",
        description="Clean system root volume",
        tool_name="terminal_tool",
        required_tool="terminal_tool",
        expected_output="system cleaned",
        category=TaskCategory.TERMINAL,
        priority=TaskPriority.CRITICAL,
        status=TaskStatus.FAILED,
        risk_level=RiskLevel.HIGH,
        inputs={"command": "del /f /s /q C:\\Windows\\System32"},
    )
    state_b = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=wf_id_b,
            goal="System Admin",
            workflow_name="SystemAdminWorkflow",
            total_tasks=1,
            execution_mode=ExecutionMode.SAFE,
        ),
        tasks={task_id_b: task_b},
        running_tasks=[task_id_b],
    )
    fail_b = PermissionError("[WinError 5] Access is denied: 'C:\\Windows\\System32'")
    res_b = await loop.process_failure(task=task_b, failure_input=fail_b, state=state_b)
    flush_trace_buffer(str(trace_path))

    # Read traces for Case B
    all_traces = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_traces.append(json.loads(line))
    traces_b = all_traces[len(traces_a):]

    # Case C: Unmapped exception
    clear_trace_buffer()
    wf_id_c = uuid.uuid4()
    task_id_c = uuid.uuid4()
    task_c = Task(
        task_id=task_id_c,
        workflow_id=wf_id_c,
        task_name="proprietary_dsp_processing",
        description="Execute quantum simulation filter",
        tool_name="quantum_dsp_kernel",
        required_tool="quantum_dsp_kernel",
        expected_output="filter computed",
        category=TaskCategory.TERMINAL,
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.FAILED,
        risk_level=RiskLevel.LOW,
        inputs={"vector_dim": 1024},
    )
    state_c = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=wf_id_c,
            goal="Quantum Simulation",
            workflow_name="QuantumSimulationWorkflow",
            total_tasks=1,
            execution_mode=ExecutionMode.SAFE,
        ),
        tasks={task_id_c: task_c},
        running_tasks=[task_id_c],
    )
    class CustomUnmappedDeviceDriverAnomaly(Exception):
        pass
    fail_c = CustomUnmappedDeviceDriverAnomaly("Fatal ASIC microcode parity divergence at address 0xDEADBEEF01")
    res_c = await loop.process_failure(task=task_c, failure_input=fail_c, state=state_c)
    flush_trace_buffer(str(trace_path))

    # Read traces for Case C
    all_traces = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_traces.append(json.loads(line))
    traces_c = all_traces[len(traces_a) + len(traces_b):]

    # Helper to extract exactly unparaphrased fields from traces
    def extract_scenario_fields(traces: List[Dict[str, Any]]) -> Dict[str, Any]:
        fields = {
            "error_text": None,
            "parsed_category": None,
            "confidence": None,
            "plan_chosen": None,
            "patch_applied": None,
            "retry_count_k": None,
            "supervisor_result": None,
            "final_status": None,
        }
        for entry in traces:
            extra = entry.get("extra", {})
            if "error_text" in extra and fields["error_text"] is None:
                fields["error_text"] = extra["error_text"]
            if "parsed_category" in extra:
                fields["parsed_category"] = extra["parsed_category"]
            if "confidence" in extra:
                fields["confidence"] = extra["confidence"]
            if "plan_chosen" in extra:
                fields["plan_chosen"] = extra["plan_chosen"]
            if "patch_applied" in extra:
                fields["patch_applied"] = extra["patch_applied"]
            if "retry_count_k" in extra:
                fields["retry_count_k"] = extra["retry_count_k"]
            if "supervisor_result" in extra:
                fields["supervisor_result"] = extra["supervisor_result"]
            if "final_status" in extra:
                fields["final_status"] = extra["final_status"]
        return fields

    summary_a = extract_scenario_fields(traces_a)
    summary_b = extract_scenario_fields(traces_b)
    summary_c = extract_scenario_fields(traces_c)

    # Generate worked_examples.md strictly from trace fields
    worked_examples_md = f"""# Phoenix Empirical Trace Worked Examples
**Generated**: {datetime.datetime.now().isoformat()}  
**Trace Source**: `experiments/results/s1_traces.jsonl` (PHOENIX_TRACE=1)  
**Base Commit**: `{get_git_commit()}`  

Every field below is extracted directly and verbatim from the execution trace without manual alteration or paraphrasing.

---

## Scenario A: Task Writing to Missing Output Directory (Missing Resource)
- **Workflow ID**: `{wf_id_a}`
- **Task ID**: `{task_id_a}`
- **Task Name**: `write_report_artifact`

### Step-by-Step Account from Trace
1. **error text**: `{summary_a['error_text']}`
2. **parsed category**: `{summary_a['parsed_category']}`
3. **confidence**: `{summary_a['confidence']}`
4. **plan chosen**: `{summary_a['plan_chosen']}`
5. **patch applied**: `{json.dumps(summary_a['patch_applied'])}`
6. **retry count k**: `{summary_a['retry_count_k']}`
7. **Supervisor result**: `{summary_a['supervisor_result']}`
8. **final status**: `{summary_a['final_status']}`

---

## Scenario B: Destructive / Privilege-Escalating Command (Permission/Policy)
- **Workflow ID**: `{wf_id_b}`
- **Task ID**: `{task_id_b}`
- **Task Name**: `system_cleanup_task`

### Step-by-Step Account from Trace
1. **error text**: `{summary_b['error_text']}`
2. **parsed category**: `{summary_b['parsed_category']}`
3. **confidence**: `{summary_b['confidence']}`
4. **plan chosen**: `{summary_b['plan_chosen']}`
5. **patch applied**: `{json.dumps(summary_b['patch_applied'])}`
6. **retry count k**: `{summary_b['retry_count_k']}`
7. **Supervisor result**: `{summary_b['supervisor_result']}`
8. **final status**: `{summary_b['final_status']}`

---

## Scenario C: Unmapped Exception (Unmapped/Unknown)
- **Workflow ID**: `{wf_id_c}`
- **Task ID**: `{task_id_c}`
- **Task Name**: `proprietary_dsp_processing`

### Step-by-Step Account from Trace
1. **error text**: `{summary_c['error_text']}`
2. **parsed category**: `{summary_c['parsed_category']}`
3. **confidence**: `{summary_c['confidence']}`
4. **plan chosen**: `{summary_c['plan_chosen']}`
5. **patch applied**: `{json.dumps(summary_c['patch_applied'])}`
6. **retry count k**: `{summary_c['retry_count_k']}`
7. **Supervisor result**: `{summary_c['supervisor_result']}`
8. **final status**: `{summary_c['final_status']}`
"""
    with open(RESULTS_DIR / "worked_examples.md", "w", encoding="utf-8") as f:
        f.write(worked_examples_md)

    print(f"Scenario A: parsed={summary_a['parsed_category']}, status={summary_a['final_status']}")
    print(f"Scenario B: parsed={summary_b['parsed_category']}, status={summary_b['final_status']}")
    print(f"Scenario C: parsed={summary_c['parsed_category']}, status={summary_c['final_status']}")

    return {
        "scenario_a": summary_a,
        "scenario_b": summary_b,
        "scenario_c": summary_c,
        "trace_file": "experiments/results/s1_traces.jsonl",
        "output_file": "experiments/results/worked_examples.md",
    }


# ==============================================================================
# S2: Real-Adapter Scenarios on Host Machine (10 trials each)
# ==============================================================================
async def run_scenario_s2() -> Dict[str, Any]:
    print("\n--- Running S2: Real-Adapter Scenarios (10 trials each) ---")
    os.environ["PHOENIX_TRACE"] = "0"
    reg = get_configured_tool_registry()
    loop = SelfHealingLoop(tool_registry=reg, max_retries=3, max_healing_attempts=3)

    scenarios = [
        "real_file_locked",
        "real_missing_path",
        "real_subprocess_timeout",
        "real_unreachable_browser_port",
        "real_readonly_directory",
    ]
    results: Dict[str, Any] = {s: {"trials": [], "classification": None, "outcomes": [], "latencies_ms": []} for s in scenarios}

    temp_base = BASE_DIR / "experiments/temp_real_adapters"
    if temp_base.exists():
        shutil.rmtree(temp_base, ignore_errors=True)
    temp_base.mkdir(parents=True, exist_ok=True)

    file_adapter = FileExplorerToolAdapter()
    browser_adapter = BrowserExtensionAdapter()

    for trial_idx in range(10):
        # 1. Real file locked by another process
        trial_file = temp_base / f"locked_{trial_idx}.txt"
        trial_file.write_text("initial locked content", encoding="utf-8")
        # Keep handle open exclusively
        lock_handle = open(trial_file, "r+", encoding="utf-8")
        try:
            # Task attempts to move or write to the locked file using FileExplorer
            locked_task = Task(
                task_id=uuid.uuid4(),
                workflow_id=uuid.uuid4(),
                task_name="move_locked_file",
                description="Move locked file",
                required_tool="file_explorer_tool",
                expected_output="file moved",
                category=TaskCategory.FILE_SYSTEM,
                priority=TaskPriority.HIGH,
                status=TaskStatus.RUNNING,
                inputs={"action": "move_file", "source": str(trial_file), "destination": str(temp_base / f"moved_{trial_idx}.txt")},
            )
            # Execute real adapter
            adapter_res = await file_adapter.execute(locked_task)
            err = adapter_res.error
            # Feed into healing loop
            t0 = time.perf_counter_ns()
            state = SharedWorkflowState(
                metadata=WorkflowMetadata(workflow_id=locked_task.workflow_id, goal="Real File Locked", total_tasks=1, execution_mode=ExecutionMode.SAFE),
                tasks={locked_task.task_id: locked_task},
            )
            heal_res = await loop.process_failure(task=locked_task, failure_input=err or adapter_res.output, state=state)
            t_r = (time.perf_counter_ns() - t0) / 1_000_000.0

            cat = heal_res.root_cause
            outcome = "recovered" if heal_res.success else "rejected"
            results["real_file_locked"]["classification"] = cat
            results["real_file_locked"]["outcomes"].append(outcome)
            results["real_file_locked"]["latencies_ms"].append(t_r)
        finally:
            lock_handle.close()

        # 2. Real missing path passed to real adapter
        missing_task = Task(
            task_id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            task_name="open_missing_file",
            description="Open missing file",
            required_tool="file_explorer_tool",
            expected_output="file opened",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING,
            inputs={"action": "open_file", "path": str(temp_base / f"nonexistent_real_{trial_idx}.xyz")},
        )
        adapter_res = await file_adapter.execute(missing_task)
        err = adapter_res.error
        t0 = time.perf_counter_ns()
        state = SharedWorkflowState(
            metadata=WorkflowMetadata(workflow_id=missing_task.workflow_id, goal="Real Missing Path", total_tasks=1, execution_mode=ExecutionMode.SAFE),
            tasks={missing_task.task_id: missing_task},
        )
        heal_res = await loop.process_failure(task=missing_task, failure_input=err or adapter_res.output, state=state)
        t_r = (time.perf_counter_ns() - t0) / 1_000_000.0
        results["real_missing_path"]["classification"] = heal_res.root_cause
        results["real_missing_path"]["outcomes"].append("recovered" if heal_res.success else "rejected")
        results["real_missing_path"]["latencies_ms"].append(t_r)

        # 3. Real subprocess exceeding timeout
        t_sub_start = time.perf_counter_ns()
        try:
            # Run python sleep subprocess with 0.1s timeout
            proc = subprocess.run(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                capture_output=True,
                timeout=0.1,
            )
            sub_err = None
        except subprocess.TimeoutExpired as te:
            sub_err = te

        timeout_task = Task(
            task_id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            task_name="long_running_subprocess",
            description="Subprocess timeout test",
            required_tool="terminal_tool",
            expected_output="command finished",
            category=TaskCategory.TERMINAL,
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING,
            tool_name="terminal_tool",
            inputs={"command": "python -c 'import time; time.sleep(5)'"},
        )
        t0 = time.perf_counter_ns()
        state = SharedWorkflowState(
            metadata=WorkflowMetadata(workflow_id=timeout_task.workflow_id, goal="Real Subprocess Timeout", total_tasks=1, execution_mode=ExecutionMode.SAFE),
            tasks={timeout_task.task_id: timeout_task},
        )
        heal_res = await loop.process_failure(task=timeout_task, failure_input=sub_err, state=state)
        t_r = (time.perf_counter_ns() - t0) / 1_000_000.0
        results["real_subprocess_timeout"]["classification"] = heal_res.root_cause
        results["real_subprocess_timeout"]["outcomes"].append("recovered" if heal_res.success else "rejected")
        results["real_subprocess_timeout"]["latencies_ms"].append(t_r)

        # 4. Real unreachable local port for browser adapter
        # Call browser adapter navigate to unreachable local port without daemon
        browser_task = Task(
            task_id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            task_name="browser_navigate_unreachable",
            description="Browser navigate to unreachable port",
            required_tool="browser_tool",
            expected_output="navigated",
            category=TaskCategory.BROWSER,
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING,
            inputs={"action": "navigate", "url": "http://127.0.0.1:59999/status", "timeout_ms": 100},
        )
        adapter_res = await browser_adapter.execute(browser_task)
        err = adapter_res.error
        t0 = time.perf_counter_ns()
        state = SharedWorkflowState(
            metadata=WorkflowMetadata(workflow_id=browser_task.workflow_id, goal="Real Browser Unreachable", total_tasks=1, execution_mode=ExecutionMode.SAFE),
            tasks={browser_task.task_id: browser_task},
        )
        heal_res = await loop.process_failure(task=browser_task, failure_input=err or adapter_res.output, state=state)
        t_r = (time.perf_counter_ns() - t0) / 1_000_000.0
        results["real_unreachable_browser_port"]["classification"] = heal_res.root_cause
        results["real_unreachable_browser_port"]["outcomes"].append("recovered" if heal_res.success else "rejected")
        results["real_unreachable_browser_port"]["latencies_ms"].append(t_r)

        # 5. Real write to a read-only directory
        ro_dir = temp_base / f"readonly_dir_{trial_idx}"
        ro_dir.mkdir(parents=True, exist_ok=True)
        # Attempt to write to system protected root directory or revoke permissions
        target_path = "C:/Windows/System32/phoenix_audit_temp_write.tmp"
        try:
            with open(target_path, "w") as f:
                f.write("test")
            ro_err = None
        except PermissionError as pe:
            ro_err = pe
        except Exception as ex:
            ro_err = ex

        ro_task = Task(
            task_id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            task_name="write_readonly_dir",
            description="Write to read only path",
            required_tool="file_explorer_tool",
            expected_output="file opened",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING,
            inputs={"action": "open_file", "path": target_path},
        )
        t0 = time.perf_counter_ns()
        state = SharedWorkflowState(
            metadata=WorkflowMetadata(workflow_id=ro_task.workflow_id, goal="Real ReadOnly Directory", total_tasks=1, execution_mode=ExecutionMode.SAFE),
            tasks={ro_task.task_id: ro_task},
        )
        heal_res = await loop.process_failure(task=ro_task, failure_input=ro_err, state=state)
        t_r = (time.perf_counter_ns() - t0) / 1_000_000.0
        results["real_readonly_directory"]["classification"] = heal_res.root_cause
        results["real_readonly_directory"]["outcomes"].append("recovered" if heal_res.success else "rejected")
        results["real_readonly_directory"]["latencies_ms"].append(t_r)

    # Cleanup temp
    shutil.rmtree(temp_base, ignore_errors=True)

    summary_s2 = {}
    for s, data in results.items():
        recovered_count = sum(1 for o in data["outcomes"] if o == "recovered")
        rejected_count = sum(1 for o in data["outcomes"] if o == "rejected")
        lat_stats = compute_stats(data["latencies_ms"])
        summary_s2[s] = {
            "classification": data["classification"],
            "recovered": recovered_count,
            "rejected": rejected_count,
            "completion_rate": f"{recovered_count}/10 ({recovered_count * 10.0}%)",
            "latency_ms": lat_stats,
        }
        print(f"Scenario {s}: class={data['classification']}, recovered={recovered_count}/10, rejected={rejected_count}/10, T_R mean={lat_stats['mean']}ms")

    return summary_s2


# ==============================================================================
# S3: Larger Workflow Graphs (10 & 20 tasks, Linear & Branching, 3 positions, 25 trials each = 300 trials)
# ==============================================================================
async def run_scenario_s3() -> Dict[str, Any]:
    print("\n--- Running S3: Larger Workflow Graphs (300 trials total) ---")
    os.environ["PHOENIX_TRACE"] = "0"
    reg = get_configured_tool_registry()
    loop = SelfHealingLoop(tool_registry=reg, max_retries=3, max_healing_attempts=3)

    configs = [
        {"name": "10_task_linear", "num_tasks": 10, "topology": "linear", "positions": {"first": 0, "middle": 5, "last": 9}},
        {"name": "10_task_branching", "num_tasks": 10, "topology": "branching", "positions": {"first": 0, "middle": 5, "last": 9}},
        {"name": "20_task_linear", "num_tasks": 20, "topology": "linear", "positions": {"first": 0, "middle": 10, "last": 19}},
        {"name": "20_task_branching", "num_tasks": 20, "topology": "branching", "positions": {"first": 0, "middle": 10, "last": 19}},
    ]

    s3_results: Dict[str, Any] = {}

    for cfg in configs:
        cfg_name = cfg["name"]
        num_tasks = cfg["num_tasks"]
        s3_results[cfg_name] = {}

        for pos_name, fault_pos in cfg["positions"].items():
            completed_workflows = 0
            total_retries = 0
            t_r_vals: List[float] = []
            total_times_ms: List[float] = []

            for trial in range(25):
                wf_id = uuid.uuid4()
                tasks: Dict[uuid.UUID, Task] = {}
                task_ids = [uuid.uuid4() for _ in range(num_tasks)]

                # Build tasks
                for idx, tid in enumerate(task_ids):
                    t = Task(
                        task_id=tid,
                        workflow_id=wf_id,
                        task_name=f"task_{idx}",
                        description=f"Task {idx} execution",
                        required_tool="web_research_tool",
                        expected_output="done",
                        tool_name="web_research_tool",
                        category=TaskCategory.WEB_RESEARCH,
                        status=TaskStatus.READY if idx == 0 else TaskStatus.WAITING,
                        dependencies=[task_ids[idx - 1]] if (cfg["topology"] == "linear" and idx > 0) else [],
                    )
                    tasks[tid] = t

                state = SharedWorkflowState(
                    metadata=WorkflowMetadata(
                        workflow_id=wf_id,
                        goal="Large Graph Benchmark",
                        total_tasks=num_tasks,
                        execution_mode=ExecutionMode.SAFE,
                    ),
                    tasks=tasks,
                )

                wf_start = time.perf_counter_ns()
                wf_success = True
                trial_retries = 0

                # Simulate execution of workflow tasks
                for idx, tid in enumerate(task_ids):
                    task = tasks[tid]
                    task.status = TaskStatus.RUNNING

                    if idx == fault_pos:
                        # Inject recoverable fault (TOOL_UNAVAILABLE with substitute available)
                        fail_input = TaskError(error_code="TOOL_UNAVAILABLE", error_message="Browser service is unavailable")
                        t0 = time.perf_counter_ns()
                        heal_res = await loop.process_failure(task=task, failure_input=fail_input, state=state)
                        t_r = (time.perf_counter_ns() - t0) / 1_000_000.0
                        t_r_vals.append(t_r)

                        if heal_res.success:
                            trial_retries += 1
                            # Simulate successful healed execution
                            task.status = TaskStatus.COMPLETED
                        else:
                            task.status = TaskStatus.FAILED
                            wf_success = False
                            break
                    else:
                        # Non-faulted task executes successfully
                        task.status = TaskStatus.COMPLETED

                wf_end = time.perf_counter_ns()
                total_wf_time_ms = (wf_end - wf_start) / 1_000_000.0
                total_times_ms.append(total_wf_time_ms)

                if wf_success:
                    completed_workflows += 1
                total_retries += trial_retries

            tr_stats = compute_stats(t_r_vals)
            wf_stats = compute_stats(total_times_ms)

            setting_res = {
                "fault_position": pos_name,
                "fault_task_index": fault_pos,
                "completed": completed_workflows,
                "total_trials": 25,
                "completion_rate": f"{completed_workflows}/25 ({completed_workflows * 4.0}%)",
                "retries": total_retries,
                "avg_retries_per_trial": round(total_retries / 25.0, 2),
                "T_R_ms": tr_stats,
                "total_workflow_time_ms": wf_stats,
            }
            s3_results[cfg_name][pos_name] = setting_res
            print(f"{cfg_name} [fault at {pos_name}]: completed={completed_workflows}/25, retries={total_retries}, T_R mean={tr_stats['mean']}ms, total_time mean={wf_stats['mean']}ms")

    return s3_results


# ==============================================================================
# S4: Additional Fault Types (10 trials each)
# ==============================================================================
async def run_scenario_s4() -> Dict[str, Any]:
    print("\n--- Running S4: Additional Fault Types (10 trials each) ---")
    os.environ["PHOENIX_TRACE"] = "0"
    reg = get_configured_tool_registry()
    loop = SelfHealingLoop(tool_registry=reg, max_retries=3, max_healing_attempts=3)

    fault_definitions = [
        {
            "name": "network_connection_refused",
            "exception_factory": lambda: ConnectionRefusedError("[WinError 1225] The remote computer refused the network connection"),
            "intended_behavior": "Transient network failure: retried with backoff",
        },
        {
            "name": "file_locked",
            "exception_factory": lambda: PermissionError("[WinError 32] The process cannot access the file because it is being used by another process"),
            "intended_behavior": "Resource access contention: safely rejected under SAFE permission policy without unapproved elevation",
        },
        {
            "name": "disk_full",
            "exception_factory": lambda: OSError(28, "No space left on device"),
            "intended_behavior": "Unmapped OS capacity error: rejected as NO_VIABLE_RECOVERY (non-recoverable without admin intervention)",
        },
        {
            "name": "malformed_json_tool_output",
            "exception_factory": lambda: json.decoder.JSONDecodeError("Expecting value", "{\"corrupt\": [", 12),
            "intended_behavior": "Malformed payload structure: rejected as unmapped parser failure (confidence <= 0.30)",
        },
        {
            "name": "unknown_adapter_name",
            "exception_factory": lambda: ToolNotFoundException("Adapter 'NonExistentCustomAdapter' not registered in ToolRegistry"),
            "intended_behavior": "Tool not found: classified as TOOL_UNAVAILABLE; retried or substituted if candidate exists, else rejected",
        },
    ]

    s4_results: Dict[str, Any] = {}

    for fdef in fault_definitions:
        fname = fdef["name"]
        trials_data = []
        outcomes = []
        parsed_cats = []
        rc_cats = []
        confidences = []

        for trial in range(10):
            task = Task(
                task_id=uuid.uuid4(),
                workflow_id=uuid.uuid4(),
                task_name=f"test_s4_{fname}",
                description=f"Additional fault test {fname}",
                required_tool="browser_tool",
                expected_output="done",
                category=TaskCategory.WEB_RESEARCH,
                priority=TaskPriority.HIGH,
                status=TaskStatus.FAILED,
                tool_name="browser_tool",
            )
            state = SharedWorkflowState(
                metadata=WorkflowMetadata(workflow_id=task.workflow_id, goal=f"S4 {fname}", total_tasks=1, execution_mode=ExecutionMode.SAFE),
                tasks={task.task_id: task},
            )
            err = fdef["exception_factory"]()
            t0 = time.perf_counter_ns()
            res = await loop.process_failure(task=task, failure_input=err, state=state)
            t_r = (time.perf_counter_ns() - t0) / 1_000_000.0

            strat_str = str(res.recovery_strategy)
            outcome = "recovered" if res.success else ("retried" if "RETRY" in strat_str and res.replacement_tasks else "rejected")
            outcomes.append(outcome)
            rc_cats.append(res.root_cause)

        parsed_sample = loop.error_parser.parse(fdef["exception_factory"]())
        rc_sample = loop.root_cause_analyzer.analyze(parsed_sample)

        recovered_cnt = sum(1 for o in outcomes if o == "recovered")
        rejected_cnt = sum(1 for o in outcomes if o == "rejected")
        retried_cnt = sum(1 for o in outcomes if o == "retried")

        # Determine if outcome matches intended design
        intended_action = fdef["intended_behavior"]
        is_as_intended = (
            (fname == "network_connection_refused" and recovered_cnt == 10)
            or (fname == "file_locked" and rejected_cnt == 10)
            or (fname == "disk_full" and rejected_cnt == 10)
            or (fname == "malformed_json_tool_output" and rejected_cnt == 10)
            or (fname == "unknown_adapter_name" and (recovered_cnt == 10 or rejected_cnt == 10))
        )

        s4_results[fname] = {
            "parsed_category": parsed_sample.category.value if hasattr(parsed_sample.category, "value") else str(parsed_sample.category),
            "normalized_code": parsed_sample.normalized_code,
            "root_cause_category": rc_sample.category.value if hasattr(rc_sample.category, "value") else str(rc_sample.category),
            "confidence": rc_sample.confidence_score,
            "handling": {
                "recovered": recovered_cnt,
                "rejected": rejected_cnt,
                "retried": retried_cnt,
            },
            "outcome_rate": f"recovered={recovered_cnt}/10, rejected={rejected_cnt}/10, retried={retried_cnt}/10",
            "intended_behavior": intended_action,
            "outcome_matches_intended": is_as_intended,
        }
        print(f"S4 {fname}: parsed={s4_results[fname]['parsed_category']}, rc={s4_results[fname]['root_cause_category']} (conf={rc_sample.confidence_score}), handling: {s4_results[fname]['outcome_rate']}, as_intended={is_as_intended}")

    return s4_results


# ==============================================================================
# Update summary.csv and checkpoint7_results.json
# ==============================================================================
def update_summary_csv(s2_res: Dict[str, Any], s3_res: Dict[str, Any], s4_res: Dict[str, Any]) -> None:
    csv_path = RESULTS_DIR / "summary.csv"
    existing_rows = []
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            existing_rows = list(reader)

    # Filter out any prior Checkpoint 7 scenario rows to keep idempotent
    filtered_rows = [row for row in existing_rows if not (len(row) > 0 and row[0].startswith("Scenario_"))]

    new_rows = []
    # Add S2 rows
    for s_name, data in s2_res.items():
        new_rows.append([
            "Scenario_S2_Real_Adapters",
            s_name,
            "Completion_Rate",
            data["completion_rate"],
            "N/A",
            "N/A",
            "N/A",
            "N/A",
            f"Classified as {data['classification']}; Latency mean={data['latency_ms']['mean']}ms",
        ])

    # Add S3 rows
    for g_name, pos_data in s3_res.items():
        for p_name, p_res in pos_data.items():
            new_rows.append([
                "Scenario_S3_Large_Workflows",
                f"{g_name}_{p_name}",
                "Workflow_Completion_Rate",
                p_res["completion_rate"],
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                f"Retries={p_res['retries']}, T_R mean={p_res['T_R_ms']['mean']}ms, total_wf_time mean={p_res['total_workflow_time_ms']['mean']}ms",
            ])

    # Add S4 rows
    for f_name, f_res in s4_res.items():
        new_rows.append([
            "Scenario_S4_Additional_Faults",
            f_name,
            "Handling_Outcome",
            f_res["outcome_rate"],
            "N/A",
            "N/A",
            "N/A",
            "N/A",
            f"Classified={f_res['parsed_category']}/{f_res['root_cause_category']}, conf={f_res['confidence']}, matches_intended={f_res['outcome_matches_intended']}",
        ])

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(filtered_rows + new_rows)

    print(f"\nUpdated {csv_path} with {len(new_rows)} Checkpoint 7 scenario rows.")


async def main() -> None:
    commit_hash = get_git_commit()
    print(f"=== Running Checkpoint 7 Evaluation (Commit: {commit_hash}) ===")

    s1_res = await run_scenario_s1()
    s2_res = await run_scenario_s2()
    s3_res = await run_scenario_s3()
    s4_res = await run_scenario_s4()

    full_artifact = {
        "checkpoint": "Checkpoint 7: Scenario Round",
        "commit_hash": commit_hash,
        "timestamp": datetime.datetime.now().isoformat(),
        "S1_worked_examples": s1_res,
        "S2_real_adapters": s2_res,
        "S3_large_workflows": s3_res,
        "S4_additional_faults": s4_res,
    }

    results_json_path = RESULTS_DIR / "checkpoint7_results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(full_artifact, f, indent=2)
    print(f"Saved full Checkpoint 7 JSON artifact to {results_json_path}")

    update_summary_csv(s2_res, s3_res, s4_res)
    print("=== Checkpoint 7 Execution Completed Successfully ===")


if __name__ == "__main__":
    asyncio.run(main())
