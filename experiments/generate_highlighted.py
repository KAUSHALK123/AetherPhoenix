import re

with open("main.tex", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Preamble: Add \usepackage{xcolor} and \newcommand{\chg}[1]{{\color{blue}#1}}
preamble_target = r"\usepackage{placeins}"
preamble_replacement = r"""\usepackage{placeins}
\usepackage{xcolor}
\newcommand{\chg}[1]{{\color{blue}#1}}"""
text = text.replace(preamble_target, preamble_replacement, 1)

# 2. Abstract highlighted text
old_abs = r"Empirical evaluation across controlled fault injections demonstrates that the pipeline recovered 100.0\% of recoverable-by-design faults, safely rejected all non-recoverable faults, and achieved an overall recovery rate of 60.0\% (outperforming naive retry and fail-fast baselines), with an average recovery handling latency of 11.99~ms on mocked adapters."
new_abs = r"\chg{" + old_abs + r"}"
text = text.replace(old_abs, new_abs, 1)

# 3. Contributions:
old_contrib2 = r"achieving millisecond-scale handling latency ($T_R = 11.99$~ms, $T_{\text{rec}} = 12.00$~ms on mocked adapters; 1.89~ms on real filesystem)."
new_contrib2 = r"achieving millisecond-scale handling latency \chg{($T_R = 11.99$~ms, $T_{\text{rec}} = 12.00$~ms on mocked adapters; 1.89~ms on real filesystem)}."
text = text.replace(old_contrib2, new_contrib2, 1)

old_contrib4 = r"\textbf{Empirical Verification Across 125 Controlled Trials:} Benchmark evaluation demonstrating complete recovery on recoverable faults, zero safety violations, and significant advantage over naive retry and fail-fast baselines."
new_contrib4 = r"\chg{" + old_contrib4 + r"}"
text = text.replace(old_contrib4, new_contrib4, 1)

# 4. Related Work:
old_rw1 = r"\textbf{Foundations in Classic Fault Tolerance:} Phoenix Agents builds upon classical principles of dependable computing. Avi\v{z}ienis et al.~\cite{avizienis2004} formalized the fundamental taxonomy of faults, errors, and failures, establishing the necessity of error detection and system recovery boundaries. In high-availability systems, Gray and Siewiorek~\cite{gray1991} demonstrated that transient software faults can be overcome through modular process isolation and bounded restart mechanisms. In enterprise software architecture, Nygard~\cite{nygard2018} formalized stability patterns including circuit breakers, bounded retries, and exponential backoff to prevent cascading failures. For multi-step distributed operations, Garcia-Molina and Salem~\cite{garciamolina1987} introduced Sagas to structure compensations without long-lived locks. While bounded retries and exponential backoff are standard industry mechanisms, the contribution of Phoenix Agents lies in combining an in-process, safety-checked, rule-classified recovery pipeline with monotonic permission validation and its empirical evaluation for multi-agent desktop automation."
new_rw1 = r"\chg{" + old_rw1 + r"}"
text = text.replace(old_rw1, new_rw1, 1)

old_wu = r"Wu et al.~\cite{wu2025} developed BacktrackAgent, introducing verifier, judger, and reflector modules for GUI error detection and backtracking; they reported GUI-agent step latencies of 1.374 to 1.938~s per step."
new_wu = r"\chg{" + old_wu + r"}"
text = text.replace(old_wu, new_wu, 1)

old_diff = r"mean $T_R = 11.99$~ms, $T_{\text{rec}} = 12.00$~ms"
new_diff = r"\chg{mean $T_R = 11.99$~ms, $T_{\text{rec}} = 12.00$~ms}"
text = text.replace(old_diff, new_diff, 1)

# Table I (Comparison table)
old_tab1 = r"""\begin{table}[t]
\centering
\caption{Architectural Comparison of Agent Recovery Frameworks}
\label{tab:comparison}
\footnotesize
\setlength{\tabcolsep}{2pt}
\begin{tabularx}{\columnwidth}{p{0.22\columnwidth}p{0.25\columnwidth}p{0.25\columnwidth}X}
\toprule
\textbf{Approach} & \textbf{Recovery Method} & \textbf{Fault Scope} & \textbf{Safety Guard} \\
\midrule
Babu~\cite{babu2026} & LLM reflection & Tool / orchestration & Budget limit \\
Jeong~\cite{jeong2026} & LLM reliability & Hallucination / exec. & Reliability check \\
Patel~\cite{patel2026b} & Multi-agent learn & Infra / system & Coordinated acts \\
Wu~\cite{wu2025} & Backtracking & GUI action errors & Pre-rewrite check \\
\textbf{Phoenix} & \textbf{Deterministic 5-stage} & \textbf{5-class taxonomy} & \textbf{Policy rejection} \\
\bottomrule
\end{tabularx}
\end{table}"""

new_tab1 = r"""\begin{table}[t]
\centering
\caption{\chg{Architectural Comparison of Agent Recovery Frameworks}}
\label{tab:comparison}
\footnotesize
\setlength{\tabcolsep}{2pt}
\begin{tabularx}{\columnwidth}{p{0.22\columnwidth}p{0.25\columnwidth}p{0.25\columnwidth}X}
\toprule
\chg{\textbf{Approach}} & \chg{\textbf{Recovery Method}} & \chg{\textbf{Fault Scope}} & \chg{\textbf{Safety Guard}} \\
\midrule
\chg{Babu~\cite{babu2026}} & \chg{LLM reflection} & \chg{Tool / orchestration} & \chg{Budget limit} \\
\chg{Jeong~\cite{jeong2026}} & \chg{LLM reliability} & \chg{Hallucination / exec.} & \chg{Reliability check} \\
\chg{Patel~\cite{patel2026b}} & \chg{Multi-agent learn} & \chg{Infra / system} & \chg{Coordinated acts} \\
\chg{Wu~\cite{wu2025}} & \chg{Backtracking} & \chg{GUI action errors} & \chg{Pre-rewrite check} \\
\chg{\textbf{Phoenix}} & \chg{\textbf{Deterministic 5-stage}} & \chg{\textbf{5-class taxonomy}} & \chg{\textbf{Policy rejection}} \\
\bottomrule
\end{tabularx}
\end{table}"""
text = text.replace(old_tab1, new_tab1, 1)

# Stage 4 risk invariance
old_risk = r"subject to monotonic risk invariance ($\text{risk}(\tau'_i) \le \text{risk}(\tau_i)$)"
new_risk = r"\chg{" + old_risk + r"}"
text = text.replace(old_risk, new_risk, 1)

# Section IV.A
old_iva = r"Execution within each worker occurs on Python's single-threaded cooperative event loop; per-task state is isolated in scoped dictionaries, and failure-signature count read-modify-write sequences execute atomically without intervening \texttt{await} yields."
new_iva = r"\chg{" + old_iva + r"}"
text = text.replace(old_iva, new_iva, 1)

# Section IV.C/D
old_ivd = r"Dynamic adapter substitution was evaluated on $n=25$ faults with mocked adapters through \texttt{ToolRegistry} (verified in unit tests in \texttt{test\_adapter\_substitution.py}); real adapters were not evaluated in the 125-fault benchmark suite."
new_ivd = r"\chg{" + old_ivd + r"}"
text = text.replace(old_ivd, new_ivd, 1)

# Section V.A Evaluation Disclosure
old_disc = r"and (iv) Tool/Adapter faults were initially rejected (0/25, recoverable-class 50/75) because adapter error signatures were not registered in \texttt{ErrorParser}; after registering real adapter error signatures emitted by codebase adapters, the class reached 25/25. Additionally, two shared-state defects were resolved: \texttt{SelfHealingLoop.current\_state} was replaced with per-task state, and \texttt{RetryEngine.\_failure\_signature\_counts} was re-keyed by (workflow\_id, task\_id, signature) with atomic updates."
new_disc = r"\chg{" + old_disc + r"}"
text = text.replace(old_disc, new_disc, 1)

# Table II
old_tab2_r3 = r"Tool/Adapter Failure ($n=25$) & Recoverable & 100.0\% (25/25) & 0.0\% (0/25) & [86.7, 100.0]\% & 0.0\% (0/25) & 0.0\% (0/25) \\"
new_tab2_r3 = r"\chg{Tool/Adapter Failure ($n=25$)} & \chg{Recoverable} & \chg{100.0\% (25/25)} & \chg{0.0\% (0/25)} & \chg{[86.7, 100.0]\%} & \chg{0.0\% (0/25)} & \chg{0.0\% (0/25)} \\"
text = text.replace(old_tab2_r3, new_tab2_r3, 1)

old_tab2_r6 = r"All Recoverable Faults ($n=75$) & Recoverable Aggregate & 100.0\% (75/75) & 0.0\% (0/75) & [95.1, 100.0]\% & 33.3\% (25/75) & 0.0\% (0/75) \\"
new_tab2_r6 = r"\chg{All Recoverable Faults ($n=75$)} & \chg{Recoverable Aggregate} & \chg{100.0\% (75/75)} & \chg{0.0\% (0/75)} & \chg{[95.1, 100.0]\%} & \chg{33.3\% (25/75)} & \chg{0.0\% (0/75)} \\"
text = text.replace(old_tab2_r6, new_tab2_r6, 1)

old_tab2_r7 = r"All Non-Recoverable Faults ($n=50$) & Safety Aggregate & 0.0\% (0/50) & 100.0\% (50/50) & [92.9, 100.0]\% & 0.0\% (0/50) & 0.0\% (0/50) \\"
new_tab2_r7 = r"\chg{All Non-Recoverable Faults ($n=50$)} & \chg{Safety Aggregate} & \chg{0.0\% (0/50)} & \chg{100.0\% (50/50)} & \chg{[92.9, 100.0]\%} & \chg{0.0\% (0/50)} & \chg{0.0\% (0/50)} \\"
text = text.replace(old_tab2_r7, new_tab2_r7, 1)

old_tab2_r8 = r"Overall Fault Suite ($n=125$) & Entire Suite & 60.0\% (75/125) & 40.0\% (50/125) & [51.2, 68.2]\% & 20.0\% (25/125) & 0.0\% (0/125) \\"
new_tab2_r8 = r"\chg{Overall Fault Suite ($n=125$)} & \chg{Entire Suite} & \chg{60.0\% (75/125)} & \chg{40.0\% (50/125)} & \chg{[51.2, 68.2]\%} & \chg{20.0\% (25/125)} & \chg{0.0\% (0/125)} \\"
text = text.replace(old_tab2_r8, new_tab2_r8, 1)

old_note2 = r"For overall rows, recovered (75) + rejected (50) = 125."
new_note2 = r"\chg{" + old_note2 + r"}"
text = text.replace(old_note2, new_note2, 1)

# Eq (6)
old_eq6 = r"SR_{\text{rec}} = \frac{N_{\text{recovered,rec}}}{N_{\text{injected,rec}}} \times 100 = \frac{75}{75} \times 100 = 100.0\%"
new_eq6 = r"\chg{" + old_eq6 + r"}"
text = text.replace(old_eq6, new_eq6, 1)

old_eq6_txt = r"with a Wilson 95\% confidence interval of [95.1\%, 100.0\%] ($n=75$). Phoenix successfully remediated 25/25 Timeout faults (exponential backoff), 25/25 Missing Resource faults (directory synthesis and path correction), and 25/25 Tool/Adapter faults (dynamic adapter substitution via \texttt{ToolRegistry})."
new_eq6_txt = r"\chg{" + old_eq6_txt + r"}"
text = text.replace(old_eq6_txt, new_eq6_txt, 1)

# Eq (8)
old_eq8 = r"SR = \frac{N_{\text{recovered}}}{N_{\text{injected}}} \times 100 = \frac{75}{125} \times 100 = 60.0\%"
new_eq8 = r"\chg{" + old_eq8 + r"}"
text = text.replace(old_eq8, new_eq8, 1)

old_eq8_txt = r"with a Wilson 95\% confidence interval of [51.2\%, 68.2\%] ($n=125$). Because 50 faults represent non-recoverable security and unmapped errors, the theoretical maximum recovery rate on this benchmark is 60.0\% (75/125)."
new_eq8_txt = r"\chg{" + old_eq8_txt + r"}"
text = text.replace(old_eq8_txt, new_eq8_txt, 1)

# Section V.C Worked examples
old_vc = r"""\subsection{Worked Examples from Real Execution Traces}
To illustrate the diagnostic execution flow, single-fault traces were captured with telemetry enabled (\texttt{PHOENIX\_TRACE=1}). In a Missing Resource scenario, a file task failed with \texttt{[Errno 2] No such file or directory: 'report.json'}; Stage~1 parsed the error into \texttt{FILE\_NOT\_FOUND}, Stage~2 analyzed root cause as \texttt{RESOURCE} (confidence 0.95), Stage~3 selected \texttt{MISSING\_DIRECTORY\_RECOVERY}, Stage~4 synthesized directory parameters, and Stage~5 executed retry ($k=1$), yielding supervisor status \texttt{PASSED} ($S \leftarrow \text{COMPLETED}$). For non-recoverable cases, an unauthorized command (\texttt{del /f /s /q C:\textbackslash Windows\textbackslash System32}) failed with \texttt{Access is denied}, parsed as \texttt{PERMISSION\_DENIED} (confidence 0.98), was blocked by monotonic policy check at Stage~3 ($k=0$), and halted as \texttt{FAILED}. An unmapped driver exception (\texttt{Fatal ASIC microcode parity divergence}) received confidence 0.30, mapped to \texttt{NO\_VIABLE\_RECOVERY}, and was terminated as \texttt{ESCALATED}."""

new_vc = r"""\subsection{\chg{Worked Examples from Real Execution Traces}}
\chg{To illustrate the diagnostic execution flow, single-fault traces were captured with telemetry enabled (\texttt{PHOENIX\_TRACE=1}). In a Missing Resource scenario, a file task failed with \texttt{[Errno 2] No such file or directory: 'report.json'}; Stage~1 parsed the error into \texttt{FILE\_NOT\_FOUND}, Stage~2 analyzed root cause as \texttt{RESOURCE} (confidence 0.95), Stage~3 selected \texttt{MISSING\_DIRECTORY\_RECOVERY}, Stage~4 synthesized directory parameters, and Stage~5 executed retry ($k=1$), yielding supervisor status \texttt{PASSED} ($S \leftarrow \text{COMPLETED}$). For non-recoverable cases, an unauthorized command (\texttt{del /f /s /q C:\textbackslash Windows\textbackslash System32}) failed with \texttt{Access is denied}, parsed as \texttt{PERMISSION\_DENIED} (confidence 0.98), was blocked by monotonic policy check at Stage~3 ($k=0$), and halted as \texttt{FAILED}. An unmapped driver exception (\texttt{Fatal ASIC microcode parity divergence}) received confidence 0.30, mapped to \texttt{NO\_VIABLE\_RECOVERY}, and was terminated as \texttt{ESCALATED}.}"""
text = text.replace(old_vc, new_vc, 1)

# Section V.D baseline
old_naive = r"Across all 75 recoverable faults, Naive Retry recovers 25/75 (33.3\%, Wilson 95\% CI: [23.7\%, 44.6\%]). On the 50 non-recoverable faults, Naive Retry dispatches $3 \times 50 = 150$ retries before terminal failure (0.0\% safe rejection). Because adapters were bypassed during these faulted trials, these represent retry dispatches rather than executed unauthorized actions. Overall recovery is 20.0\% (25/125, Wilson CI: [13.9\%, 27.9\%])."
new_naive = r"\chg{" + old_naive + r"}"
text = text.replace(old_naive, new_naive, 1)

# Section V.E Latency
old_lat_intro = r"Table~\ref{tab:latency_breakdown} reports latency distributions across demarcated intervals:"
new_lat_intro = r"\chg{" + old_lat_intro + r"}"
text = text.replace(old_lat_intro, new_lat_intro, 1)

old_tr_txt = r"(\texttt{run\_step0\_latency.py}, lines 126--128). Across $n=2250$ observations (30 repeats of 75 recovered trials), $T_R$ recorded a mean of 11.99~ms, SD of 7.04~ms, median of 11.36~ms, and IQR of 10.81~ms. $T_R$ measures software recovery dispatch and strategy generation only; it does not await the exponential backoff sleep delay ($\Delta t = 2^k \times 1.0\,\text{s}$). When the real backoff sleep is awaited, wall-clock duration recorded a mean of 1010.50~ms (median 1010.35~ms)."
new_tr_txt = r"\chg{" + old_tr_txt + r"}"
text = text.replace(old_tr_txt, new_tr_txt, 1)

old_trec_txt = r"(lines 123--136). Across $n=2250$ observations, $T_{\text{rec}}$ recorded a mean of 12.00~ms, SD of 7.04~ms, median of 11.36~ms, and IQR of 10.81~ms."
new_trec_txt = r"\chg{" + old_trec_txt + r"}"
text = text.replace(old_trec_txt, new_trec_txt, 1)

old_fs_txt = r"(lines 170--174), recording a mean of 1.89~ms, SD of 1.79~ms, median of 1.67~ms, and IQR of 0.38~ms ($n=100$)."
new_fs_txt = r"\chg{" + old_fs_txt + r"}"
text = text.replace(old_fs_txt, new_fs_txt, 1)

old_ff_txt = r"Delimited across lines 157--159, recording a mean of 0.0007~ms (median 0.0006~ms, $n=3750$)."
new_ff_txt = r"\chg{" + old_ff_txt + r"}"
text = text.replace(old_ff_txt, new_ff_txt, 1)

# Table III
old_tab3 = r"""\begin{table}[t]
\centering
\caption{Empirical Latency Breakdown (Tracing OFF)}
\label{tab:latency_breakdown}
\footnotesize
\begin{tabularx}{\columnwidth}{Xcccc}
\toprule
\textbf{Metric} & \textbf{Mean} & \textbf{SD} & \textbf{Med.} & \textbf{IQR} \\
\midrule
$T_R$ (Stages 1--5) & 11.99 & 7.04 & 11.36 & 10.81 \\
$T_{\text{rec}}$ (Dispatch--Done) & 12.00 & 7.04 & 11.36 & 10.81 \\
$T_{\text{rec}}$ (Real FS) & 1.89 & 1.79 & 1.67 & 0.38 \\
$T_{\text{no\_rec}}$ (Fail-Fast) & 0.001 & 0.001 & 0.001 & 0.000 \\
\bottomrule
\multicolumn{5}{p{0.95\columnwidth}}{\textsuperscript{*}Note: Latencies in ms. Ranges: $T_R$ [1.27, 84.26], $T_{\text{rec}}$ [1.27, 84.27], Real FS [1.23, 19.28], Fail-Fast [0.0005, 0.069]. Mocked $n=2250$, Real FS $n=100$, Fail-Fast $n=3750$.}
\end{tabularx}
\end{table}"""

new_tab3 = r"""\begin{table}[t]
\centering
\caption{\chg{Empirical Latency Breakdown (Tracing OFF)}}
\label{tab:latency_breakdown}
\footnotesize
\begin{tabularx}{\columnwidth}{Xcccc}
\toprule
\chg{\textbf{Metric}} & \chg{\textbf{Mean}} & \chg{\textbf{SD}} & \chg{\textbf{Med.}} & \chg{\textbf{IQR}} \\
\midrule
\chg{$T_R$ (Stages 1--5)} & \chg{11.99} & \chg{7.04} & \chg{11.36} & \chg{10.81} \\
\chg{$T_{\text{rec}}$ (Dispatch--Done)} & \chg{12.00} & \chg{7.04} & \chg{11.36} & \chg{10.81} \\
\chg{$T_{\text{rec}}$ (Real FS)} & \chg{1.89} & \chg{1.79} & \chg{1.67} & \chg{0.38} \\
\chg{$T_{\text{no\_rec}}$ (Fail-Fast)} & \chg{0.001} & \chg{0.001} & \chg{0.001} & \chg{0.000} \\
\bottomrule
\multicolumn{5}{p{0.95\columnwidth}}{\chg{\textsuperscript{*}Note: Latencies in ms. Ranges: $T_R$ [1.27, 84.26], $T_{\text{rec}}$ [1.27, 84.27], Real FS [1.23, 19.28], Fail-Fast [0.0005, 0.069]. Mocked $n=2250$, Real FS $n=100$, Fail-Fast $n=3750$.}}
\end{tabularx}
\end{table}"""
text = text.replace(old_tab3, new_tab3, 1)

# Concurrency & Adversarial
old_audit = r"0 state-clobbering events (overwriting shared workflow attributes) and 0 failure-signature collisions (clobbering retry counters) were observed, confirming that per-task state tracking and atomic retry bookkeeping preserve determinism under concurrency."
new_audit = r"\chg{" + old_audit + r"}"
text = text.replace(old_audit, new_audit, 1)

old_adv = r"In an adversarial safety test evaluating 25 distinct destructive or privilege-escalating commands (e.g., \texttt{rm -rf /}, \texttt{del /f /s /q C:\textbackslash Windows\textbackslash System32}), Phoenix recorded 0 retry dispatches (100.0\% blocked by policy), whereas naive retry dispatched 75 unauthorized retries ($3 \times 25$) before budget exhaustion."
new_adv = r"\chg{" + old_adv + r"}"
text = text.replace(old_adv, new_adv, 1)

# Scenario Section V.G
old_vg = r"""\subsection{Real Adapters, Larger Graphs, and Additional Faults}
Beyond the synthetic suite, three scenario experiments evaluated broader coverage:
(1)~\textbf{Real-Adapter Scenarios (S2, $n=10$ each):} On host adapters under live OS conditions, subprocess timeout achieved 10/10 recovery (100.0\%, Wilson CI: [72.2\%, 100.0\%], mean $T_R = 8.39$~ms). File locked by another process (0/10), missing paths outside the sandbox (0/10), unreachable browser ports (0/10), and read-only directories (0/10) were all safely rejected as non-recoverable permission/policy violations (10/10 safe rejection each, [72.2\%, 100.0\%]).
(2)~\textbf{Larger Workflow Graphs (S3, 300 trials):} 10-task and 20-task graphs (linear and branching) were evaluated with one recoverable fault injected at first, middle, and last task positions ($n=25$ each). All settings achieved 100.0\% completion (25/25, Wilson CI: [86.7\%, 100.0\%], 300/300 overall), with mean $T_R$ scaling mildly from 2.23~ms to 5.47~ms and total workflow duration from 2.25~ms to 5.52~ms without dependency deadlocks.
(3)~\textbf{Additional Fault Types (S4, $n=10$ each):} Transient connection refused achieved 10/10 recovery (100.0\%, CI: [72.2\%, 100.0\%]), and unknown adapter names achieved 10/10 recovery via substitution (100.0\%, CI: [72.2\%, 100.0\%]). Operating system disk full, locked files, and malformed JSON payloads were safely rejected (10/10 each, [72.2\%, 100.0\%]) under the $\le 0.30$ confidence rule."""

new_vg = r"""\subsection{\chg{Real Adapters, Larger Graphs, and Additional Faults}}
\chg{Beyond the synthetic suite, three scenario experiments evaluated broader coverage:
(1)~\textbf{Real-Adapter Scenarios (S2, $n=10$ each):} On host adapters under live OS conditions, subprocess timeout achieved 10/10 recovery (100.0\%, Wilson CI: [72.2\%, 100.0\%], mean $T_R = 8.39$~ms). File locked by another process (0/10), missing paths outside the sandbox (0/10), unreachable browser ports (0/10), and read-only directories (0/10) were all safely rejected as non-recoverable permission/policy violations (10/10 safe rejection each, [72.2\%, 100.0\%]).
(2)~\textbf{Larger Workflow Graphs (S3, 300 trials):} 10-task and 20-task graphs (linear and branching) were evaluated with one recoverable fault injected at first, middle, and last task positions ($n=25$ each). All settings achieved 100.0\% completion (25/25, Wilson CI: [86.7\%, 100.0\%], 300/300 overall), with mean $T_R$ scaling mildly from 2.23~ms to 5.47~ms and total workflow duration from 2.25~ms to 5.52~ms without dependency deadlocks.
(3)~\textbf{Additional Fault Types (S4, $n=10$ each):} Transient connection refused achieved 10/10 recovery (100.0\%, CI: [72.2\%, 100.0\%]), and unknown adapter names achieved 10/10 recovery via substitution (100.0\%, CI: [72.2\%, 100.0\%]). Operating system disk full, locked files, and malformed JSON payloads were safely rejected (10/10 each, [72.2\%, 100.0\%]) under the $\le 0.30$ confidence rule.}"""
text = text.replace(old_vg, new_vg, 1)

# Limitations
old_lim1 = r"(1)~\textbf{No Blind Held-Out Evaluation:} Although a held-out template structure was prepared, no blind held-out evaluation was conducted; the 50-fault auxiliary set served strictly as an internal diagnostic suite to detect classification and policy defects."
new_lim1 = r"\chg{" + old_lim1 + r"}"
text = text.replace(old_lim1, new_lim1, 1)

old_lim2 = r"(2)~\textbf{Tool/Adapter Failure Handling:} Dynamic adapter substitution was evaluated on $n=25$ faults with mocked adapters through \texttt{ToolRegistry} (verified in unit tests in \texttt{test\_adapter\_substitution.py}); real adapters were not evaluated in the 125-fault benchmark suite."
new_lim2 = r"\chg{" + old_lim2 + r"}"
text = text.replace(old_lim2, new_lim2, 1)

old_lim3 = r"(3)~\textbf{Absence of LLM Baseline:} An empirical head-to-head comparison against an active LLM orchestrator was not conducted due to lack of local API credentials; literature step latencies~\cite{wu2025} reflect GUI-agent execution rather than isolated recovery handling."
new_lim3 = r"\chg{" + old_lim3 + r"}"
text = text.replace(old_lim3, new_lim3, 1)

# Conclusion
old_concl1 = r"(1)~\textbf{Millisecond-Scale Recovery Handling:} The pipeline achieved mean $T_R = 11.99$~ms and total duration $T_{\text{rec}} = 12.00$~ms on mocked adapters, with real-filesystem repair averaging 1.89~ms."
new_concl1 = r"\chg{" + old_concl1 + r"}"
text = text.replace(old_concl1, new_concl1, 1)

old_concl2 = r"(2)~\textbf{Fault Recovery on Recoverable Faults:} Across 75 recoverable-by-design faults, Phoenix recovered 75/75 (100.0\%), successfully repairing 25/25 Timeout, 25/25 Missing Resource, and 25/25 Tool/Adapter faults."
new_concl2 = r"\chg{" + old_concl2 + r"}"
text = text.replace(old_concl2, new_concl2, 1)

old_concl4 = r"(4)~\textbf{Overall Recovery and Baseline Contrast:} Overall recovery across all 125 faults was 60.0\% (75/125), substantially exceeding Naive Retry (20.0\%) and Fail-Fast (0.0\%). The Phoenix advantage over naive retry comes from Missing Resource and Tool/Adapter faults, while naive retry matches Phoenix on Timeouts."
new_concl4 = r"\chg{" + old_concl4 + r"}"
text = text.replace(old_concl4, new_concl4, 1)

# References
for b in ["avizienis2004", "gray1991", "nygard2018", "garciamolina1987"]:
    pattern = r"(\\bibitem\{" + b + r"\}.*?)(?=\\bibitem|\\end\{thebibliography\})"
    def repl(m):
        return r"\chg{" + m.group(1).strip() + r"}" + "\n\n"
    text = re.sub(pattern, repl, text, flags=re.DOTALL)

with open("main_highlighted.tex", "w", encoding="utf-8") as f:
    f.write(text)

print("main_highlighted.tex generated successfully.")
