# Unverified Items & Open Questions (QUESTIONS.md)

This document lists items from the reviewer feedback that require empirical evaluation data, missing repository log traces, or author confirmation. In accordance with the strict instructions, no values or citations have been fabricated in the camera-ready LaTeX text.

---

### 1. Item 8: Latency Breakdown Arithmetic (0.14 ms Discrepancy)
* **Context:** In Section V.D, the isolated software-level recovery handling latency is reported as $T_R = 1.30\text{ ms}$ (mean), while in Section V.E (ablation study), the fail-fast latency is $T_{\text{no\_rec}} = 0.44\text{ ms}$ and the recovery-enabled workflow latency is $T_{\text{rec}} = 1.88\text{ ms}$, giving an overhead of $\Delta T_{\text{overhead}} = 1.44\text{ ms}$.
* **Reviewer Query:** $0.44\text{ ms} + 1.30\text{ ms} = 1.74\text{ ms}$, leaving $0.14\text{ ms}$ between $1.88\text{ ms}$ and $1.74\text{ ms}$ unexplained.
* **Finding:** While the $0.14\text{ ms}$ difference is attributable to in-process `EventBus` coroutine scheduling, state reset overhead ($S_i \leftarrow \text{READY}$), and task re-enqueue latency outside the isolated diagnostic pipeline, no repository log file or benchmark trace explicitly records this $0.14\text{ ms}$ sub-component.
* **Action Taken:** Per the strict rule (*"only add an explanation if repository logs document it; if not documented, leave the text as is and record in QUESTIONS.md"*), the text in Sections V.D and V.E remains unchanged.
* **Author Question:** Would the authors like to run a targeted micro-benchmark logging the exact nanosecond-level breakdown between pipeline execution ($T_R$) and EventBus re-dispatch overhead to formally document this in a camera-ready footnote?

---

### 2. Item 9: Detailed Distribution Metrics (SD, IQR, Repetitions per Cell)
* **Context:** Reviewers requested uncertainty reporting, including Standard Deviation (SD), Interquartile Range (IQR), number of timing runs, and repetition counts per cell for the latency distributions in Section V.D.
* **Finding:** The repository logs record the observed mean ($1.30\text{ ms}$), median ($1.10\text{ ms}$), min ($0.51\text{ ms}$), and max ($4.58\text{ ms}$), as well as the total trial counts ($N=125$, $N_{\text{rec}}=75$, $N_{\text{unsafe}}=50$). However, raw trial-by-trial millisecond timing arrays required to compute the exact sample standard deviation and interquartile range were not archived in `backend/tests/` or `logs/`.
* **Action Taken:** Added exact Wilson 95% confidence intervals for all three categorical rates ($SR_{\text{rec}}$, $SR_{\text{safe}}$, $SR$). Did not invent or estimate SD/IQR numbers.
* **Author Question:** If raw per-trial benchmark timing dumps exist in local author archives, please provide the standard deviation and IQR so they can be inserted into Section V.D.

---

### 3. Item 17: Empirical Measurement of LLM Recovery Baseline
* **Context:** Claims that LLM-based recovery incurs prohibitive latency and token costs were softened to qualitative statements (*"each LLM call in recovery incurs latency and token cost that depend on the model and prompt size"*), removing any implication of a local head-to-head empirical measurement.
* **Author Question:** If a real comparative benchmark against an LLM-based repair baseline (e.g., GPT-4o-mini or Claude 3.5 Haiku parameter re-synthesis) is conducted in the future, would you like to introduce a comparative latency/token table in Section V?

---

### 4. Item 21: Table III Baseline Metrics Confirmation
* **Context:** Baseline metrics from published literature in Table II (formerly Table III) were verified against original source papers:
  - Babu & Agrawal [1]: **98.8%** task success rate (100-task benchmark). Confirmed.
  - BacktrackAgent (Mobile3M) [12]: **38.93%** error recovery accuracy, **1.938 s** per step. Confirmed.
  - BacktrackAgent (Auto-UI) [12]: **31.24%** error recovery accuracy, **1.374 s** per step. Confirmed.
  - Patel et al. [8]: Recovery-time reduction **Up to 47%**. Confirmed.
* **Action Taken:** All values verified and retained intact in LaTeX. Footnote added clarifying that numbers reflect reported values under each paper's distinct evaluation protocols.


---

### 5. Item 22: Documentation of All Claims of DAG Replanning and `dag.replanned` in Paper
* **Requirement:** Document every place the paper claims dynamic topological replanning or mentions the typed event `dag.replanned`.
* **Repository Findings:**
  1. The string `"dag.replanned"` does **NOT exist** anywhere in the Python repository.
  2. While `PlannerAgent.handle_replanning_event()` (`backend/app/agents/planner/agent.py:205-260`) catches `ModelEventType.REPLANNING_TRIGGERED` and synthesizes a new `PlannerResponse`, `PipelineOrchestrator` (`backend/app/engine/orchestrator.py:348-350`) **never connects this back to dynamic graph mutation**. When a task permanently fails, `orchestrator.py` halts immediately and marks the workflow as `FAILED`.
* **Occurrences in the Accepted Paper (`main.tex` / `main_original.tex`):**
  - **Abstract:** *"and dynamic DAG replanning for structural failures"*
  - **Section III.B (Stage 4 & 5):** *"When a task permanently fails and the recovery planner determines that structural re-execution is required, the healing agent emits a typed `dag.replanned` event containing the invalid subgraph and replacement candidate."*
  - **Section III.B (Stage 5):** *"Dynamic DAG Replanning: In Stage 5, the orchestrator consumes the replanning request, uses Kahn's topological sort algorithm to identify downstream tasks that depend on the failed node, prunes the invalid subgraph, and splices in replacement tasks while preserving graph acyclicity."*
  - **Figure 1 / Architectural Flow:** Caption and diagram arrows indicating `retry / dag-replanned`.
  - **Section IV.E (Dynamic Topological DAG Replanning):** *"When recovery cannot be achieved through parameter mutation or tool substitution alone, Phoenix triggers dynamic topological replanning... The topological replanning capability is part of the implemented recovery architecture but was not included in the 125-trial fault-injection evaluation reported in this paper."*
* **Recommendation:**
  In Phase 3, remove claims of end-to-end dynamic DAG replanning from the Abstract and Section III.B, and state plainly in Section IV.E and the Conclusion that dynamic topological replanning is an architectural prototype whose live orchestrator integration is future work.

---

### 6. Item 23: Baseline Exclusion - LLM Replanner
* **Context:** Reviewers suggested evaluating an LLM-based replanning baseline alongside fail-fast and naive retry.
* **Finding:** Neither `GEMINI_API_KEY` nor `OPENAI_API_KEY` was provided or present in the local environment (`os.getenv('GEMINI_API_KEY')` returned `False`).
* **Action Taken:** In accordance with the user instructions (*"Skip LLM replanner if no API key/unclear budget; document in QUESTIONS.md"*), only the two local deterministically verifiable baselines (`fail-fast` $K=0$ and `naive_retry` $K=3$) were benchmarked head-to-head on the 125-fault suite.
