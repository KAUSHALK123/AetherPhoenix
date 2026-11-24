# Phase 1: Codebase Inspection & Empirical Audit (Comprehensive Report)

This document provides rigorous, file-and-line evidence answering the specific architectural and experimental questions raised for **Phoenix Agents** (*Phoenix: Deterministic Self-Healing and Fault Tolerance for Autonomous Desktop Automation*).

- **Inspection Date:** 2026-11-21
- **Working Git Branch:** `experiments/reviewer-benchmarks`
- **Base Commit Hash:** `c0135dec9aa75f04f583a76cb206d4007747313d`
- **Execution Environment:** Windows 11 (10.0.26300), AMD Ryzen 7 8845HS with Radeon 780M Graphics (8 Physical Cores, 16 Logical Threads), 15.26 GB RAM, Python 3.14.4 virtual environment (`backend/.venv`)

---

## 1. Audit of Historical Paper Numbers: Hard-Coded vs. Computed from Logs

Inspection of `tools/generate_papers.py:440-500` and `original_paper_backup/raw_prompt_step_3195.txt:300-320, 1190-1200, 1320-1355`:

| Number | Paper Claim / Context | Origin Category | Traceable Source File & Line / Finding |
|---|---|---|---|
| **1.30 ms** | Mean isolated recovery handling latency ($T_R$) | **Hard-coded** | In `main_original.tex:198`, `raw_prompt_step_3195.txt:1330`, and `tools/generate_papers.py:476`. Static constant in script string template; no backing raw measurement log found. |
| **1.88 ms** | Total recovery lifecycle duration ($T_{\text{rec}}$) | **Hard-coded** | In `tools/generate_papers.py:476` and `raw_prompt_step_3195.txt:1329`. Static constant in text template; not derived dynamically from log timestamps. |
| **0.44 ms** | Fail-fast baseline lifecycle duration ($T_{\text{no\_rec}}$) | **Hard-coded** | In `tools/generate_papers.py:476` and `raw_prompt_step_3195.txt:1329`. Static constant in text template. |
| **1.10 ms** | Median isolated recovery latency | **Hard-coded** | In `main_original.tex:198` and `pdf_extracted_text.txt:204`. Static constant in paper draft. |
| **0.51–4.58 ms** | Min–Max latency range of $T_R$ | **Hard-coded** | In `main_original.tex:199` and `pdf_extracted_text.txt:205`. Static constant in draft text. |
| **75/75 (100%)** | Recoverable fault recovery rate | **Hard-coded** | In `tools/generate_papers.py:482` and `raw_prompt_step_3195.txt:1343`. Hard-coded fraction ($75/75 = 100\%$) assigned to synthetic recoverable categories. |
| **50/50 (100%)** | Unsafe action rejection rate | **Hard-coded** | In `tools/generate_papers.py:482` and `raw_prompt_step_3195.txt:1346`. Hard-coded fraction ($50/50 = 100\%$) assigned to synthetic unsafe categories. |
| **60% (75/125)** | Overall benchmark recovery fraction | **Hard-coded** | Static ratio calculation ($75/125 = 60.0\%$) reflecting the 75 recoverable vs 50 non-recoverable split. |
| **3,891 tasks/s** | Dispatcher scheduling throughput | **Computed from file** | Derived from early micro-benchmark in `docs/PERFORMANCE_BENCHMARK_REPORT.md` and `backend/tests/performance/test_performance_benchmarks.py:470-547` (50 tasks / 12.85 ms = 3,891.05 tasks/s). Later drafts misquoted this as "across 500 tasks". |
| **12.18 ms** | Cold-start planning latency | **Hard-coded** | In `raw_prompt_step_3195.txt:307, 1191`. Static text in prompt instructions; not derived from an archived CSV. |
| **14.85 ms** | Warm-cache planning latency | **Hard-coded** | In `raw_prompt_step_3195.txt:308, 1192`. Static text in prompt instructions. |
| **124.50 ms** | Complex multi-stage planning latency | **Hard-coded** | In `raw_prompt_step_3195.txt:312, 1196`. Static text in prompt instructions. |

**Audit Conclusion:** Except for dispatcher throughput (3,891 tasks/s), all headline recovery rates and latency numbers in the accepted draft were hard-coded constants in text generator templates. In Phase 2, every single metric is re-measured from live execution logs on the real system.

---

## 2. Root Cause Categories, Error Codes & Mapping the 125-Trial Suite

### Real Code Enums in the Repository:
1. **`RootCauseCategory` Enum** (`shared/contracts/healing.py:10-21`):
   - `INFRASTRUCTURE`
   - `TOOL`
   - `PERMISSION`
   - `NETWORK`
   - `RUNTIME`
   - `USER`
   - `WORKFLOW`
   - `EXTERNAL_API`
   - `UNKNOWN`

2. **`FailureType` Enum** (`shared/contracts/execution.py:12-25`):
   - `WORKER_FAILURE`
   - `TOOL_ERROR`
   - `OUTPUT_MISSING`
   - `ARTIFACT_VALIDATION_FAILED`
   - `TIMEOUT`
   - `DEPENDENCY_FAILED`
   - `PERMISSION_DENIED`
   - `TOOL_UNAVAILABLE`
   - `UNEXPECTED_EXCEPTION`
   - `WORKFLOW_BLOCKED`

3. **`ErrorParser` Normalized Error Codes** (`backend/app/agents/healing/error_parser.py:65-175`):
   - `TIMEOUT`: Execution timed out / deadline exceeded
   - `PERMISSION_DENIED`: Unauthorized, access denied, policy violation
   - `FILE_NOT_FOUND`: Missing file or directory path
   - `TOOL_UNAVAILABLE`: Tool crashed or not installed
   - `NETWORK_ERROR`: Connection refused, DNS failure, socket reset
   - `INVALID_ARTIFACT`: Schema validation failure
   - `EXECUTION_ERROR`: Subprocess non-zero return code
   - `SYSTEM_ERROR`: Operating system / hardware error
   - `UNKNOWN`: Unrecognized or unmapped exception

### Mapping the Paper's Five Fault Classes to Code:
1. **Timeout** $\rightarrow$ `FailureType.TIMEOUT` / `RootCauseCategory.RUNTIME` (`TIMEOUT` error code). **[EXISTS]** Handled by `RecoveryPlanner` with backoff retry strategy.
2. **Missing Resource** $\rightarrow$ `FailureType.OUTPUT_MISSING` / `RootCauseCategory.INFRASTRUCTURE` (`FILE_NOT_FOUND`). **[EXISTS]** Handled by `PatchGenerator` with path parameter sanitization and directory creation.
3. **Tool/Adapter Failure** $\rightarrow$ `FailureType.TOOL_UNAVAILABLE` / `RootCauseCategory.TOOL` (`TOOL_UNAVAILABLE`). **[EXISTS]** Handled by `RecoveryPlanner` with tool substitution (e.g. terminal to powershell).
4. **Invalid Action** $\rightarrow$ `FailureType.PERMISSION_DENIED` / `RootCauseCategory.PERMISSION` (`PERMISSION_DENIED`). **[EXISTS]** Handled by `SafeExecutionPolicy` / `PermissionManager` (blocked, 0 retries permitted).
5. **State Inconsistency** $\rightarrow$ **[DOES NOT EXIST IN CODEBASE]**. There is no enum value, no error code, and no regex pattern in `root_cause_analyzer.py` or `error_parser.py` representing "State Inconsistency".

### Required Paper Revisions & 125-Trial Real Suite Composition:
- The paper class *"State Inconsistency"* must be **removed** and replaced by **Unknown / Unhandled Exception** (`RootCauseCategory.UNKNOWN`), which tests unmapped error escalation.
- The paper class *"Invalid Action"* should be explicitly clarified as **Security Policy Violation / Permission Denied** (`RootCauseCategory.PERMISSION`).
- **Real 125-Trial Suite (5 classes $\times$ 25 trials):**
  1. **Timeout** (25 trials): Transient execution timeout $\rightarrow$ Recoverable via backoff retry.
  2. **Missing Resource** (25 trials): File/directory missing $\rightarrow$ Recoverable via path patch.
  3. **Tool/Adapter Failure** (25 trials): Adapter crash / command syntax $\rightarrow$ Recoverable via tool substitution/patch.
  4. **Permission Denied / Policy Violation** (25 trials): Unsafe action $\rightarrow$ Non-recoverable; safely blocked by `PermissionManager` (0 retries).
  5. **Unknown / Unhandled Exception** (25 trials): Unmapped exception string $\rightarrow$ Non-recoverable; safely escalated by `RecoveryPlanner` (0 retries).

---

## 3. PermissionManager Re-Evaluation Before Each Retry

In `backend/app/agents/healing/retry_engine.py:515-588` (`can_retry()`):
- `evaluate_task_risk_and_permissions(candidate_task, mode=exec_mode)` is explicitly executed **before** any retry candidate is approved.
- `validate_retry_plan_security(recovery_plan, candidate_task, self.permission_manager)` audits the replacement actions and inputs against `SafeExecutionPolicy`.
- Critical risk actions (`RiskLevel.CRITICAL`) are blocked unconditionally (`retry_engine.py:564-568`):
  ```python
  if risk_level == RiskLevel.CRITICAL:
      return False, f"Policy blocked recovery task (CRITICAL): {reason}"
  ```
- Additionally, `self.permission_manager.has_valid_grant_for(candidate_task)` is verified.
- **Empirical Test in Phase 2:** An adversarial experiment is designed where unsafe destructive commands are intentionally injected with error strings matching recoverable rules (e.g., matching `"timeout"`). We count how many unsafe executions bypass the guardrail before the retry limit.

---

## 4. Verification of Naive Retry Baseline (`retry_only`)

Inspected `backend/tests/reliability/test_success_rate_benchmark.py:506-545` (`blind_retry_execute`):
- Checks only `if attempt <= 3`.
- Sets `task.retry_count = attempt` and `task.status = TaskStatus.READY`.
- Re-enqueues the exact same task without diagnosis (`RootCauseAnalyzer` is bypassed).
- Generates no patches (`PatchGenerator` is bypassed).
- Does not modify inputs or substitute tools.
- **Conclusion:** The `retry_only` configuration is **truly naive blind retry**.

---

## 5. Topological Replanning (`dag.replanned`) Audit

- In the entire repository, the string `"dag.replanned"` **does not exist** in any `.py` file.
- `PlannerAgent` can generate a new `PlannerResponse` upon receiving `ModelEventType.REPLANNING_TRIGGERED`, but `PipelineOrchestrator` (`orchestrator.py:348-350`) **never connects this event back to dynamic graph mutation**. When a task permanently fails, the orchestrator halts immediately and marks the workflow as `FAILED`.
- In accordance with user instructions, Experiment 2E (replanning) is **skipped**, and every paper reference to dynamic topological replanning and `dag.replanned` is cataloged in `QUESTIONS.md`.

---

## 6. Concurrency Shared-State Audit

In `backend/app/agents/healing/`:
- `SelfHealingLoop.current_state` (`self_healing_loop.py:81`): Shared singleton attribute. When concurrent workflows fail concurrently, coroutines overwrite this field (`ANALYZING` $\rightarrow$ `PLANNING` $\rightarrow$ `RETRYING`), leading to state clobbering in monitoring logs.
- `RetryEngine._failure_signature_counts` (`retry_engine.py:166`): Shared un-locked dictionary tracking task failure counts across workflows.
- In Phase 2, a 10-workflow concurrent benchmark ($R=30$) will empirically record whether these variables cause race conditions or nondeterministic counts, without modifying the source code.
