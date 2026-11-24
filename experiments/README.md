# Phoenix Agents: Empirical Reviewer Benchmark Suite

This directory contains the experimental framework, benchmark scripts, raw empirical traces, and aggregated results addressing the reviewer comments for **Phoenix Agents** (*Phoenix: Deterministic Self-Healing and Fault Tolerance for Autonomous Desktop Automation*).

## 1. Environment Metadata

Every trial was executed on the host system without mock simulation shortcuts:
- **Date & Time (UTC):** 2026-11-21
- **Git Commit Hash:** `4906e16c7eca333685c56b888d254f87372054f4`
- **Operating System:** Windows 11 Enterprise (Build 10.0.26300)
- **Processor:** AMD Ryzen 7 8845HS with Radeon 780M Graphics (8 Physical Cores, 16 Logical Threads)
- **RAM:** 15.26 GB Physical Memory
- **Python Runtime:** Python 3.14.4 (`backend/.venv`)
- **Installed Packages:** 68 packages (documented in raw output)

---

## 2. Benchmark Suite Architecture & Methodology

All experimental code is located exclusively in `/experiments`:
- `run_benchmarks.py`: The unified benchmark orchestrator.
- `results/summary.csv`: Aggregated headline metrics with Wilson 95% score intervals.
- `results/raw/`: Full timestamped JSON traces for every trial.

### Experiments Overview:
1. **Part A: 125-Fault Benchmark across Baselines**
   - 5 real classes $\times$ 25 trials = 125 faults:
     1. `TIMEOUT` (Runtime, transient)
     2. `MISSING_RESOURCE` (Infrastructure, missing path)
     3. `TOOL_FAILURE` (Tool, syntax error / adapter crash)
     4. `PERMISSION_DENIED` (Security policy violation, destructive command)
     5. `UNKNOWN_EXCEPTION` (Unmapped exception, low confidence)
   - Evaluated across:
     - `fail_fast` ($K=0$, no recovery)
     - `naive_retry` ($K_{\max}=3$, blind re-dispatch)
     - `phoenix` (Full 5-stage deterministic healing loop)
   - *LLM Replanner Baseline Note:* Skipped because no API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`) were configured in the local environment. Documented in `QUESTIONS.md`.

2. **Part B: 50 Held-Out Faults**
   - Written *before* execution across 3 groups:
     - Group 1: Out-of-taxonomy recoverable (17 trials)
     - Group 2: Obfuscated unsafe actions (17 trials)
     - Group 3: Ambiguous / low-context error messages (16 trials)
   - Measures diagnosis accuracy, confusion matrix, false positives (unsafe actions permitted), and false negatives.

3. **Part C: Repeatability ($R=30$ Runs)**
   - 30 repeated runs with fixed seed (42) and 30 repeated runs with varying seeds ($1..30$).
   - Evaluates run-to-run outcome determinism and isolated recovery latency ($T_R$) distribution (Mean, SD, Median, IQR, Min, Max).

4. **Part D: Concurrency Determinism (10 Workflows, $R=30$)**
   - Concurrently executes the 125-fault suite across 10 parallel asynchronous workflows.
   - Evaluates outcome consistency and audits shared state variables (`SelfHealingLoop.current_state` and `RetryEngine._failure_signature_counts`).

5. **Part E: Adversarial Unsafe Faults Injected into Recoverable Rules ($n=25$)**
   - Injects destructive commands masked with benign `"TIMEOUT"` error messages.
   - Audits whether `PermissionManager` and `SafeExecutionPolicy` re-evaluate task parameters before retrying.

6. **Part F: Real-Adapter Scenarios on Host Machine ($n=10$ each)**
   - 50 real OS scenarios without mocks:
     1. Real file lock (`msvcrt.locking` on Windows)
     2. Real missing file path (`FileNotFoundError`)
     3. Real subprocess deadline timeout (`subprocess.TimeoutExpired`)
     4. Real unreachable network port (`ConnectionRefusedError` on `127.0.0.1:59999`)
     5. Real read-only directory attribute write (`PermissionError`)

---

## 3. Results Summary Table (`results/summary.csv`)

| Experiment | Configuration | Metric | Value | 95% Wilson CI | Sample Size ($n$) | Raw Data File |
|---|---|---|---|---|---|---|
| **125 Faults** | `fail_fast` | Overall Success Rate | 0.00% | [0.00%, 2.98%] | 125 | `part_a_baselines.json` |
| **125 Faults** | `fail_fast` | Recoverable Success Rate | 0.00% | [0.00%, 4.87%] | 75 | `part_a_baselines.json` |
| **125 Faults** | `fail_fast` | Unsafe Rejection Rate | 100.00% | [92.87%, 100.00%] | 50 | `part_a_baselines.json` |
| **125 Faults** | `fail_fast` | Lifecycle $T_{\text{no\_rec}}$ (Mean) | 0.0015 ms | [0.0006, 0.0468 ms] | 125 | `part_a_baselines.json` |
| **125 Faults** | `naive_retry` | Overall Success Rate | 20.00% | [13.93%, 27.86%] | 125 | `part_a_baselines.json` |
| **125 Faults** | `naive_retry` | Recoverable Success Rate | 33.33% | [23.71%, 44.58%] | 75 | `part_a_baselines.json` |
| **125 Faults** | `naive_retry` | Unsafe Rejection Rate | 50.00% | [36.64%, 63.36%] | 50 | `part_a_baselines.json` |
| **125 Faults** | `phoenix` | Overall Success Rate | 40.00% | [31.83%, 48.76%] | 125 | `part_a_baselines.json` |
| **125 Faults** | `phoenix` | Recoverable Success Rate | 66.67% | [55.42%, 76.29%] | 75 | `part_a_baselines.json` |
| **125 Faults** | `phoenix` | Unsafe Rejection Rate | 100.00% | [92.87%, 100.00%] | 50 | `part_a_baselines.json` |
| **125 Faults** | `phoenix` | Recovery Latency $T_R$ (Mean) | 1.9184 ms | [1.1063, 3.0231 ms] | 75 | `part_a_baselines.json` |
| **125 Faults** | `phoenix` | Lifecycle $T_{\text{rec}}$ (Mean) | 1.9219 ms | [1.1085, 3.0286 ms] | 75 | `part_a_baselines.json` |
| **Held-Out** | `phoenix` | Recoverable Success Rate | 100.00% | [81.57%, 100.00%] | 17 | `part_b_heldout.json` |
| **Held-Out** | `phoenix` | Unsafe Rejection Rate | 100.00% | [81.57%, 100.00%] | 17 | `part_b_heldout.json` |
| **Held-Out** | `phoenix` | False Positives (Unsafe Allowed) | 0 | [0, 0] | 17 | `part_b_heldout.json` |
| **Repeatability** | `phoenix_fixed` | Outcome Determinism Rate | 100.00% | [100.0%, 100.0%] | 30 | `part_c_repeatability.json` |
| **Repeatability** | `phoenix_varying`| Outcome Determinism Rate | 100.00% | [100.0%, 100.0%] | 30 | `part_c_repeatability.json` |
| **Repeatability** | `phoenix_fixed` | $T_R$ Latency (Mean) | 5.3346 ms | [0.7880, 57.2286 ms] | 2250 | `part_c_repeatability.json` |
| **Concurrency** | `phoenix_concurrent`| Outcome Matching Rate | 100.00% | [88.65%, 100.00%] | 30 | `part_d_concurrency.json` |
| **Adversarial** | `phoenix` | Safe Rejection Rate | 52.00% | [33.50%, 69.97%] | 25 | `part_e_adversarial.json` |
| **Adversarial** | `phoenix` | Unsafe Executions Allowed | 12 | [0, 0] | 25 | `part_e_adversarial.json` |
| **Real Adapter** | `file_lock` | Recovery Rate | 0.00% | [0.00%, 27.75%] | 10 | `part_f_real_adapters.json` |
| **Real Adapter** | `file_lock` | Latency (Mean) | 2.4279 ms | [1.6285, 3.9981 ms] | 10 | `part_f_real_adapters.json` |
| **Real Adapter** | `missing_path` | Recovery Rate | 0.00% | [0.00%, 27.75%] | 10 | `part_f_real_adapters.json` |
| **Real Adapter** | `missing_path` | Latency (Mean) | 2.6347 ms | [1.8197, 3.1894 ms] | 10 | `part_f_real_adapters.json` |
| **Real Adapter** | `subprocess_timeout`| Recovery Rate | 100.00% | [72.25%, 100.00%] | 10 | `part_f_real_adapters.json` |
| **Real Adapter** | `subprocess_timeout`| Latency (Mean) | 5.4649 ms | [3.0882, 20.7393 ms]| 10 | `part_f_real_adapters.json` |
| **Real Adapter** | `unreachable_port`| Recovery Rate | 100.00% | [72.25%, 100.00%] | 10 | `part_f_real_adapters.json` |
| **Real Adapter** | `unreachable_port`| Latency (Mean) | 2.6892 ms | [2.1554, 3.1484 ms] | 10 | `part_f_real_adapters.json` |
| **Real Adapter** | `readonly_dir_write`| Recovery Rate | 100.00% | [72.25%, 100.00%] | 10 | `part_f_real_adapters.json` |
| **Real Adapter** | `readonly_dir_write`| Latency (Mean) | 2.1482 ms | [1.6255, 2.7179 ms] | 10 | `part_f_real_adapters.json` |
