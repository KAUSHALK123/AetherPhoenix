# CHANGES.md: Camera-Ready Revision Log & Mapping to summary.csv

This document logs all updates made to the camera-ready manuscript (`main.tex` and `main_highlighted.tex`), mapping every empirical number directly to its corresponding row in `experiments/results/summary.csv` (derived from frozen commit `7c35ab854d503924cb2af533ffee3162ff421b7e`).

---

## 1. Number-by-Number Mapping to `summary.csv`

| Paper Section & Metric | Value Reported | `summary.csv` Row | Column & Exact Value in CSV |
| :--- | :--- | :--- | :--- |
| **Abstract / Intro / Table II:** Recoverable Faults Recovery Rate | 100.0% (75/75), CI: [95.1, 100.0]% | Row 19 (`Aggregate,Recoverable_Classes_Total`) | `Phoenix_After` = `75/75 (100.0%)`, `Wilson_95_CI` = `[95.1%, 100.0%]` |
| **Abstract / Intro / Table II:** Non-Recoverable Safe Rejection Rate | 100.0% (50/50), CI: [92.9, 100.0]% | Row 20 (`Aggregate,Non_Recoverable_Safe_Rejections`) | `Phoenix_After` = `50/50 (100.0%)`, `Wilson_95_CI` = `[92.9%, 100.0%]` |
| **Abstract / Intro / Table II:** Overall Suite Recovery Rate | 60.0% (75/125), CI: [51.2, 68.2]% | Row 22 (`Aggregate,Overall_Suite_Recovery`) | `Phoenix_After` = `75/125 (60.0%)`, `Wilson_95_CI` = `[51.2%, 68.2%]` |
| **Abstract / Table II:** Naive Retry Overall Recovery Rate | 20.0% (25/125), CI: [13.9, 27.9]% | Row 22 (`Aggregate,Overall_Suite_Recovery`) | `Naive_Retry` = `25/125 (20.0%)` |
| **Abstract / Table II:** Fail-Fast Overall Recovery Rate | 0.0% (0/125), CI: [0.0, 3.0]% | Row 22 (`Aggregate,Overall_Suite_Recovery`) | `Fail_Fast` = `0/125 (0.0%)` |
| **Table II:** Timeout Class Recovery | 100.0% (25/25), CI: [86.7, 100.0]% | Row 14 (`Fault_Class,TIMEOUT`) | `Phoenix_After` = `25/25 (100.0%)`, `Wilson_95_CI` = `[86.7%, 100.0%]` |
| **Table II:** Missing Resource Class Recovery | 100.0% (25/25), CI: [86.7, 100.0]% | Row 15 (`Fault_Class,MISSING_RESOURCE`) | `Phoenix_After` = `25/25 (100.0%)`, `Wilson_95_CI` = `[86.7%, 100.0%]` |
| **Table II:** Tool/Adapter Failure Class Recovery | 100.0% (25/25), CI: [86.7, 100.0]% | Row 16 (`Fault_Class,TOOL_ADAPTER_FAILURE`) | `Phoenix_After` = `25/25 (100.0%)`, `Wilson_95_CI` = `[86.7%, 100.0%]` |
| **Table II:** Permission/Policy Safe Rejection | 100.0% (25/25), CI: [86.7, 100.0]% | Row 17 (`Fault_Class,PERMISSION_DENIED`) | Rejections After = `25/25`, Recovery = `0/25 (0.0%)` |
| **Table II:** Unmapped/Unknown Safe Rejection | 100.0% (25/25), CI: [86.7, 100.0]% | Row 18 (`Fault_Class,UNMAPPED_EXCEPTION`) | Rejections After = `25/25`, Recovery = `0/25 (0.0%)` |
| **Table II:** Naive Retry on Recoverable Pool | 33.3% (25/75), CI: [23.7, 44.6]% | Row 19 (`Aggregate,Recoverable_Classes_Total`) | `Naive_Retry` = `25/75 (33.3%)` |
| **Table II:** Overall Rejection Row | 40.0% (50/125) | Row 21 (`Aggregate,Overall_Rejections_Paper_Row`) | `Phoenix_After` = `50/125 (40.0%)` (75 rec + 50 rej = 125) |
| **Abstract / Intro / Latency:** Diagnostic Latency $T_R$ Mean | 11.99 ms | Row 2 (`Latency,T_R (ms),Mean`) | `Phoenix_After` = `11.9921` |
| **Latency Table III:** Diagnostic Latency $T_R$ Std | 7.04 ms | Row 3 (`Latency,T_R (ms),Std`) | `Phoenix_After` = `7.0401` |
| **Latency Table III:** Diagnostic Latency $T_R$ Median | 11.36 ms | Row 4 (`Latency,T_R (ms),Median`) | `Phoenix_After` = `11.3567` |
| **Latency Table III:** Diagnostic Latency $T_R$ IQR | 10.81 ms | Row 5 (`Latency,T_R (ms),IQR`) | `Phoenix_After` = `10.8083` |
| **Latency Table III:** Diagnostic Latency $T_R$ Observations | $n = 2250$ | Row 6 (`Latency,T_R (ms),Sample_N`) | `Phoenix_After` = `2250` (30 repeats $\times$ 75 recovered) |
| **Latency Table III:** Total Recovery $T_{\text{rec}}$ Mean | 12.00 ms | Row 7 (`Latency,T_rec (ms),Mean`) | `Phoenix_After` = `11.9961` |
| **Latency Table III:** Total Recovery $T_{\text{rec}}$ Std | 7.04 ms | Row 8 (`Latency,T_rec (ms),Std`) | `Phoenix_After` = `7.0407` |
| **Latency Table III:** Total Recovery $T_{\text{rec}}$ Median | 11.36 ms | Row 9 (`Latency,T_rec (ms),Median`) | `Phoenix_After` = `11.3606` |
| **Latency Table III:** Total Recovery $T_{\text{rec}}$ IQR | 10.81 ms | Row 10 (`Latency,T_rec (ms),IQR`) | `Phoenix_After` = `10.8099` |
| **Latency Table III:** Total Recovery $T_{\text{rec}}$ Observations | $n = 2250$ | Row 11 (`Latency,T_rec (ms),Sample_N`) | `Phoenix_After` = `2250` |
| **Latency Table III:** Real NTFS Missing Resource Latency Mean | 1.89 ms | Row 13 (`Latency,Real_FS_Latency (ms),Mean`) | `Phoenix_After` = `1.8882` ($n=100$) |
| **Latency Table III:** Fail-Fast Latency $T_{\text{no\_rec}}$ Mean | 0.0007 ms (0.001 ms) | Row 12 (`Latency,T_no_rec (ms),Mean`) | `Fail_Fast` = `0.0007` ($n=3750$) |
| **Section V.E:** Timeout Backoff Sleep Wall-Clock Duration | 1010.50 ms (median 1010.35 ms) | Rows 45--46 (`Timeout_Backoff,Wall_Clock_Latency`) | `Mean` = `1010.5008`, `Median` = `1010.35` |
| **Section V.F.2:** Adversarial Safety Unauthorized Dispatches | Phoenix = 0, Naive Retry = 75 | Row 47 (`Adversarial_Safety,Destructive_Commands`) | Phoenix: 0 dispatches; Naive Retry: 75 dispatches over 25 commands |
| **Section V.F.1:** Concurrency Audit Clobbering / Collisions | 0 clobbering, 0 collisions | Rows 48--49 (`Concurrency_Audit,10_Workflows_30_Repeats`) | Zero state clobbering events, zero failure signature collisions |
| **Section V.G:** S2 Real Adapters Subprocess Timeout | 10/10 (100.0%), mean $T_R = 8.39$ ms | Row 25 (`Scenario_S2_Real_Adapters,real_subprocess_timeout`) | `10/10 (100.0%)`, `mean=8.3855ms` |
| **Section V.G:** S2 Real Adapters Permission Denials (4 types) | 0/10 recovered, 10/10 safely rejected each | Rows 23, 24, 26, 27 (`Scenario_S2_Real_Adapters`) | File locked, missing path, unreachable port, readonly dir: 0/10 rec |
| **Section V.G:** S3 Large Workflow Graphs (10 & 20 tasks) | 300/300 (100.0%), $T_R \in [2.23, 5.47]$ ms | Rows 28--39 (`Scenario_S3_Large_Workflows`) | 12 settings $\times$ 25 trials = 300 trials, 100% completion |
| **Section V.G:** S4 Additional Fault Types | Net Refused: 10/10; Unknown Adapter: 10/10; Disk Full / Locked / JSON: 0/10 (10/10 rejected) | Rows 40--44 (`Scenario_S4_Additional_Faults`) | Exact matches with intended deterministic classification |

---

## 2. Item-by-Item Editorial Implementation Details

1. **Headline Numbers & Clarification:**
   - Updated headline numbers: Recoverable faults = 75/75 (100.0%, [95.1, 100.0]%), Safe rejection = 50/50 (100.0%, [92.9, 100.0]%), Overall suite = 75/125 = 60.0% ([51.2, 68.2]%), Naive Retry = 25/125 = 20.0% ([13.9, 27.9]%), Fail-Fast = 0/125 = 0.0%.
   - Clarified that recoverable classes are the ones the deterministic rules were designed for (Timeout, Missing Resource, Tool/Adapter Failure).
   - Removed the "total correct decision rate" metric (former Eq. 9).

2. **Evaluation Disclosure:**
   - Added disclosure in Section V.A describing all four fixes: (i) confidence boundary $\le 0.30$, (ii) missing-path recoverability block in `RetryEngine`, (iii) permission-signal ordering error, and (iv) Tool/Adapter faults initially rejected (0/25) until real adapter signatures emitted by codebase adapters were registered in `ErrorParser`, reaching 25/25.
   - Also disclosed the two shared-state defect resolutions (`SelfHealingLoop.current_state` replaced with per-task state; `RetryEngine._failure_signature_counts` re-keyed with atomic updates).
   - Clarified that the 50-fault auxiliary set served strictly as a diagnostic set, not as a blind held-out evaluation.

3. **Tool/Adapter Failure & Limitation 2:**
   - Section IV.D and Limitation 2 explicitly note: dynamic adapter substitution was evaluated on $n=25$ faults with mocked adapters through `ToolRegistry` (verified in unit tests in `test_adapter_substitution.py`); real adapters were not evaluated in the 125-fault benchmark suite.

4. **Table II (Recovery Rates) Formatting:**
   - One row per class, plus aggregate rows for Recoverable, Non-Recoverable, and Overall Suite.
   - Exact Wilson 95% score intervals labeled for each row.
   - Recovered (75) + Rejected (50) = 125 clearly demonstrated.
   - Uses `booktabs` rules, `\footnotesize`, and natural sizing without `\resizebox`.

5. **Latency Table III:**
   - Populated exclusively from Step 0b unified run (`run_step0_latency.py`, tracing OFF).
   - Reports mean, SD, median, IQR, and sample size for $T_R$ ($n=2250$), $T_{\text{rec}}$ ($n=2250$), Real FS ($n=100$), and Fail-Fast ($n=3750$).
   - Explicitly notes delimiter code lines and backoff sleep distinction.

6. **Related Work Classical Foundations & Comparison Table:**
   - Added foundational paragraph citing Avižienis et al. (2004), Gray & Siewiorek (1991), Garcia-Molina & Salem (1987), and Nygard (2018).
   - Added compact Table I comparing Babu (2026), Jeong (2026), Patel (2026), Wu / BacktrackAgent (2025), and Phoenix.
   - BacktrackAgent step latencies cited as 1.374--1.938 s (GUI-agent execution).
   - Removed ungrounded LLM latency claims.

7. **Concurrency Audit & Adversarial Safety:**
   - Section V.F.1 documents Experiment D (10 concurrent workflows, 30 repeats, 300 workflows, 1500 tasks) with 0 state-clobbering events and 0 signature collisions.
   - Section IV.A explains the concurrency ordering model (single-threaded cooperative event loop, atomic read-modify-write without intervening `await` yields).
   - Section V.F.2 reports adversarial safety on 25 destructive/privilege-escalating commands: Phoenix recorded 0 retry dispatches; naive retry recorded 75 unauthorized dispatches.

8. **Worked Examples & Scenario Studies:**
   - Section V.C details three real execution traces from `worked_examples.md` (Missing Resource, Permission Denied, Unmapped Exception).
   - Section V.G details S2 (Real Adapters, $n=10$ each), S3 (Larger Graphs, 300 trials), and S4 (Additional Fault Types, $n=10$ each).

9. **Repetition Reduction & Page Limit:**
   - Abstract is 179 words ($\le 200$ words) and contains exactly 3 numbers (100.0%, 60.0%, 11.99 ms).
   - Bullet points in Section I and Section VI carry no confidence intervals.
   - The paper strictly adheres to the 6-page ceiling including references: both `main.pdf` and `main_highlighted.pdf` compile to exactly 6 pages.
