# MASTER IMPLEMENTATION & EMPIRICAL EVALUATION PROMPT: CLOSING RESEARCH GAPS IN PHOENIX AGENTS

> **Instructions for the AI Assistant:**
> Act as a senior systems architect, multi-agent researcher, and experimental evaluation engineer. 
> Execute the technical improvements and empirical benchmarks detailed below to address the metrics where Phoenix Agents currently **TRAILS** published literature or is **NOT MEASURED**.
>
> **Strict Rules:**
> 1. NEVER assume or fabricate numbers. Every reported metric must be measured from an actual benchmark run in the repository.
> 2. Do not weaken existing security invariants or remove existing tests.
> 3. Preserve the bounded recovery constraint ($K_{\text{max}}=3$) and deterministic fast path.

---

## TARGET 1: Close the Self-Healing Gap Under High Fault Density (Target: Boost 50% Fault Success from 60.40% to >85%)

### 1.1 Root Cause Analysis in Codebase
In `backend/app/agents/healing/recovery_planner.py` and `patch_generator.py`, recovery strategies currently rely on:
- Static tool substitution (e.g., swapping `terminal_tool` for `powershell_tool`),
- Exponential backoff retries without modifying inputs,
- Trivial path sanitization (stripping quotes or leading slashes).

When tasks fail due to malformed JSON schemas, invalid API arguments, or corrupted command flags (e.g. at 25% and 50% fault intensities in `backend/tests/reliability/results/results.csv`), Phoenix re-executes with the exact same flawed parameters, hitting the $K_{\text{max}}=3$ retry limit and causing the success rate to plummet to **60.40%**. In contrast, Babu & Agrawal (2026) achieve **98.8%** by invoking an LLM argument re-synthesizer constrained by explicit execution budgets.

### 1.2 Proposed Technical Implementation
1. **Bounded LLM Parameter Patcher (`LLMParameterPatcher`)**:
   - In `backend/app/agents/healing/patch_generator.py`, implement an asynchronous fallback method `synthesize_repaired_parameters(task, error, schema)`.
   - Trigger this method **only** when rule-based deterministic patching fails and the error is classified as `INVALID_ARGUMENTS` or `SCHEMA_VIOLATION`.
   - Constrain the LLM call with a strict 1-call budget ($K_{\text{llm}}=1$) and temperature=0.0.
   - Subject the synthesized parameters to immediate re-validation via `evaluate_task_risk_and_permissions()` in `backend/app/core/permissions/policies.py` to prevent privilege escalation.
2. **Strategy Demotion via Task History**:
   - Connect `TaskHistoryService` into `RecoveryPlanner.plan()`: if a failure signature `(tool, error_code)` has already failed a blind retry in the current workflow, automatically demote the simple retry and select parameter repair or tool substitution.

### 1.3 Experimental Protocol
- **Test File**: `backend/tests/reliability/test_success_rate_benchmark.py`.
- **Workload**: 101 synthetic tasks evaluated across 4 fault intensities: 0%, 10%, 25%, and 50%.
- **Baselines to Compare**:
  1. *No Recovery Baseline* (fail-fast on first error),
  2. *Retry-Only Baseline* (blind retries up to $K=3$),
  3. *Existing Phoenix Deterministic Healing* (current baseline: 60.40% at 50% faults),
  4. *Enhanced Phoenix Hybrid Healing* (with bounded argument re-synthesis).
- **Required Measurements**:
  - Exact completed task counts and success rate percentage at 0%, 10%, 25%, and 50% faults.
  - Mean latency per task (ms).
  - Number of LLM patching calls invoked.
  - Output files: `backend/tests/reliability/results/results.csv` and `results.json`.

---

## TARGET 2: Eliminate Silent Failures (Target: 0.0% Silent Failure Rate)

### 2.1 Root Cause Analysis in Codebase
In `backend/app/agents/supervisor/agent.py` and `backend/app/engine/validator.py`, task completion is judged strictly by:
- `result.exit_code == 0`,
- `output is not None`,
- `os.path.exists(filepath)` and `os.path.getsize(filepath) > 0`.

If a task produces a plausible but corrupted or empty deliverable (e.g., a PowerPoint deck with 0 slides, a PDF containing only binary header bytes without pages, or a JSON response missing expected keys), the Supervisor reports `success=True`. This allows silent failures to pass undetected, whereas Babu & Agrawal achieve **0.0%** silent failures using semantic verifiers.

### 2.2 Proposed Technical Implementation
1. **Structural Deliverable Validation (`StructuralOutputValidator`)**:
   - In `backend/app/engine/validator.py`, implement deep structural checks:
     - **PPTX Validation**: Use `zipfile.is_zipfile()`, verify presence of `ppt/presentation.xml`, load via `pptx.Presentation()`, and assert `len(prs.slides) >= 1` and total word count > 0.
     - **PDF Validation**: Assert binary header begins with `%PDF-`, verify presence of `%%EOF` trailer, load via `pypdf.PdfReader`, and assert `len(reader.pages) >= 1` with non-empty extracted text stream.
     - **Structured JSON Validation**: Assert returned dictionary matches the task's expected output schema keys.
2. **Failure Routing into Self-Healing**:
   - When structural validation fails, raise `DeliverableCorruptedError` with normalized error code `CORRUPTED_DELIVERABLE` and route directly into `SelfHealingLoop`.

### 2.3 Experimental Protocol
- **Test File**: `backend/tests/engine/test_structural_validator.py`.
- **Workload**: 50 deliverable generation tasks with injected structural corruptions (truncated ZIPs, empty presentation parts, malformed PDF streams, 0-slide decks).
- **Required Measurements**:
  - Silent failure detection rate (% of corrupted files caught by Supervisor).
  - Recovery success rate (% of detected corrupted deliverables re-generated successfully by HealingAgent).
  - False positive rate on 50 valid PPTX/PDF files.

---

## TARGET 3: Instrument Resource & Token Telemetry (Target: Full Cost & Memory Observability)

### 3.1 Root Cause Analysis in Codebase
Phoenix currently reports execution latency and throughput, but lacks token consumption and physical memory usage telemetry. `docs/PERFORMANCE_BENCHMARK_REPORT.md` lists object count deltas (`+1,812 objects`), but no physical Resident Set Size (RSS) in MB or LLM token counts.

### 3.2 Proposed Technical Implementation
1. **Execution Metrics Schema Expansion**:
   - In `shared/contracts/execution.py`, add fields to `ExecutionMetrics`:
     - `prompt_tokens: int = 0`
     - `completion_tokens: int = 0`
     - `total_cost_usd: float = 0.0`
     - `memory_rss_mb: float = 0.0`
     - `planning_strategy_used: str = "DETERMINISTIC_FAST_PATH"`
2. **Process Telemetry Instrumentation**:
   - In `backend/app/planner/agent.py` and `backend/app/planner/llm_planner.py`, record token counts from LLM responses and capture `psutil.Process().memory_info().rss / (1024 * 1024)` before and after planning.
   - Record these metrics in `TaskHistoryService` upon task completion.

### 3.3 Experimental Protocol
- **Test File**: `backend/tests/performance/test_resource_telemetry.py`.
- **Workload**: 10 concurrent workflows executing 50 heterogeneous tasks.
- **Required Measurements**:
  - Total tokens consumed across deterministic vs. LLM fallback paths.
  - Average process memory RSS (MB) under steady-state execution.
  - Token cost reduction percentage achieved by the deterministic planning fast-path compared to full LLM planning.

---

## EXECUTION ORDER & ACCEPTANCE CRITERIA
1. Implement Target 2 (Structural Output Validation) and verify with tests.
2. Implement Target 3 (Resource & Token Telemetry) and verify with tests.
3. Implement Target 1 (Bounded Parameter Repair) and execute the full benchmark run.
4. Update `research/phoenix_metrics.csv` and `research/comparison.csv` with the newly measured real numbers.
5. Report the exact before-and-after numbers in your response.
