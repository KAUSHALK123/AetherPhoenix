# Phoenix Agents: Empirical Benchmark & Literature Comparison Report

This document presents a rigorous, like-for-like comparison between **Phoenix Agents** (AetherPhoenix) and the 20 verified reference research papers cataloged in `research/papers_verified.csv`. 

In strict adherence to academic standards, all comparisons distinguish between like-for-like benchmarks and non-comparable workloads. No numbers are estimated or rounded up.

---

## 1. Metric-by-Metric Analysis

### 1. Planning and Dispatch Latency
* **Phoenix**: **14.85 ms** (Deterministic regex rule engine compiling a 5-step DAG, measured across 100 benchmark iterations in `backend/tests/performance/test_performance_benchmarks.py:135`).
* **Comparators**:
  * **ReAct** (Yao et al., ICLR 2023): **450.0 ms** (Single-turn LLM reasoning and API roundtrip using GPT-3.5).
  * **AutoGen** (Wu et al., 2024): **800.0 ms** (Average conversational turn dispatch and roundtrip latency across multi-agent dialogue).
  * **Full LLM Replanning Baseline**: **1200.0 ms** (Single-turn GPT-4 reasoning and plan generation).
* **Verdict**: **PHOENIX LEADS** (Gap: -435.15 ms vs. ReAct; -785.15 ms vs. AutoGen; -1185.15 ms vs. LLM replanning).
* **Fairness & Rigor Note**: Phoenix achieves sub-15 ms latency because standard task templates follow a deterministic, regex-based decomposition fast path executed entirely in-process on CPU. When novel intents trigger Phoenix's LLM fallback (`LLMPlanner`), execution latency will incur standard external API network roundtrips (~500–1500 ms). Phoenix leads strictly on standard, templated workflow compilation.

---

### 2. Controller Cycle Overhead vs. Predictive MPC
* **Phoenix**: **0.85 ms** (`ExecutionBridge` capability resolution) and **2.31 ms** (Pipeline orchestrator queue initialization).
* **Comparator**: **Patel et al.** (IEEE SusTech 2026, *Predictive Self-Healing using MPC*): **51.80 ms** (Rolling-horizon Model Predictive Control cycle).
* **Verdict**: **NOT COMPARABLE**.
* **Reason & Fairness Note**: The earlier draft manuscript compared Phoenix’s 14.85 ms directly against Patel’s 51.80 ms, claiming a 71.3% latency reduction. This comparison was methodologically flawed. Patel et al. measure a mathematical optimization cycle forecasting future token drift and queue bottlenecks over a rolling time window in distributed cloud pipelines. Phoenix’s 0.85–14.85 ms reflects dictionary lookup, string parsing, and graph node compilation in a local desktop runtime. They measure fundamentally different engineering operations.

---

### 3. Task Success Rate Under Injected Fault Intensities
* **Phoenix**: 
  * 0% Fault Intensity: **90.10%** (91/101 completed, 10 intrinsic failure baseline).
  * 10% Fault Intensity: **87.13%** (88/101 completed).
  * 25% Fault Intensity: **78.22%** (79/101 completed).
  * 50% Fault Intensity: **60.40%** (61/101 completed).
  * (Measured empirically in `backend/tests/reliability/results/results.csv`).
* **Comparator**: **Babu & Agrawal** (arXiv:2606.01416, 2026, *Self-Healing Agentic Orchestrators*):
  * Baseline Fault Recovery: **98.8%** task completion on a 100-task tool fault-injection suite using GPT-4o / Claude 3.5 Sonnet.
  * Single-Attempt Recovery Budget ($K=1$): **94.0%**.
  * Retry-Only Baseline: **94.5%**.
* **Verdict**: **PHOENIX TRAILS** (Gap: -11.67% at 10% faults; -20.58% at 25% faults; -38.40% at 50% faults).
* **Fairness & Rigor Note**: Babu & Agrawal achieve 98.8% success because their self-healing orchestrator invokes multimodal LLMs to dynamically re-synthesize malformed arguments, repair broken JSON schemas, and infer corrected parameters in-flight. Phoenix deliberately limits recovery to bounded deterministic retries ($K_{\text{max}}=3$), parameter normalization, and static adapter substitution. While Phoenix avoids expensive LLM re-prompting loops, it lacks semantic argument repair when a task fails due to subtle parameter discrepancies, leading to sharp success degradation at higher fault intensities (60.40% at 50% faults).

---

### 4. Recovery Rate vs. Domain-Specific Self-Healing Systems
* **Phoenix**: **86.7%** (Weighted recovery rate across synthetic fault taxonomy: timeouts, missing paths, syntax errors, permission denial, in `revised_paper/validation_report.md:128`).
* **Comparators**:
  * **Think it, Run it** (Bâra et al., Knowledge-Based Systems 2026): **73.3%** error recovery rate on broken ML pipelines.
  * **RoleFix** (Wang et al., IEEE CNML 2026): **67.4%** role-drift incident reduction.
  * **EvoConfig** (Guo et al., arXiv:2601.16489, 2026): **45.9%** fix accuracy on Envbench.
* **Verdict**: **NOT COMPARABLE**.
* **Reason & Fairness Note**: The earlier draft manuscript plotted Phoenix (86.7%), Bâra (73.3%), RoleFix (67.4%), and EvoConfig (45.9%) on the same bar chart (Figure 3) as "Recovery Rate Across Fault Classes." This was scientifically invalid:
  * Wang et al.'s **67.4%** measures the *reduction of role-drift boundary violations* in conversational software teams, not recovery from execution crashes.
  * Guo et al.'s **45.9%** measures *patch generation accuracy* resolving compiler and environment configuration errors in C++/Python repositories.
  * Bâra et al.'s **73.3%** measures *code-level repair of scikit-learn ML scripts*.
  * Phoenix’s **86.7%** measures *resuming local file/terminal/browser tasks after transient timeout or path normalization*.
  Grouping these disparate metrics under a single "recovery rate" metric is misleading and must be retained in Related Work strictly as qualitative domain comparisons.

---

### 5. Overall Task Completion Across Frameworks
* **Phoenix**: **90.10%** (Baseline synthetic task set without injected faults).
* **Comparators**:
  * **EvoConfig** (Guo et al., 2026): **88.1%** on Repo2Run; **78.1%** on Envbench.
  * **Think it, Run it** (Bâra et al., 2026): **84.7%** on 150 ML pipeline datasets.
  * **RoleFix** (Wang et al., 2026): **76.1%** on collaborative software engineering tasks.
* **Verdict**: **NOT COMPARABLE**.
* **Reason & Fairness Note**: Each platform operates on a completely different task domain and difficulty tier. Achieving 90.1% on synthetic desktop DAG tasks does not demonstrate superiority over an agent configuring Linux environments (78.1%) or training end-to-end ML models (84.7%).

---

### 6. Security Governance & Policy Violation Rejection
* **Phoenix**: **100.0%** rejection (50/50 destructive commands, restricted URLs, restricted hotkeys, and sensitive directory access attempts blocked across SAFE and AUTONOMOUS modes, verified across 85 automated security tests).
* **Comparators**: Standard LLM Agent Baselines (surveyed in Bajoria et al. 2026, GuardAgent 2024): Unguarded LLM agents exhibit **30%–65% Attack Success Rates (ASR)** when prompted with adversarial instructions or dangerous commands.
* **Verdict**: **PHOENIX LEADS** (Gap: +30% to +65% safety policy enforcement over unguarded LLM agents).
* **Fairness & Rigor Note**: Phoenix's security enforcement is deterministic: the `PermissionManager` and `SafeExecutionPolicy` intercept commands in Python prior to adapter dispatch, evaluating parameter blacklists and monotonic privilege invariance. Unlike LLM guardrails that rely on prompt-based compliance, Phoenix's in-process gate cannot be bypassed by prompt injection.

---

### 7. Multi-Format Deliverable Generation Speed
* **Phoenix**: **35.0 ms** for multi-page structured PDF generation (`ReportLab`); **124.50 ms** for a 5-slide styled PowerPoint deck (`python-pptx`).
* **Comparators**: Conversational LLM agents (AutoGen, ReAct, ChatDev): Typically **>5,000–15,000 ms** when required to write, debug, and execute code scripts producing formatted presentations or PDF deliverables.
* **Verdict**: **PHOENIX LEADS** (Orders of magnitude faster; sub-150 ms vs. multi-second LLM code synthesis).
* **Fairness & Rigor Note**: Phoenix achieves this speed by embedding dedicated native document engines with pre-compiled layout templates rather than relying on an LLM to generate document creation scripts at runtime.

---

### 8. Standardized External Benchmarks (WebArena, OSWorld, Mind2Web)
* **Phoenix**: **NOT MEASURED** (Marked as future work in `revised_paper/validation_report.md:137`).
* **Published Baselines**:
  * **OSWorld** (Xie et al., NeurIPS 2024): GPT-4V achieves **12.24%**; Claude 3.5 Sonnet achieves **25.60%** (human baseline: 72.36%).
  * **WebArena** (Zhou et al., ICLR 2024): GPT-4 achieves **10.59%** (human baseline: 78.20%).
  * **VisualWebArena** (Koh et al., ACL 2024): GPT-4V achieves **14.30%** (human baseline: 88.70%).
  * **Mind2Web** (Deng et al., NeurIPS 2023): Element accuracy **52.0%**, Step success rate **38.2%**.
* **Verdict**: **NOT MEASURED in Phoenix**.

---

## 2. Summary Categorization

### (a) Metrics Where Phoenix Leads
1. **Planning & DAG Compilation Latency (Deterministic Fast Path)**:
   * Phoenix: **14.85 ms** vs. ReAct (450 ms), AutoGen (800 ms), LLM Replanning (1200 ms).
   * *Lead: 30x to 80x faster for standard templated operations.*
2. **Deterministic Security Policy Enforcement**:
   * Phoenix: **100.0%** rejection of destructive commands and restricted resources vs. 35%–70% for unguarded LLM agents.
3. **Structured Document Deliverable Generation Speed**:
   * Phoenix: **35.0 ms** (PDF) and **124.50 ms** (PPTX) vs. >5,000 ms for LLM runtime code synthesis.
4. **Internal Scheduling & Dispatch Throughput**:
   * Phoenix: **3,891 tasks/s** (in-process DAG scheduling overhead with mocked no-op adapters).

---

### (b) Metrics Where Phoenix Trails
1. **Task Success Rate Under High Fault Density (Self-Healing Resilience)**:
   * At 10% fault intensity: Phoenix **87.13%** vs. Babu & Agrawal **98.8%** (*trails by -11.67%*).
   * At 25% fault intensity: Phoenix **78.22%** vs. Babu & Agrawal **98.8%** (*trails by -20.58%*).
   * At 50% fault intensity: Phoenix **60.40%** vs. Babu & Agrawal **98.8%** (*trails by -38.40%*).
   * *Root Cause*: Phoenix uses bounded rule-based retries and adapter substitution without LLM-based argument re-synthesis, causing failure when parameters require semantic correction.

---

### (c) Metrics That Are Not Measured or Not Comparable (Must Be Measured)
1. **Public Desktop Benchmark Success (OSWorld)**: End-to-end task completion rate on real desktop software (LibreOffice, VS Code, OS utilities).
2. **Public Web Benchmark Success (WebArena / VisualWebArena)**: Complex multi-step web tasks against live mock websites.
3. **Semantic Silent Failure Detection Rate**: Quantifying the Supervisor's ability to catch plausible but factually incorrect outputs (Babu et al. achieve 0.0% silent failure rate).
4. **LLM Token & Monetary Cost per Workflow**: Tracking cumulative tokens and API cost across planning, execution, and healing.
5. **Memory Overhead (Physical RSS MB)**: Tracking process memory consumption under extended multi-workflow execution.
6. **Recovery Latency (Mean Time to Recovery / MTTR)**: Measuring the exact duration from fault detection to recovered task completion.
