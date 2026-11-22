# Phoenix Agents: Revised IEEE Conference Paper

This repository contains the self-contained, fully revised IEEE conference manuscript for:

**"Phoenix Agents: Governed Multi-Agent Desktop Automation with Interactive Planning and Multi-Format Deliverable Generation"**

---

## 1. Directory Structure

```text
revised_paper/
├── main.tex                   # Anonymous review version (double-blind compliant)
├── main_camera_ready.tex      # Camera-ready version (with author block & AMC affiliation)
├── anonymous_submission.pdf   # Compiled anonymous PDF (strict 6-page IEEE layout)
├── camera_ready.pdf           # Compiled camera-ready PDF (strict 6-page IEEE layout)
├── IEEEtran.cls               # Official CTAN IEEE conference document class
├── validation_report.md       # Comprehensive audit, verification, and validation report
├── README.md                  # This compilation and replication guide
├── figures/
│   ├── phoenix_architecture.jpg  # High-resolution 300 DPI system architecture diagram
│   └── phoenix_architecture.png  # Lossless source diagram
└── graphs/
    ├── graph_planning_latency.jpg # Fig. 2: Decision and planning latency
    ├── graph_recovery_rate.jpg    # Fig. 3: Recovery rates across fault classes
    ├── graph_task_success.jpg     # Fig. 4: Task completion across fault intensities
    └── graph_throughput.jpg       # Fig. 5: Concurrency scaling throughput
```

---

## 2. Compilation Instructions

### Option A: Using Standalone Tectonic (Fastest, zero TeX-Live installation required)
Tectonic automatically resolves packages and runs the necessary TeX passes in a single command:

```powershell
# Compile anonymous review manuscript
tools\tectonic\tectonic.exe revised_paper\main.tex -o revised_paper\

# Compile camera-ready manuscript
tools\tectonic\tectonic.exe revised_paper\main_camera_ready.tex -o revised_paper\
```

### Option B: Using Standard TeX Live / MiKTeX (`pdflatex`)
The document uses a self-contained `\begin{thebibliography}{18}` block ordered in strict sequential order of citation appearance. Run `pdflatex` twice to resolve cross-references and citation labels:

```bash
cd revised_paper
pdflatex main.tex
pdflatex main.tex

pdflatex main_camera_ready.tex
pdflatex main_camera_ready.tex
```

---

## 3. Key Enhancements Over Rejected Version

1. **Strict Double-Blind Compliance:** `main.tex` strips all author identities and college affiliations for anonymous review.
2. **Consecutive Citation Ordering & Resolved References:** Every manually hardcoded bracket (e.g. `[9], [11]`) was replaced with formal `\cite{...}` commands. Zero unresolved `[?]` or `??` labels exist.
3. **Exact 6-Page Budget:** Layout floats, equation line breaks, and table dimensions are tuned to eliminate trailing lines and fit strictly within the 6-page IEEE conference limit.
4. **Transparent Evaluation:** Distinguishes internal dispatch and scheduling performance (measured via mocked adapters at 3,891 tasks/s) from physical desktop/browser execution latency.
5. **Authentic Evidence Grounding:** All 11 metrics in Table I cite benchmark scripts executed in `backend/tests/performance/test_performance_benchmarks.py` and `backend/tests/reliability/test_success_rate_benchmark.py`.
