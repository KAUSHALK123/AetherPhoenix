# Camera-Ready Paper Revisions (CHANGES.md)

**Paper Title:** Phoenix: Deterministic Self-Healing and Fault Tolerance for Autonomous Desktop Automation  
**Target Venue:** IEEE Conference Camera-Ready Track  
**Baseline Git Tag:** `paper-freeze-v2` (`08b790406692ac4343a4786dd48e9311ed909d20`)  
**Data Source:** `experiments/results/summary.csv` (generated from empirical benchmark harness)  
**Deliverable Files:**
- `main_before_experiments.tex` (backup prior to experimental update)
- `main.tex` (final clean camera-ready LaTeX, compiled to `main.pdf`, exactly 6 pages)
- `main_highlighted.tex` (identical to `main.tex`, with changes wrapped in `\chg{...}`, compiled to `main_highlighted.pdf`, exactly 6 pages)
- `CHANGES.md` (this traceability and revision document)
- `QUESTIONS.md` (unsupported claims, figures to redraw, and author inquiries)

---

## 1. Number Mapping Table (Every Number in Revised Paper Traceable to `summary.csv`)

Every numerical quantity, percentage, latency metric, and confidence interval in `main.tex` is directly mapped to a specific row in `experiments/results/summary.csv`:

| Paper Location | Metric / Value in LaTeX | `summary.csv` Row | Experiment | Config | Metric Name | Raw CSV Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Abstract, Sec I, Sec V.B, Table I, Sec VI.A | **50/75 (66.7%)** Recoverable Rate | Row 20 | `125_fault_suite_synthetic` | `phoenix_75_recoverable_legacy_command_failed` | `recoverable_case_rate` | `mean=0.6667`, $n=75$ |
| Abstract, Sec I, Sec V.B, Table I, Sec VI.A | **[55.4%, 76.3%]** Wilson 95% CI | Row 20 | `125_fault_suite_synthetic` | `phoenix_75_recoverable_legacy_command_failed` | `ci_95_low, ci_95_high` | `0.5542, 0.7629` ($n=75$) |
| Abstract, Sec I, Sec V.B, Table I, Sec VI.A | **50/50 (100.0%)** Safe Rejection | Row 24 | `125_fault_suite_synthetic` | `phoenix_50_non_recoverable` | `safe_rejection_rate` | `mean=1.0`, $n=50$ |
| Abstract, Sec I, Sec V.B, Table I, Sec VI.A | **[92.9%, 100.0%]** Wilson 95% CI | Row 24 | `125_fault_suite_synthetic` | `phoenix_50_non_recoverable` | `ci_95_low, ci_95_high` | `0.9287, 1.0` ($n=50$) |
| Abstract, Sec I, Sec V.B, Table I, Sec VI.A | **50/125 (40.0%)** Overall Recovery | Row 2 | `125_fault_suite_synthetic` | `phoenix` | `overall_accuracy_rate` | `mean=0.4`, $n=125$ |
| Abstract, Sec I, Sec V.B, Table I, Sec VI.A | **[31.8%, 48.8%]** Wilson 95% CI | Row 2 | `125_fault_suite_synthetic` | `phoenix` | `ci_95_low, ci_95_high` | `0.3183, 0.4876` ($n=125$) |
| Abstract, Sec I, Sec V.B, Table I, Sec VI.A | **100/125 (80.0%)** Correct Decision | Row 29 | `125_fault_suite_synthetic` | `phoenix_125_total_correct_handling_legacy_tool` | `correct_decision_rate` | `mean=0.8`, $n=125$ |
| Abstract, Sec I, Sec V.B, Table I, Sec VI.A | **[72.1%, 86.1%]** Wilson 95% CI | Row 29 | `125_fault_suite_synthetic` | `phoenix_125_total_correct_handling_legacy_tool` | `ci_95_low, ci_95_high` | `0.7214, 0.8607` ($n=125$) |
| Table I (Timeout Class) | **25/25 (100.0%)** Rec, **[86.7, 100.0]%** CI | Row 3 | `125_fault_suite_synthetic` | `phoenix_TIMEOUT` | `class_rate` | `mean=1.0, low=0.8668, high=1.0`, $n=25$ |
| Table I (Missing Resource Class) | **25/25 (100.0%)** Rec, **[86.7, 100.0]%** CI | Row 4 | `125_fault_suite_synthetic` | `phoenix_MISSING_RESOURCE` | `class_rate` | `mean=1.0, low=0.8668, high=1.0`, $n=25$ |
| Table I (Tool/Adapter Failure Class) | **0/25 (0.0%)** Rec, 25/25 Rej, **[0.0, 13.3]%** CI | Row 5, 38 | `125_fault_suite_synthetic` | `phoenix_TOOL_ADAPTER_FAILURE` | `class_rate` | `mean=0.0, low=0.0, high=0.1332`, $n=25$ |
| Table I (Permission/Policy Violation) | **0/25 (0.0%)** Rec, 25/25 Rej, **[0.0, 13.3]%** CI | Row 6 | `125_fault_suite_synthetic` | `phoenix_PERMISSION_DENIED` | `class_rate` | `mean=0.0, low=0.0, high=0.1332`, $n=25$ |
| Table I (Unmapped/Unknown Exception) | **0/25 (0.0%)** Rec, 25/25 Rej, **[0.0, 13.3]%** CI | Row 7 | `125_fault_suite_synthetic` | `phoenix_UNMAPPED_EXCEPTION` | `class_rate` | `mean=0.0, low=0.0, high=0.1332`, $n=25$ |
| Table I, Sec V.C (Naive Retry Overall) | **25/125 (20.0%)** Rec, **[13.9, 27.9]%** CI | Row 8 | `125_fault_suite_synthetic` | `retry_only` | `overall_accuracy_rate` | `mean=0.2, low=0.1393, high=0.2786`, $n=125$ |
| Table I, Sec V.C (Naive Retry Timeout) | **25/25 (100.0%)** Rec | Row 9 | `125_fault_suite_synthetic` | `retry_only_TIMEOUT` | `class_rate` | `mean=1.0, low=0.8668, high=1.0`, $n=25$ |
| Table I, Sec V.C (Naive Retry Missing Resource) | **0/25 (0.0%)** Rec | Row 10 | `125_fault_suite_synthetic` | `retry_only_MISSING_RESOURCE` | `class_rate` | `mean=0.0, low=0.0, high=0.1332`, $n=25$ |
| Table I, Sec V.C (Naive Retry Tool/Adapter) | **0/25 (0.0%)** Rec | Row 11 | `125_fault_suite_synthetic` | `retry_only_TOOL_ADAPTER_FAILURE` | `class_rate` | `mean=0.0, low=0.0, high=0.1332`, $n=25$ |
| Table I, Sec V.C (Naive Retry Recoverable) | **25/75 (33.3%)** Rec, **[23.7, 44.6]%** CI | Row 22 | `125_fault_suite_synthetic` | `retry_only_75_recoverable` | `recoverable_case_rate` | `mean=0.3333, low=0.2371, high=0.4458`, $n=75$ |
| Table I, Sec V.C (Naive Retry Safe Rejection) | **0/50 (0.0%)** Rej, **[0.0, 7.1]%** CI | Row 25 | `125_fault_suite_synthetic` | `retry_only_50_non_recoverable` | `safe_rejection_rate` | `mean=0.0, low=0.0, high=0.0713`, $n=50$ |
| Table I, Sec V.C (Fail-Fast Overall) | **0/125 (0.0%)** Rec, **[0.0, 3.0]%** CI | Row 14 | `125_fault_suite_synthetic` | `no_recovery` | `overall_accuracy_rate` | `mean=0.0, low=0.0, high=0.0298`, $n=125$ |
| Table I, Sec V.C (Fail-Fast Recoverable) | **0/75 (0.0%)** Rec, **[0.0, 4.9]%** CI | Row 23 | `125_fault_suite_synthetic` | `no_recovery_75_recoverable` | `recoverable_case_rate` | `mean=0.0, low=0.0, high=0.0487`, $n=75$ |
| Table I, Sec V.C (Fail-Fast Safe Rejection) | **50/50 (100.0%)** Rej, **[92.9, 100.0]%** CI | Row 26 | `125_fault_suite_synthetic` | `no_recovery_50_non_recoverable` | `safe_rejection_rate` | `mean=1.0, low=0.9287, high=1.0`, $n=50$ |
| Table I, Sec V.C (Fail-Fast Total Correct) | **50/125 (40.0%)** Correct, **[31.8, 48.8]%** CI | Row 31 | `125_fault_suite_synthetic` | `no_recovery_125_total_correct_handling` | `correct_decision_rate` | `mean=0.4, low=0.3183, high=0.4876`, $n=125$ |
| Sec V.A (Dual Injection Mode Parity) | **100% parity** across 125 trials | Rows 2--7 vs 32--37 | `125_fault_suite_real_exception` | `phoenix` & classes | All metrics identical | Synthetic vs Real Exception match 100% |
| Sec V.A, Sec V.D (Repeatability across seeds) | **100% determinism** across 30 seeds | Rows 42, 43 | `determinism_and_repeatability` | `synthetic_125`, `real_exception_125` | `identical_outcomes_across_30_seeds` | `mean=1.0, low=1.0, high=1.0`, $n=30$ |
| Sec V.D, Table II ($T_R$ Stages 1--5) | **Mean: 2.05 ms, SD: 0.69 ms, Med: 1.98 ms, IQR: 0.71 ms, Range: [1.03, 11.84] ms** | Row 45 | `latency_tracing_off` | `phoenix_mocked_adapter` | `T_R_ms` | `mean=2.0515, std=0.6908, med=1.9801, iqr=0.7145, low=1.0301, high=11.8418`, $n=1500$ |
| Sec V.D, Table II ($T_{\text{rec}}$ Dispatch--Done) | **Mean: 2.06 ms, SD: 0.69 ms, Med: 1.98 ms, IQR: 0.72 ms, Range: [1.03, 11.85] ms** | Row 46 | `latency_tracing_off` | `phoenix_mocked_adapter` | `T_rec_ms` | `mean=2.0553, std=0.6914, med=1.9840, iqr=0.7161, low=1.0318, high=11.8453`, $n=1500$ |
| Sec V.D, Table II ($T_{\text{rec}}$ Real Filesystem) | **Mean: 2.30 ms, SD: 0.25 ms, Med: 2.29 ms, IQR: 0.28 ms, Range: [1.74, 3.17] ms** | Row 48 | `latency_tracing_off` | `phoenix_real_filesystem_missing_resource` | `T_rec_real_fs_ms` | `mean=2.3045, std=0.2540, med=2.2947, iqr=0.2830, low=1.7355, high=3.1686`, $n=100$ |
| Sec V.D, Table II ($T_{\text{no\_rec}}$ Fail-Fast) | **Mean: 0.001 ms, SD: 0.002 ms, Med: 0.001 ms, IQR: 0.000 ms, Range: [0.001, 0.073] ms** | Row 47 | `latency_tracing_off` | `no_recovery` | `T_no_rec_ms` | `mean=0.0010, std=0.0015, med=0.0008, iqr=0.0004, low=0.0005, high=0.0726`, $n=3750$ |
| Sec V.E (Experiment D Concurrency) | **100.0% outcome match**, 0 clobbering, 0 collisions | Row 44 | `concurrency_determinism` | `10_concurrent_workflows` | `outcome_match_rate` | `mean=1.0, low=0.8865, high=1.0`, $n=30$ |

---

## 2. Detailed Breakdown of the 12 Requested Edits

### Edit 1: Fault Classes Renamed to Implementation Reality
* **Action:** Replaced `"Invalid Action"` and `"State Inconsistency"` with `"Permission/Policy Violation"` and `"Unmapped/Unknown Exception"` across Abstract, Introduction, Section III.A (Eq. 2), Section III.B (Eq. 3), Section IV.C, Section V, Table I, and Conclusion.
* **Trace:** `backend/kernel/root_cause_analyzer.py` line 14 defines `RootCauseCategory` (`TIMEOUT`, `MISSING_RESOURCE`, `TOOL_UNAVAILABLE`, `PERMISSION_DENIED`, `UNKNOWN_ROOT_CAUSE`). The paper previously had speculative category names from draft templates. The 125 faults are explicitly structured as 25 distinct faults per class across these 5 real classes.

### Edit 2: DAG Replanning Removed from System Description
* **Action:** Removed all mentions of dynamic/topological DAG replanning and `dag.replanned` from Section III.B (Stage 4 & Stage 5), Section IV.D (formerly Section III.C / IV.E), and Table descriptions.
* **Trace:** Added explicit item (1) in Section VI.B (Future Work) stating that while topological graph pruning and Kahn-based dependency sorting exist in `backend/kernel/orchestrator.py`, they are not wired into the self-healing benchmark loop.

### Edit 3: All Old Numbers Replaced with Measured Empirical Results
* **Action:** Completely purged all unverified draft numbers (`1.30`, `1.88`, `0.44`, `1.44`, `1.10`, `0.51--4.58`, `75/75`, `50/50`, `60%`, `100% vs 0%`).
* **Trace:** Replaced with exact values from `summary.csv` (`T_R = 2.05` ms, `T_rec = 2.06` ms, `T_rec,real_fs = 2.30` ms, `T_no_rec = 0.001` ms; Recoverable rate = 50/75 [66.7%]; Safe rejection = 50/50 [100.0%]; Overall recovery = 50/125 [40.0%]; Correct decisions = 100/125 [80.0%]).

### Edit 4: Honest Reporting of Tool/Adapter Failure Class
* **Action:** Reported 0/25 (0.0%) recovery on Tool/Adapter Failure in the benchmark suite.
* **Trace:** The benchmark suite injected unmapped command failure strings (`COMMAND_FAILED`), which `ErrorParser` did not map to `TOOL_UNAVAILABLE`. Under the $\le 0.30$ confidence rule, they were classified as `UNKNOWN_ROOT_CAUSE` and safely rejected (25/25 rejected). The paper explicitly clarifies (Abstract, Section IV.D, Section V.B, Section V.F) that adapter substitution via `ToolRegistry` was verified in isolated unit tests (`backend/tests/test_patch_generator.py`), not demonstrated in the 125-fault suite.

### Edit 5: Naive Retry Baseline Honesty
* **Action:** Accurately detailed Naive Retry's behavior: it achieves 25/25 (100.0%) on Timeout (transient delay clears on retry), but 0/25 (0.0%) on Missing Resource (blind retries cannot create missing directories), 0/25 (0.0%) on Tool/Adapter Failure, 33.3% (25/75) across recoverable faults, 0/50 (0.0%) safe rejection (executing 150 unauthorized retries before terminal failure), and 20.0% (25/125) overall recovery.

### Edit 6: Experimental Setup Detailed in Section V.A
* **Action:** Documented exact hardware and OS specifications: AMD Ryzen 7 8845HS (16 threads), 15.26 GB RAM, Windows 11 Home (build 10.0.26300), Python 3.14.4. Documented dual injection modes (synthetic and real_exception, achieving 100% parity across all 125 trials), 30 randomized repeats (seeds 42--71), and specified the distinct fault as the statistical unit ($n=25, 75, 50, 125$) for Wilson 95% score confidence intervals.

### Edit 7: Audit Bug Disclosures
* **Action:** In Section V.A (*Evaluation Disclosure*), transparently reported the three bug fixes identified during the audit: (i) confidence boundary condition $\le 0.30$ in `RecoveryPlanner`, (ii) missing-path directory synthesis block in `RetryEngine`, and (iii) permission-signal ordering error in `ErrorParser`. Clarified that the 50-fault auxiliary set served strictly as an internal diagnostic set, not as a blind held-out evaluation.

### Edit 8: Blind Held-Out Disclaimer
* **Action:** Explicitly stated in Section V.A and Section V.F (Limitations) that no blind held-out evaluation was conducted, and that `heldout_blind_TEMPLATE.json` was prepared as a template but left unpopulated.

### Edit 9: Qualitative LLM Comparison & Concurrency Audit (Experiment D)
* **Action:** Maintained comparison with LLM orchestrators as qualitative in Section V.E (latency, cost, and determinism). Added Experiment D reporting 10 concurrent workflows over 30 repeats with 100.0% outcome match vs sequential execution, 0 state clobbering events, and 0 failure signature collisions.

### Edit 10: Tables Restructured
* **Action:** 
  - **Table I:** Replaced old Table II with a comprehensive 9-row table reporting all 5 fault classes ($n=25$ each) plus 4 aggregate rows (Recoverable $n=75$, Non-Recoverable $n=50$, Entire Suite $n=125$, Correct Decision $n=125$). Included Phoenix Recovery, Phoenix Rejection, Wilson 95% CI, Naive Retry, and Fail-Fast columns.
  - **Table II:** Compact single-column table reporting empirical latency distributions with tracing OFF ($T_R$, $T_{\text{rec}}$, $T_{\text{rec,RealFS}}$, $T_{\text{no\_rec}}$) with Mean, SD, Median, IQR, and ranges in the table note.

### Edit 11: Abstract, Contributions, and Conclusion Rewritten
* **Action:** Synchronized Abstract, Contributions bullet points, and Section VI.A Conclusion with all empirical findings. Removed speculative claims of 100% recovery or dynamic DAG replanning.

### Edit 12: Strict Page Budget Enforcement ($\le 6$ Pages)
* **Action:** Both `main.pdf` and `main_highlighted.pdf` compile with **total page count: 6** with zero overflow onto page 7. All 12 references fit cleanly on page 6. Zero placeholders (`TODO`, `ASK ME`, `TBD`, `[?]`, `XXX`) exist in either LaTeX source.
