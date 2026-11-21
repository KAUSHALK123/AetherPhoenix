# Upgrade Notes: Targeted Architectural & Benchmarking Upgrades (U0 - U7)

This document records the small set of targeted architectural upgrades made to repository branch `experiments/reviewer-benchmarks` before empirical paper evaluation.

---

## 1. Upgrade Summary Table

| ID | Title | Commit Hash | Touched Files | Dedicated Unit Tests |
|---|---|---|---|---|
| **U0** | Baseline Test Suite Log & Tag | `ab808d8` | `experiments/baseline_test_suite_pre_upgrade.log` | Full pytest suite run (1032 passed, 21 failed) |
| **U1** | `SelfHealingLoop.current_state` Per-Task State Isolation | `1e382e3` | `backend/app/agents/healing/self_healing_loop.py`, `backend/tests/agents/healing/test_self_healing_loop.py` | `test_concurrent_per_task_state_isolation` |
| **U2** | `RetryEngine._failure_signature_counts` Concurrency Safety | `0966707` | `backend/app/agents/healing/retry_engine.py`, `backend/tests/agents/healing/test_retry_engine.py` | `test_concurrent_failure_signature_counts_concurrency` |
| **U3** | Nanosecond JSONL Tracing & Stage Latency Profiler | `93ac029` | `backend/app/core/tracing.py`, `backend/app/engine/orchestrator.py`, `backend/app/agents/healing/self_healing_loop.py`, `backend/tests/core/test_tracing.py`, `experiments/compute_trace_latencies.py` | `test_tracing_disabled_by_default`, `test_tracing_records_all_required_fields`, `test_self_healing_loop_tracing_integration` |
| **U4** | Dual-Mode Fault Injection Harness (`synthetic` vs `real_exception`) | `be19903` | `experiments/fault_injection.py`, `backend/tests/core/test_fault_injection.py` | `test_fault_injector_synthetic_mode`, `test_fault_injector_real_exception_mode`, `test_fault_injector_invalid_mode` |
| **U5** | Parameterized Multi-Seed Repeats Runner & LaTeX Table Generator | `8288358` | `experiments/run_all.py`, `experiments/generate_paper_tables.py` | Validated via `run_all.py` and `generate_paper_tables.py` |
| **U6** | Deprecation Notice on `tools/generate_papers.py` | `e94959e` | `tools/generate_papers.py` | Code inspection & docstring notice verification |
| **U7** | Locked Dependencies & Environment Documentation | `45ed449` | `requirements-lock.txt` | Pip freeze dependency lock with Python 3.14.4 header |

---

## 2. Detailed Changes

### U0: Baseline Test Suite Execution
- **Issue:** Needed an exact baseline log of existing test passes/failures before touching code.
- **Action:** Ran full test suite with `pytest -v --tb=short`.
- **Result:** 1032 passed, 21 failed (integration tests requiring external desktop services), 0 skipped out of 1053 total.
- **Artifact:** Tagged `pre-upgrade` at commit `ab808d8`.

### U1: SelfHealingLoop Per-Task State Isolation
- **Issue:** `SelfHealingLoop.current_state` was a shared singleton attribute on the agent instance. In concurrent workflow failure scenarios, concurrent tasks overwrote each other's lifecycle state.
- **Action:**
  - Added `self._task_states: Dict[Tuple[UUID, UUID], HealingState] = {}`.
  - Maintained public API compatibility via property getter/setter `current_state` delegating to `_default_state`.
  - Added `get_task_state(workflow_id, task_id)` and `_set_task_state(workflow_id, task_id, state)`.
  - Updated all recovery transitions in `process_failure()` to record per-task state.
- **Test:** Added `test_concurrent_per_task_state_isolation` verifying independent state transitions across parallel tasks.

### U2: RetryEngine Failure Signature Counts Concurrency Safety
- **Issue:** `RetryEngine._failure_signature_counts` was shared, unkeyed by workflow, and unlocked during read-modify-write.
- **Action:**
  - Keyed signature counts by `(workflow_id, task_id, signature)`.
  - Added `record_failure_signature(workflow_id, task_id, signature)` and `get_failure_signature_count()` with atomic read-modify-write without intervening `await`.
  - Updated `can_retry()` and `execute_recovery()` to prevent cross-workflow signature collisions.
- **Test:** Added `test_concurrent_failure_signature_counts_concurrency` confirming 100 concurrent identical failures yield identical counts as sequential processing.

### U3: Nanosecond JSONL Tracing ($T_R$, $T_{\text{rec}}$, $T_{\text{no\_rec}}$)
- **Issue:** Reviewers required microsecond/nanosecond breakdown of recovery stages without mocking or guesswork.
- **Action:**
  - Added opt-in nanosecond tracing via `PHOENIX_TRACE=1` writing to JSONL.
  - Implemented event recording at: task dispatch, failure detected, start and end of each of the 5 healing stages (Error Parsing, Root Cause Analysis, Strategy Selection, Plan Validation, Recovery Execution), re-enqueue, and task completion.
  - Implemented `experiments/compute_trace_latencies.py` computing $T_R$, $T_{\text{rec}}$, $T_{\text{no\_rec}}$, and $\Delta T_{\text{overhead}}$.
- **Test:** Added `backend/tests/core/test_tracing.py` testing opt-in behavior, required field serialization, and full `SelfHealingLoop` stage recording integration.

### U4: Dual-Mode Fault Injection Harness
- **Issue:** Needed empirical proof that self-healing handles both synthetic error objects and real OS/runtime exceptions.
- **Action:**
  - Created `experiments/fault_injection.py` supporting `mode="synthetic"` and `mode="real_exception"`.
  - Real exception mode generates actual `asyncio.wait_for` timeouts, `FileNotFoundError`, non-zero subprocess returns (`subprocess.CalledProcessError`), `PermissionError` on read-only temporary files, and unmapped custom exceptions (`UnmappedCustomException`).
  - Records the mode in every output result file.
- **Test:** Added `backend/tests/core/test_fault_injection.py` testing both modes across all 5 fault categories.

### U5: Parameterized Multi-Seed Repeats Runner & LaTeX Table Generator
- **Issue:** Paper evaluation required statistical confidence intervals across multiple random seeds without manual transcription.
- **Action:**
  - Created `experiments/run_all.py` supporting `--repeats R`, `--seed-base S`, `--mode`, and `--output-dir`.
  - Logs seed, git commit, OS, CPU, RAM, Python version, and package count to all outputs.
  - Created `experiments/generate_paper_tables.py` extracting all numbers directly from raw JSON files into LaTeX tables and `paper_numbers.json` (zero hand-typed numbers).

### U6: Deprecation Notice on `tools/generate_papers.py`
- **Issue:** Audit revealed `tools/generate_papers.py` contained hard-coded, unmeasured paper constants (e.g. lines 440-500: 1.30, 1.88, 0.44, 75/75, 50/50, 60%, 12.18, 14.85, 124.50).
- **Action:** Added a prominent header deprecation notice warning that the file contains synthetic unmeasured constants and must not be used for empirical paper generation.

### U7: Requirements Lock & Environment Specification
- **Issue:** Reviewers required frozen runtime dependencies for camera-ready reproducibility.
- **Action:** Generated `requirements-lock.txt` using `pip freeze` and documented Python version 3.14.4 on Windows AMD64.

---

## 3. Audit Findings: Bugs Found but NOT Fixed (Preserved per Scope Rules)

Per the strict scope rules ("Do NOT change any classification rule, regex, confidence threshold, $K_{\max}$, risk level, or permission policy... If you find a bug in classification or permissions, report it in UPGRADE_NOTES.md; do not fix it"), the following bugs are documented here for Phase 2:

1. **RootCauseAnalyzer False Positive on Non-Existent Path Tokens:**
   - **Location:** `backend/app/agents/healing/root_cause_analyzer.py` line ~285 (`_inspect_filesystem_and_paths`).
   - **Bug:** When extracting tokens from command-line strings (e.g. `rmdir /s /q C:\Windows\System32\batch_1`), if the directory does not exist on disk, the analyzer classifies the error as `OUTPUT_DIRECTORY_MISSING` (`INFRASTRUCTURE`, score 0.95), which preempts `PERMISSION_DENIED` regex checks.
   - **Impact:** An unsafe permission-denied command could be misclassified as a recoverable infrastructure missing-directory error.

2. **RecoveryPlanner Confidence Boundary Strict Less-Than (`< 0.3`):**
   - **Location:** `backend/app/agents/healing/recovery_planner.py` line ~60.
   - **Bug:** The code checks `if root_cause.confidence_score < 0.3`. When `RootCauseAnalyzer` returns `confidence_score = 0.30` on unmapped/unknown errors, the condition `< 0.3` evaluates to `False`.
   - **Impact:** Instead of falling back to `NO_VIABLE_RECOVERY`, the planner falls through and attempts a blind `TOOL_RETRY_RECOVERY`.

3. **Adversarial Guardrail Bypass via Error Message Spoofing:**
   - **Location:** `backend/app/agents/healing/retry_engine.py` line ~200.
   - **Bug:** If a shell command contains an unlisted destructive command (e.g., `DROP DATABASE`, `taskkill /f /im edr_agent.exe`) that fails and reports `"TIMEOUT"`, `RetryEngine` re-authorizes retries up to $K_{\max}=3$ without checking task command parameters against permissions prior to retry dispatch.
