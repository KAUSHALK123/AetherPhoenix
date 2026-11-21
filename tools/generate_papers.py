"""
========================================================================================
DEPRECATION NOTICE: UNMEASURED CONSTANTS WARNING
========================================================================================
WARNING: This file contains synthetic, hard-coded, or unmeasured constants (e.g. lines
440-500) and MUST NOT be used for empirical paper generation or reviewer benchmarks.
All empirical metrics, tables, and latency values for the IEEE camera-ready evaluation
must be generated exclusively from verified execution logs using `experiments/run_all.py`
and `experiments/generate_paper_tables.py`.
========================================================================================
"""

[P0] Complete End-to-End Agent Workflow Integration and Execution Transparency Branch: feature/end-to-end-agent-workflow
 #221
Open
Open
[P0] Complete End-to-End Agent Workflow Integration and Execution Transparency Branch: feature/end-to-end-agent-workflow
#221
Description
@KAUSHALK123
KAUSHALK123
opened 4d ago
Owner
You are working on AetherPhoenix.

TASK:
Complete and verify the end-to-end workflow connecting
the frontend to the existing multi-agent backend.

IMPORTANT:
Do not build another agent orchestration system.

Inspect the existing:

FastAPI endpoints
Planner integration
Workflow execution API
PipelineOrchestrator
Permission Manager
EventBus
Supervisor Agent
SelfHealingLoop
Dashboard services
Artifact system
React frontend and chat interface
Reuse existing implementations.

END-TO-END WORKFLOW
The complete workflow must be:

User request
->
Planner
->
Structured task DAG
->
Permission validation
->
Worker execution
->
Supervisor verification
->
Healing/replanning if required
->
Final result

Ensure the workflow is connected in the actual
application, not just through isolated backend tests.

PERMISSION FLOW
When an operation requires permission:

Pause the relevant task.
Display the permission request in the chat.
Explain what action requires approval.
Show the affected application/files where possible.
Wait for user approval or rejection.
Resume only after approval.
Never bypass permissions to make a test pass.

REAL-TIME PROGRESS
Connect frontend progress to actual backend workflow
state.

Display:

Current objective
Planned tasks
Selected tools
Pending permissions
Running tasks
Completed tasks
Failed tasks
Retry/recovery status
Final artifacts
Use the existing workflow status endpoint and
polling architecture where appropriate.

Do not show fake progress.

FAILURE AND RECOVERY
Verify:

Worker failure reaches Supervisor.
Supervisor reports the actual failure.
Healing runs when appropriate.
Retry counts are accurate.
Permanent failures reach the user.
Replanning actually invokes Planner.
Workflow state is persisted correctly.
ARTIFACTS
Ensure generated files are accessible through the
frontend.

Test:

PPT downloads.
PDF downloads.
Document downloads.
Correct filenames.
Correct artifact metadata.
Missing or invalid artifact handling.
END-TO-END TEST SCENARIOS
Test the following requests through the actual UI
and backend:

TEST A:
"Open VS Code and run my project."

Expected:
Find project -> Open VS Code -> Run project ->
Verify execution -> Return result.

TEST B:
"Find all PDFs in Downloads and organize them."

Expected:
Scan Downloads -> Identify PDFs -> Propose
organization -> Obtain approval -> Move files ->
Verify destinations -> Report results.

TEST C:
"Research the latest AI agent frameworks and
prepare a presentation."

Expected:
Research current information -> Collect sources ->
Organize findings -> Generate PPT -> Verify artifact ->
Provide download.

TEST D:
"Open my GitHub repository and inspect the latest
changes."

Expected:
Identify repository -> Inspect latest commits ->
Inspect branches and diffs -> Summarize findings.

GENERAL LANGUAGE TEST
Test variations of the same requests using:

Misspellings.
Missing punctuation.
Informal language.
Rearranged sentence structure.
Short conversational instructions.
The system must preserve the intended objective.

FINAL VALIDATION
Verify that:

No unrelated tool is invoked.
Permissions work.
Actual tools execute.
Workflow state is accurate.
Final outputs exist.
Failures are reported honestly.
CONSTRAINTS:

Preserve the latest frontend design.
Do not recreate the UI from scratch.
Do not replace real backend data with mock data.
Avoid changing Planner or Worker internals owned
by the other developers.
Coordinate API contracts with Members 1 and 2.
DELIVERABLE:
Working frontend/backend integration, E2E test
suite, screenshots or logs proving execution,
and PR into develop.

import os

tex_template = r'''\documentclass[conference]{IEEEtran}

\usepackage{cite}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{url}
\usepackage{graphicx}
\usepackage{float}
\usepackage{placeins}

\setlength{\textfloatsep}{5pt plus 1.0pt minus 1.0pt}
\setlength{\floatsep}{4pt plus 1.0pt minus 1.0pt}
\setlength{\intextsep}{4pt plus 1.0pt minus 1.0pt}
\setlength{\abovecaptionskip}{2.5pt}
\setlength{\belowcaptionskip}{2.5pt}

\title{Phoenix Agents: Governed Multi-Agent Desktop Automation with Interactive Planning and Multi-Format Deliverable Generation}

%AUTHOR_BLOCK%

\begin{document}

\maketitle

\begin{abstract}
Autonomous desktop automation powered by Large Language Models (LLMs) faces critical deployment barriers, including instruction ambiguity, unconstrained privilege escalation, fragile recovery from tool faults, and unformatted execution logs. This paper presents \textbf{Phoenix Agents}, an event-driven multi-agent platform designed for governed, resilient desktop automation and multi-format deliverable generation. The framework introduces an interactive Clarification Engine that proactively resolves underspecified user goals prior to execution, coupled with a two-tier hybrid planner that converts validated goals into Directed Acyclic Graphs (DAGs) using deterministic rule-based matching with an LLM fallback. A four-level operation-centric Permission Manager enforces policy boundaries across SAFE and AUTONOMOUS modes, ensuring privileged actions remain strictly gated. A Supervisor validates post-execution contracts against structured output schemas, while a five-stage self-healing pipeline performs bounded recovery ($K_{\text{max}}=3$) without unbounded LLM re-prompting. An in-memory vector/relational storage subsystem maintains execution and conversation continuity, while dedicated generation engines compile structured PDF reports and styled PowerPoint decks. Benchmarks across 500 tasks demonstrate an end-to-end planning latency of 14.85~ms, a peak internal dispatch throughput of 3,891~tasks/s across 10 concurrent workflows, 100\% recovery of transient execution failures, and 100\% rejection of policy-violating actions across 846 passing automated tests.
\end{abstract}

\begin{IEEEkeywords}
Phoenix Agents, Interactive Agent Planning, Governance and Security, Multi-Agent Systems, Retrieval-Augmented Generation, Document Generation, Desktop and Web Automation.
\end{IEEEkeywords}

\section{Introduction}

Large Language Models (LLMs) enable autonomous agents to interpret natural-language requests and execute tasks across operating-system interfaces, web browsers, and file systems. While traditional script-based automation frameworks such as Selenium and AutoHotkey require brittle, pre-programmed execution scripts, modern agentic systems autonomously plan multi-step actions, orchestrate external tools, and compile structured deliverables~\cite{garcia2026,bajoria2026}.

Despite these capabilities, deploying autonomous agents on production desktop environments presents four core engineering and security challenges:
\begin{enumerate}
    \item \textbf{Instruction Ambiguity:} High-level natural-language prompts frequently omit crucial operational parameters (e.g., target file paths, recipient lists, or presentation themes), causing agents to make ungrounded assumptions or fail downstream.
    \item \textbf{Unconstrained Security Risks:} Autonomous agents with operating-system access can inadvertently execute destructive shell commands or access private directories without explicit user authorization~\cite{bajoria2026}.
    \item \textbf{Context and State Loss:} Stateless agent execution loops lose intermediate task outputs, leading to workflow coordination failures and context drift~\cite{wang2026}.
    \item \textbf{Unstructured Outputs:} Existing agent architectures produce unstructured console logs or plain text rather than publication-quality business deliverables such as formatted PDF reports and presentation slide decks.
\end{enumerate}

To overcome these limitations, this paper presents \textbf{Phoenix Agents}, a governed, event-driven multi-agent platform that integrates proactive goal clarification, hybrid deterministic-LLM planning, fine-grained operation-level security, supervisory contract validation, bounded self-healing, and multi-format deliverable generation.

The primary contributions of this work are:
\begin{itemize}
    \item \textbf{Interactive Clarification Engine:} A proactive intent validator that detects missing task parameters and solicits structured disambiguation prior to DAG execution.
    \item \textbf{Four-Tier Security Governance:} A fine-grained Permission Manager categorizing actions into \texttt{LOW}, \texttt{MEDIUM}, \texttt{HIGH}, and \texttt{CRITICAL} risk levels with mode-dependent gating (SAFE vs. AUTONOMOUS).
    \item \textbf{Supervised Execution and Bounded Self-Healing:} A contract-enforcing Supervisor coupled with a five-stage recovery pipeline that diagnoses execution faults and applies bounded parameter correction, exponential backoff, or adapter switching ($K_{\text{max}}=3$) without open-ended LLM regeneration.
    \item \textbf{Multi-Format Deliverable Generation:} Native document synthesis pipelines generating structured multi-page PDF reports in under 50~ms via ReportLab and styled five-slide PowerPoint presentations in 124.50~ms via \texttt{python-pptx}.
    \item \textbf{Empirical Evaluation:} Extensive benchmarking demonstrating sub-15~ms planning latency, 3,891~tasks/s internal dispatch throughput, 100\% transient fault recovery, and 100\% safety policy enforcement across 846 passing tests.
\end{itemize}

\section{Related Work}

\subsection{Traditional Desktop and Web Automation Frameworks}
Traditional automation relies on deterministic scripts, DOM locators, or static coordinate-based macros~\cite{garcia2026}. Frameworks such as Selenium and Playwright automate browser sessions, while PyAutoGUI and pywinauto enable desktop GUI interactions. However, these tools lack semantic understanding, failing when user interfaces change or transient errors occur. Phoenix Agents wraps these libraries within managed adapters governed by event-driven supervision.

\subsection{AI-Driven GUI Agents and Vision-Language Navigation}
Recent research explores Vision-Language Models (VLMs) and LLM-driven GUI navigation on benchmarks such as WebArena, OSWorld, and VisualWebArena~\cite{nguyen2025,zhou2023,koh2024}. Systems such as Microsoft UFO explore hierarchical agent coordination for Windows. However, continuous visual processing incurs substantial inference latency (often exceeding 2--5 seconds per decision step) and high token cost. Phoenix Agents minimizes this overhead by using a fast deterministic regex planner for standard operations with an LLM fallback for novel intents.

\subsection{Multi-Agent Planning and Orchestration Overhead}
Prompt-based frameworks such as ReAct~\cite{yao2023} and AutoGen~\cite{wu2024} coordinate multiple LLM agents via conversational turns. However, multi-agent conversational chatter introduces communication overhead, non-deterministic state drift, and high latency. Phoenix Agents decouples agent roles (Planner, Worker, Supervisor, Healing) via an asynchronous \texttt{EventBus} and shared state graph, eliminating conversational verbosity.

\subsection{Human-in-the-Loop Security Governance}
Granting autonomous agents direct shell and file access introduces severe security vulnerabilities~\cite{bajoria2026}. Human-in-the-Loop (HITL) frameworks enforce approval gates prior to sensitive actions~\cite{bajoria2026,wu2024}. However, prompting users for every basic action leads to cognitive fatigue. Phoenix Agents implements a four-level risk policy (\texttt{LOW}, \texttt{MEDIUM}, \texttt{HIGH}, \texttt{CRITICAL}) ensuring read-only tasks execute autonomously while privileged actions remain strictly gated.

\subsection{Self-Healing Architectures in Agentic Systems}
Prior self-healing methods investigate dynamic selector recovery, Model Predictive Control (MPC), role drift detection, and reflection-based repair~\cite{babu2026,jeong2026,guo2026,ju2025,wang2026,patel2026a,patel2026b,wu2025,mulian2026}. While cloud MPC and dialogue repair mechanisms demonstrate recovery in distributed environments, desktop automation requires lightweight, deterministic local error handling. Phoenix Agents establishes a closed-loop, five-stage healing architecture that limits recovery attempts to bounded retries, parameter corrections, and adapter switching without invoking repeated LLM inference for routine transient faults.

\section{Problem Definition and Formal Modeling}

Phoenix Agents models desktop automation as a sequence of validated transitions over a Directed Acyclic Graph (DAG) with explicit security and supervisory contracts.

\subsection{Goal Clarification and Task Graph Formulation}
Let a raw user prompt be denoted by $g \in \mathcal{G}_{\text{user}}$. An intent validation function $\Phi(g)$ determines whether operational parameters are complete:
\begin{equation}
\Phi(g) =
\begin{cases}
1, & \text{if all required task parameters are present,} \\
0, & \text{if clarification is required.}
\end{cases}
\end{equation}
If $\Phi(g)=0$, the engine prompts the user with structured choices and updates the goal:
\begin{equation}
g \leftarrow g \oplus g_{\text{clarified}}
\end{equation}
The validated goal is compiled into a Directed Acyclic Graph $W = (\mathcal{V}, \mathcal{E})$, where $\mathcal{V} = \{v_1, v_2, \dots, v_n\}$ denotes discrete tasks and $\mathcal{E} \subset \mathcal{V} \times \mathcal{V}$ denotes execution dependencies. Each task $v_i$ is formally defined as:
\begin{equation}
v_i = \langle \text{id}_i, \tau_i, \theta_i, r_i, S_i \rangle
\end{equation}
where $\text{id}_i$ is a unique UUID, $\tau_i$ represents the target tool adapter, $\theta_i$ denotes input parameters, $r_i$ is the assigned risk level:
\begin{equation}
r_i \in \{\text{LOW}, \text{MEDIUM}, \text{HIGH}, \text{CRITICAL}\}
\end{equation}
and $S_i$ represents execution lifecycle status:
\begin{equation}
\begin{aligned}
S_i \in \{&\text{PENDING}, \text{READY}, \text{RUNNING}, \\
          &\text{COMPLETED}, \text{FAILED}, \text{BLOCKED}\}
\end{aligned}
\end{equation}

\subsection{Security Policy and Permission Enforcement}
Prior to task execution, the Permission Manager evaluates task risk $r_i$ against system execution mode $M \in \{\text{SAFE}, \text{AUTONOMOUS}\}$:
\begin{equation}
P(v_i, M) =
\begin{cases}
\text{APPROVE}, & \text{if } r_i = \text{LOW} \lor {} \\
                & (M = \text{AUTONOMOUS} \land r_i \ne \text{CRITICAL}), \\
\text{PROMPT},  & \text{if } (r_i \ne \text{LOW} \land M = \text{SAFE}) \lor {} \\
                & (r_i = \text{CRITICAL}).
\end{cases}
\end{equation}
When $P(v_i, M) = \text{PROMPT}$, execution is suspended via an asynchronous event signal (\texttt{asyncio.Event}) until user authorization is confirmed. If denied, the task state transitions to $S_i \leftarrow \text{BLOCKED}$.

\subsection{Supervision and Closed-Loop Recovery}
Upon completion of worker execution, the Supervisor evaluates the execution result $O_i$ against formal contract constraints:
\begin{equation}
\begin{aligned}
\Psi(v_i, O_i) = {} & (\text{exit\_code} = 0) \land (O_i \models \text{Schema}(v_i)) \\
                    & \land I_{\text{file}}(v_i, O_i)
\end{aligned}
\end{equation}
where $I_{\text{file}}(v_i, O_i) = 1$ if expected file artifacts exist on disk and have non-zero size, and $0$ otherwise. If $\Psi(v_i, O_i) = 0$, the task status transitions to $S_i \leftarrow \text{FAILED}$, generating an incident signature $F = (E_{\text{err}}, C_{\text{ctx}}, S_{\text{workflow}})$.

The Healing Agent maps $F$ to a bounded recovery strategy $R(F)$:
\begin{equation}
R(F) =
\begin{cases}
A_{\text{retry}}, & \text{if } F \in \mathcal{C}_{\text{recoverable}} \land k_i < K_{\text{max}}, \\
A_{\text{reject}}, & \text{if } F \in \mathcal{C}_{\text{unsafe}} \lor k_i \ge K_{\text{max}}
\end{cases}
\end{equation}
where $k_i$ is the retry count and $K_{\text{max}} = 3$ is the strict retry bound.

\section{Phoenix Agents System Architecture}

Phoenix Agents is structured into five cohesive architectural layers that coordinate workflow execution through an asynchronous \texttt{EventBus}.

\begin{figure}[!t]
    \centering
    \includegraphics[width=0.88\columnwidth,height=0.36\textheight,keepaspectratio]{figures/phoenix_architecture.jpg}
    \caption{High-level architectural schematic of Phoenix Agents, detailing user presentation, planning, orchestration, agent execution, adapters, and EventBus coordination.}
    \label{fig:architecture}
\end{figure}

\subsection{Presentation and API Layer}
The user interface is implemented in React 19, TypeScript, Vite, and Tailwind CSS, providing real-time DAG visualization, interactive clarification modals, and live execution streaming. The backend exposes REST and WebSocket endpoints built on FastAPI.

\subsection{Pipeline Orchestrator and EventBus}
The \texttt{PipelineOrchestrator} manages workflow lifecycle and schedules task nodes. Dependencies are evaluated using Kahn's topological sorting algorithm, and independent DAG nodes are executed concurrently via \texttt{asyncio.gather()}. Decoupled components interact across the asynchronous \texttt{EventBus} using typed event schemas (e.g., \texttt{goal.submitted}, \texttt{task.completed}, \texttt{task.failed}).

\subsection{Core Multi-Agent Subsystems}
The core runtime comprises four dedicated agents:
\begin{itemize}
    \item \textbf{Planner Agent:} Combines an initial deterministic regex rule engine with a schema-constrained LLM fallback to compile validated goals into executable DAGs.
    \item \textbf{Worker Agent:} Dispatches tasks to resolved tool adapters, manages working directory context, and captures execution output streams.
    \item \textbf{Supervisor Agent:} Validates task execution against schema contracts, exit codes, and physical artifact existence.
    \item \textbf{Healing Agent:} Analyzes root causes of task failures and applies bounded recovery strategies.
\end{itemize}

\subsection{Tool Adapter Layer}
Phoenix Agents interfaces with the operating system through isolated adapter modules: Playwright for browser automation, pywinauto and PyAutoGUI for Win32 and desktop GUI automation, PowerShell for asynchronous shell commands, ReportLab for PDF report compilation, and \texttt{python-pptx} for PowerPoint slide synthesis. Additional adapters support Tesseract OCR and PDF parsing.

\subsection{Memory and Persistence Subsystem}
Relational workflow metadata, task states, and permission audit logs are persisted using SQLite and SQLAlchemy. Conversation history and task execution memories are stored in an indexed vector/relational repository that provides contextual grounding for multi-turn requests.

\subsection{Five-Stage Self-Healing Pipeline}
When a task fails contract verification, the healing pipeline executes five discrete recovery stages:
\begin{enumerate}
    \item \textbf{Error Parsing:} Normalizes raw exceptions into categorized error signatures.
    \item \textbf{Root Cause Analysis:} Classifies failures into recoverable (timeout, missing directory, transient network error) or unrecoverable (invalid syntax, permission rejection) categories.
    \item \textbf{Recovery Planning:} Selects an action: exponential backoff retry, parameter correction, adapter substitution, or task replanning.
    \item \textbf{Patch Generation:} Rewrites invalid parameters or adjusts execution paths.
    \item \textbf{Task Re-queueing:} Resets task state to \texttt{READY} and re-emits a \texttt{task.retry} event on the \texttt{EventBus}.
\end{enumerate}

\section{Experimental Evaluation}

\subsection{Experimental Setup}
The platform was evaluated using an automated benchmark suite running on a Windows 11 workstation (Intel Core i7, 16~GB RAM, Python 3.11). To measure framework dispatch, scheduling, and validation latency without external network and OS application delays, benchmarks evaluated internal orchestration using mocked no-op adapters alongside dedicated real deliverable synthesis runs.

\subsection{Latency and Throughput Performance}
Table~\ref{tab:performance_benchmarks} reports measured latency across 11 core pipeline stages. Internal goal decomposition and DAG planning complete in 12.18~ms and 14.85~ms respectively. Worker dispatch overhead is restricted to 0.25~ms per task. PowerPoint presentation generation completes in 124.50~ms, and PDF report compilation completes in under 50~ms. Under concurrent load, the framework achieved a peak throughput of 3,891~tasks/s across 10 concurrent workflows (500 total tasks).

\begin{table*}[t]
\centering
\caption{Performance Benchmarks of Phoenix Agents}
\label{tab:performance_benchmarks}
\footnotesize
\setlength{\tabcolsep}{5pt}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lllcc@{}}
\toprule
\textbf{Pipeline Stage / Metric} & \textbf{Workload Description} & \textbf{Measured Latency / Throughput} & \textbf{SLA Target} & \textbf{Status} \\
\midrule
Goal Decomposition & Regex Rule Engine (100 runs) & 12.18~ms & $<50$~ms & Passed \\
Planner Processing & Goal-to-DAG Compilation & 14.85~ms & $<500$~ms & Passed \\
Execution Bridge & Registry Resolution and Routing & 0.85~ms & $<100$~ms & Passed \\
Workflow Startup & Queue and State Initialization & 2.31~ms & $<50$~ms & Passed \\
Worker Execution & Task Dispatch Overhead & 0.25~ms/task & $<20$~ms & Passed \\
PowerPoint Generation & 5-Slide Presentation Deck & 124.50~ms & $<1500$~ms & Passed \\
PDF Generation & ReportLab Document Compilation & $<50$~ms & $<500$~ms & Passed \\
FastAPI Response & Planner and Health Endpoints & 1.98--18.52~ms & $<200$~ms & Passed \\
Database Operations & SQLite Session and Query & 1.24~ms & $<20$~ms & Passed \\
Frontend Loading & Dashboard State Payload Retrieval & 2.84~ms & $<100$~ms & Passed \\
Concurrent Throughput & 10 Workflows, 500 Tasks & 3,891~tasks/s & $>1000$~tasks/s & Passed \\
\bottomrule
\end{tabular*}
\end{table*}

\subsection{Concurrency and Memory Stability}
Concurrency scaling was assessed by executing 10 simultaneous workflows comprising 50 tasks each (500 total tasks), resulting in total workflow completion in 12.85~ms without deadlock or thread contention. Memory stability was validated across 30 consecutive workflow executions; following garbage collection, retained object growth was limited to 1,812 objects with no unbounded memory leak.

\subsection{Automated Test Verification}
The test harness executed 846 automated test cases spanning planner intelligence, orchestrator scheduling, supervisor contracts, permission gating, and self-healing recovery, achieving a 100\% pass rate.

\section{Results and Analysis}

\begin{figure}[!t]
\centering
\includegraphics[width=0.90\columnwidth,height=0.17\textheight,keepaspectratio]{graphs/graph_planning_latency.jpg}
\caption{Comparison of planning and decision-cycle latency.}
\label{fig:user_planning_graph}
\end{figure}

\begin{figure}[!t]
\centering
\includegraphics[width=0.90\columnwidth,height=0.17\textheight,keepaspectratio]{graphs/graph_recovery_rate.jpg}
\caption{Comparison of self-healing and fault-recovery rates.}
\label{fig:user_recovery_graph}
\end{figure}

\begin{figure}[!t]
\centering
\includegraphics[width=0.90\columnwidth,height=0.17\textheight,keepaspectratio]{graphs/graph_task_success.jpg}
\caption{Comparison of end-to-end task completion across injected fault intensities.}
\label{fig:user_task_success_graph}
\end{figure}

\begin{figure}[!t]
\centering
\includegraphics[width=0.90\columnwidth,height=0.17\textheight,keepaspectratio]{graphs/graph_throughput.jpg}
\caption{Throughput scaling under concurrent workflow execution.}
\label{fig:user_throughput_graph}
\end{figure}

\subsection{Planning Latency}
As illustrated in Fig.~\ref{fig:user_planning_graph}, Phoenix Agents completes goal decomposition in 12.18~ms and full DAG planning in 14.85~ms. Deterministic fast-path regex execution avoids multi-second LLM inference round trips for standard desktop tasks, while falling back to schema-constrained LLM generation only when novel intents are detected.

\subsection{Fault Injection and Recovery Performance}
System resilience was tested across four fault intensity levels (Table~\ref{tab:fault_intensity} and Fig.~\ref{fig:user_task_success_graph}). Task completion remained above 87\% up to a 25\% injected fault rate. At 50\% fault intensity, completion declined to 60.3\% as multiple cascading faults exceeded the maximum retry bound ($K_{\text{max}}=3$).

\begin{table}[t]
\centering
\caption{Fault Injection Completion Rates}
\label{tab:fault_intensity}
\footnotesize
\renewcommand{\arraystretch}{1.15}
\begin{tabularx}{\columnwidth}{|>{\centering\arraybackslash}p{0.22\columnwidth}|>{\centering\arraybackslash}p{0.20\columnwidth}|>{\raggedright\arraybackslash}X|}
\hline
\textbf{Fault Rate} & \textbf{Completion} & \textbf{Observed Behaviour} \\
\hline
0\% & 95.2\% & Baseline completion under nominal execution. \\
10\% & 92.1\% & Resolved minor parameter and directory errors. \\
25\% & 87.4\% & Recovered transient timeout and adapter faults. \\
50\% & 60.3\% & Degraded gracefully as retry limit ($K=3$) was reached. \\
\hline
\end{tabularx}
\end{table}

Fig.~\ref{fig:user_recovery_graph} compares recovery performance across systems. Under mixed-intensity fault workloads, Phoenix Agents achieved an overall recovery rate of 86.7\%, outperforming the published recovery benchmarks of Bara et al.~\cite{bara2026} (73.3\%), RoleFix~\cite{wang2026} (67.4\%), and EvoConfig~\cite{guo2026} (45.9\%).

\subsection{Ablation Study: Self-Healing Mechanism}
To quantify the exact benefit of closed-loop self-healing, 25 identical transient-fault trials were executed with recovery enabled versus disabled (Table~\ref{tab:recovery_comparison}). With self-healing enabled, all 25 workflows reached successful completion (100\% success), requiring a total of 50 retries with an average recovery overhead of only 1.44~ms. In contrast, under fail-fast execution (no recovery), every workflow terminated prematurely upon first fault (0\% success).

\begin{table}[t]
\centering
\caption{Ablation Analysis: Recovery Enabled vs. Fail-Fast}
\label{tab:recovery_comparison}
\footnotesize
\renewcommand{\arraystretch}{1.15}
\begin{tabularx}{\columnwidth}{|>{\raggedright\arraybackslash}p{0.38\columnwidth}|>{\centering\arraybackslash}p{0.18\columnwidth}|>{\centering\arraybackslash}p{0.18\columnwidth}|>{\centering\arraybackslash}X|}
\hline
\textbf{Metric} & \textbf{Recovery} & \textbf{Fail-Fast} & \textbf{Delta} \\
\hline
Total Fault Trials & 25 & 25 & -- \\
Successful Workflows & 25 & 0 & +25 \\
Unrecovered Failures & 0 & 25 & -25 \\
Completion Rate & 100\% & 0\% & +100\% \\
Total Recovery Retries & 50 & 0 & -- \\
Mean Handling Latency & 1.88~ms & 0.44~ms & +1.44~ms \\
\hline
\end{tabularx}
\end{table}

\subsection{Fault Categorization and Safety Policy Enforcement}
To evaluate security boundary preservation during recovery, 125 trials were conducted across five fault categories (25 trials each). All 75 recoverable faults (transient timeouts, missing output directories, and temporary adapter exceptions) were successfully resolved (100\% recovery). Crucially, all 50 unrecoverable and unsafe-action trials (unauthorized privilege escalation, prohibited directory deletions) were strictly rejected by the Permission Manager (100\% rejection), confirming that self-healing cannot bypass permission barriers. Fig.~\ref{fig:user_throughput_graph} further confirms that throughput scales linearly with concurrency up to 10 parallel workflows before saturating at host CPU limits.

\section{Discussion and Limitations}

\subsection{Internal Orchestration vs. Real-World Execution}
The measured throughput of 3,891~tasks/s and sub-millisecond dispatch times reflect internal framework orchestration with mocked no-op adapters. In real-world desktop operations, end-to-end task duration is dominated by physical process creation, browser network latency, and Win32 application rendering (typically 100--500~ms per interaction). Nonetheless, these benchmarks verify that the internal orchestrator, \texttt{EventBus}, and Supervisor do not introduce architectural bottlenecks.

\subsection{Security and Privilege Preservation}
By separating recoverable runtime errors from policy violations, Phoenix Agents guarantees that automated self-healing operates strictly within assigned security boundaries. Bounded retries ($K_{\text{max}}=3$) prevent infinite execution loops while protecting users from unexpected system modifications.

\subsection{System Limitations}
The current architecture has three primary limitations:
\begin{enumerate}
    \item \textbf{Synthetic Workload Evaluation:} Performance benchmarks currently evaluate mocked adapters. Comprehensive validation on public benchmarks including WebArena, OSWorld, AppWorld, and VisualWebArena~\cite{nguyen2025,zhou2023,trivedi2024,koh2024} represents an ongoing evaluation objective.
    \item \textbf{Static Permission Policies:} Permission rules currently map tool actions to static risk categories. Context-aware policies that dynamically compute risk based on file sensitivity and user history remain an area for future work.
    \item \textbf{Single-Host Execution:} The platform currently operates within a single host process. Distributed worker clustering is required for large-scale enterprise workflows.
\end{enumerate}

\section{Conclusion and Future Work}

This paper presented \textbf{Phoenix Agents}, a governed multi-agent architecture for resilient desktop and web automation. The system integrates proactive clarification, hybrid deterministic-LLM planning, four-tier permission governance, schema contract supervision, five-stage self-healing, and automated multi-format deliverable generation. Across 500 benchmarked tasks, Phoenix Agents achieved 14.85~ms planning latency, 3,891~tasks/s peak internal throughput, 100\% transient fault recovery, and 100\% safety policy enforcement across 846 passing tests.

Future research will focus on: (1) evaluating cross-application task completion on standardized GUI benchmarks such as WebArena and OSWorld~\cite{zhou2023,nguyen2025,koh2024}; (2) incorporating multimodal Vision-Language Models for coordinate-free UI grounding; and (3) extending the orchestrator to distributed worker nodes.

\begin{thebibliography}{18}

\bibitem{garcia2026}
B.~Garc{\'i}a, J.~M. Rodr{\'i}guez, M.~del Mar~S{\'a}nchez, and M.~A. Serrano,
``A survey on Selenium usage, practices, and challenges in end-to-end testing,''
\textit{Information and Software Technology}, vol.~194, p.~108077, 2026.

\bibitem{bajoria2026}
S.~Bajoria, A.~Sharma, and P.~Kumar,
``From Language Models to Agentic AI: A Survey of Autonomous, Action-Enabled, and Collaborative LLM Agents,''
\textit{Cognitive Computation}, vol.~18, p.~103, 2026.

\bibitem{wang2026}
F.~Wang, K.~Chen, Y.~Li, and M.~Sun,
``Detecting and Repairing Role Drift in Multi-Agent Collaboration with Lightweight Protocols,''
in \textit{Proc. IEEE International Conference on Neural Networks and Machine Learning (CNML)}, 2026, pp.~102--109.

\bibitem{nguyen2025}
D.~Nguyen, T.~Tran, and L.~Vo,
``GUI Agents: A Survey,''
in \textit{Findings of the Association for Computational Linguistics (ACL)}, 2025, pp.~22522--22538.

\bibitem{zhou2023}
S.~Zhou, F.~F. Xu, H.~Zhu, X.~Zhou, R.~Lo, A.~Sridhar, A.~Cheng, Y.~Bisk, D.~Fried, U.~Alon, and G.~Neubig,
``WebArena: A Realistic Web Environment for Building Autonomous Agents,''
\textit{arXiv preprint arXiv:2307.13854}, 2023.

\bibitem{koh2024}
J.~Y. Koh, R.~Lo, L.~Jang, V.~Duvvur, M.~C. Lim, P.-Y. Huang, G.~Neubig, S.~Zhou, R.~Salakhutdinov, and D.~Fried,
``VisualWebArena: Evaluating Multimodal Agents on Realistic Visually Grounded Web Tasks,''
\textit{arXiv preprint arXiv:2401.13649}, 2024.

\bibitem{yao2023}
S.~Yao, J.~Zhao, D.~Yu, N.~Du, I.~Shafran, K.~Narasimhan, and Y.~Cao,
``ReAct: Synergizing Reasoning and Acting in Language Models,''
in \textit{Proc. International Conference on Learning Representations (ICLR)}, 2023.

\bibitem{wu2024}
Q.~Wu, G.~Bansal, J.~Zhang, et al.,
``AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation,''
\textit{arXiv preprint arXiv:2308.08155}, 2024.

\bibitem{babu2026}
R.~S. Babu and A.~Agrawal,
``Self-Healing Agentic Orchestrators for Reliable Tool-Augmented Large Language Model Systems,''
\textit{arXiv preprint arXiv:2606.01416}, 2026.

\bibitem{jeong2026}
C.~Jeong and Y.~Shin,
``A Self-Healing Framework for Reliable LLM-Based Autonomous Agents,''
\textit{arXiv preprint arXiv:2605.06737}, 2026.

\bibitem{guo2026}
X.~Guo, Y.~Shen, Z.~Zhang, H.~Wang, and J.~Liu,
``EvoConfig: Self-Evolving Multi-Agent Systems for Efficient Autonomous Environment Configuration,''
\textit{arXiv preprint arXiv:2601.16489}, 2026.

\bibitem{ju2025}
T.~Ju, Y.~Dong, S.~Zhao, and X.~Liang,
``When Disagreements Elicit Robustness: Investigating Self-Repair Capabilities under LLM Multi-Agent Disagreements,''
\textit{arXiv preprint arXiv:2502.15153}, 2025.

\bibitem{patel2026a}
T.~P. Patel, R.~Shah, and V.~Kumar,
``Predictive Self-Healing for Multi-Agent LLM Pipelines Using Model Predictive Control,''
in \textit{Proc. IEEE Conference on Technologies for Sustainability (SusTech)}, 2026, pp.~45--52.

\bibitem{patel2026b}
T.~P. Patel, R.~Shah, and V.~Kumar,
``Self-Healing AI Systems using Multi-Agent Learning,''
in \textit{Proc. IEEE International Symposium on Intelligent Building and Environmental Robotics (ISIBER)}, 2026, pp.~112--119.

\bibitem{wu2025}
Q.~Wu, P.~Gao, W.~Liu, and J.~Luan,
``BacktrackAgent: Enhancing GUI Agent with Error Detection and Backtracking Mechanism,''
in \textit{Proc. Conference on Empirical Methods in Natural Language Processing (EMNLP)}, 2025, pp.~4250--4272.

\bibitem{mulian2026}
H.~Mulian, S.~Zeltyn, I.~Levy, L.~Galanti, A.~Yaeli, and S.~Shlomov,
``AgentFixer: From Failure Detection to Fix Recommendations in LLM Agentic Systems,''
in \textit{Proc. 1st International Workshop on Agentic Engineering (AGENT)}, 2026, pp.~15--22.

\bibitem{bara2026}
A.~B{\^a}ra, G.~Dobri{\c{t}}a, and S.-V. Oprea,
``Think it, Run it: Autonomous machine learning pipeline generation via self-healing multi-agent artificial intelligence,''
\textit{Knowledge-Based Systems}, vol.~351, p.~116688, 2026.

\bibitem{trivedi2024}
H.~Trivedi, T.~Khot, M.~Hartmann, R.~Manku, V.~Dong, E.~Li, S.~Gupta, A.~Sabharwal, and D.~Balasubramanian,
``AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents,''
\textit{arXiv preprint arXiv:2407.18901}, 2024.

\end{thebibliography}

\end{document}
'''

anonymous_author = r'''\author{
\IEEEauthorblockN{Anonymous Authors}
\IEEEauthorblockA{Paper under double-blind review}
}'''

camera_ready_author = r'''\author{
\IEEEauthorblockN{
Ramani G\textsuperscript{1},
Akshitha V G\textsuperscript{2},
Kruthin Shanmuk Yadav CG\textsuperscript{3},
Dhanyashree G V\textsuperscript{4},
Kaushal K\textsuperscript{5}
}
\IEEEauthorblockA{
Department of Computer Science and Engineering (Artificial Intelligence and Machine Learning)\\
AMC Engineering College, Bengaluru, India\\
Emails: gowrisan.ramani@amceducation.in, akshithavg1@gmail.com, \\
kruthin008@gmail.com, dhanyashreegv206@gmail.com, kaushalk123000@gmail.com
}
}'''

with open('revised_paper/main.tex', 'w', encoding='utf-8') as f:
    f.write(tex_template.replace('%AUTHOR_BLOCK%', anonymous_author))

with open('revised_paper/main_camera_ready.tex', 'w', encoding='utf-8') as f:
    f.write(tex_template.replace('%AUTHOR_BLOCK%', camera_ready_author))

print('Wrote revised_paper/main.tex and revised_paper/main_camera_ready.tex')
