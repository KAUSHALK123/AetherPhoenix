# Camera-Ready Unverified Items, Figures to Redraw, & Author Queries (QUESTIONS.md)

This document records architectural nuances, figures requiring author redraws, and disclosures that could not be verified by empirical log traces, ensuring absolute scientific integrity for the camera-ready version of the paper (*Phoenix: Deterministic Self-Healing and Fault Tolerance for Autonomous Desktop Automation*).

---

## 1. Figures Requiring Re-Export / Visual Redraw

### Figure 1: Architectural Diagram (`extracted_figures/fig_p2__Im1.png`)
* **Current Status:** Embedded in `main.tex` (line 90). The image is a pre-rendered bitmap artifact inherited from the draft manuscript.
* **Discrepancies in Graphic:**
  1. **Topological Replanning:** The visual flow in Fig. 1 shows a box for *"Topological Replanning"* emitting a `dag.replanned` event to `Orchestrator`. Per the audit, dynamic DAG replanning is not wired into the benchmark execution loop and has been demoted to Future Work in the paper text.
  2. **Fault Classification Labels:** Fig. 1 labels unsafe faults with the legacy taxonomy (*"Invalid Action"* and *"State Inconsistency"*). The paper text has been fully aligned with the real codebase taxonomy (*"Permission/Policy Violation"* and *"Unmapped/Unknown Exception"*).
* **Action Required by Authors:** If the original editable vector graphic (e.g., Draw.io, Figma, or TikZ source) is available, authors should:
  - Remove or grey out the `dag.replanned` branch (label as *"Future Work"* or remove).
  - Update the fault class labels in the classification box to match `RootCauseCategory` (`TIMEOUT`, `MISSING_RESOURCE`, `TOOL_UNAVAILABLE`, `PERMISSION_DENIED`, `UNKNOWN_ROOT_CAUSE`).

---

## 2. Unsupported Claims & Disclosures Documented in Paper

### A. Dynamic Adapter Substitution in the Benchmark Suite
* **Finding:** In the 125-fault benchmark suite, Tool/Adapter Failure faults were injected with `error_code="COMMAND_FAILED"`. `ErrorParser` does not map `COMMAND_FAILED` to `TOOL_UNAVAILABLE`, resulting in a confidence score $\le 0.30$ and safe rejection (0/25 recovered, 25/25 rejected).
* **Paper Disclosure:** The camera-ready text explicitly discloses this in Section IV.D, Section V.B, and Section V.F (Limitations). The paper clarifies that while `ToolRegistry` and adapter substitution logic exist in `patch_generator.py` and pass isolated component unit tests (`backend/tests/test_patch_generator.py`), dynamic substitution was not demonstrated within the 125-fault suite.

### B. Dynamic Topological DAG Replanning
* **Finding:** Runtime Kahn-based graph pruning and replacement graph synthesis exist in `backend/kernel/orchestrator.py`, but are not integrated into `backend/kernel/self_healing.py`.
* **Paper Disclosure:** Section III and Section IV were completely pruned of claims that the benchmark evaluated DAG replanning. It is now explicitly listed as Item 1 in Section VI.B (Future Work).

### C. Blind Held-Out Evaluation
* **Finding:** A template file `heldout_blind_TEMPLATE.json` was prepared, but was never populated with an independently withheld test suite. The 50-fault auxiliary set was used iteratively to identify and fix three bugs during the audit.
* **Paper Disclosure:** Section V.A (*Evaluation Disclosure*) and Section V.F (*Limitations*) explicitly report that no blind held-out evaluation was conducted, and that the 50-fault set served strictly as an internal diagnostic set.

### D. LLM-Based Recovery Comparison
* **Finding:** No head-to-head empirical experiments were run locally against active LLM models (e.g., GPT-4o-mini or Claude 3.5 Haiku) due to lack of local API keys and non-deterministic cloud latency.
* **Paper Disclosure:** The comparison in Section V.E is framed strictly as qualitative, citing established literature values for model latency and cost.

---

## 3. Verification Summary

* **LaTeX Files:**
  - `main_before_experiments.tex`: Unmodified snapshot prior to experiment updates.
  - `main.tex`: Final camera-ready clean version.
  - `main_highlighted.tex`: Identical to `main.tex`, with all changed/added text wrapped in `\chg{...}` via `\usepackage{xcolor}` and `\newcommand{\chg}[1]{{\color{blue}#1}}`.
* **Page Count Verification:**
  - `main.pdf`: Exactly 6 pages (no overflow).
  - `main_highlighted.pdf`: Exactly 6 pages (no overflow).
* **Placeholder Scan:** Zero instances of `TODO`, `ASK ME`, `TBD`, `[?]`, or unverified numbers.
