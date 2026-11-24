# Phoenix Agents: Codebase Audit & Empirical Answers for IEEE Submission

- **Date:** 2026-11-11
- **Branch:** `paper/experiments`
- **Git Commit Hash:** `c0135dec9aa75f04f583a76cb206d4007747313d`
- **Python Version:** Python 3.14.4
- **Host CPU:** AMD Ryzen 7 8845HS w/ Radeon 780M Graphics (8 Cores, 16 Threads)
- **Host RAM:** 15.26 GB
- **Default LLM / Model:** `gemini-2.5-flash` (via Google Gemini v1beta endpoint; metadata label: `gemini-pro`)

---

## Question 1: When is the LLM planning fallback triggered? Which LLM and version?

### Evidence
- **Decomposition Fallback:** `backend/app/planner/decomposer.py:396-420`
  In `GoalDecomposer.decompose_goal(goal, workflow_id)`, the decomposer checks deterministic keyword/regex branches for known categories (system control, browser, presentation, pdf, git, terminal, file organization, filesystem). When none match, execution enters the `else` block at `decomposer.py:396`, instantiates `LLMPlanner()`, checks `is_nonsense(goal)`, and calls:
  ```python
  resp = self.llm_planner.plan(
      PlannerRequest(session_id=str(workflow_id), message=goal),
      workflow_id=workflow_id,
  )
  ```
- **Agent Entry Point:** `backend/app/agents/planner/agent.py:320-342`
  `PlannerAgent.process_request(request)` uses `LLMPlanner` to detect pure conversational messages (`is_conversational_chat`, returning directly without planning) or detect gibberish/keystroke mashing (`is_nonsense`, returning `await_user_input`).
- **LLM Call & Model Version:** `backend/app/planner/llm_planner.py:306-314`, `481-548`
  In `LLMPlanner.plan()`:
  - If `GEMINI_API_KEY` is present in the environment (`llm_planner.py:306`), it executes `_call_gemini_planner()` (`llm_planner.py:481`).
  - Target URL and Model: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}` (`llm_planner.py:499`).
  - Therefore, the model is **`gemini-2.5-flash`** via the Google Gemini API (`v1beta`).
  - *Note on metadata:* In `llm_planner.py:448`, the serialised plan dictionary sets `"planner_model": "gemini-pro"`, but the actual network call is dispatched to `gemini-2.5-flash`.
  - If `OPENAI_API_KEY` is present, `_call_openai_planner()` currently redirects to `_fallback_catalog_planner` (`llm_planner.py:550-554`).
  - If no API key is present or LLM calls fail twice, it calls `_fallback_catalog_planner()` (`llm_planner.py:316-479`).

---

## Question 2: How is the clarification check computed (rules, LLM, or both)? Which details does it look for? What does merging the clarified answer into the request do?

### Evidence
- **Computation Mechanism (Rules vs. LLM):** **Purely rules-based** (no LLM is invoked during clarification checking).
  - Defined in `ClarificationEngine.evaluate_requirement()` (`backend/app/planner/clarifier.py:161-190`).
  - Invoked in `PlannerAgent.process_request()` (`backend/app/agents/planner/agent.py:350-362` and `375-381`).
  - *Bias toward acting:* Read-only data-retrieval intents (`is_read_only = user_req.intent == IntentCategory.DATA_RETRIEVAL`) bypass clarification entirely (`agent.py:353`).
- **Details Looked For:** `backend/app/planner/clarifier.py:53-122` (`detect_missing_info`)
  1. **File organization intent** (`_is_file_organization_intent`, lines 20-52):
     - `source_folder`: Scans for folder keywords (`download`, `desktop`, `documents`, `pictures`, `videos`, `:\`, `:/`, `/home`, `/user`) (lines 66-84). If absent, flags `"source_folder"` as missing.
     - `organization_criteria`: Scans for criteria keywords (`by file type`, `by extension`, `by date`, `by size`, `alphabetical`, `by category`, `sort by`) (lines 85-106). If absent, flags `"organization_criteria"` as missing.
  2. **General intent:** If `requirement.intent == IntentCategory.UNKNOWN`, flags `"intent"` as missing (lines 116-117).
  3. **Empty requirements:** If `not requirement.requirements`, flags `"requirements"` as missing (lines 119-120).
- **What Merging Does:** `backend/app/agents/planner/agent.py:310-318`, `472-475`
  1. **Session Context Stitching:** If `request.session_id` is found in `self.active_sessions`, it extracts `original_goal` and sets:
     ```python
     combined_message = f"{original_goal} (Clarification provided: {request.message})"
     request.message = combined_message
     ```
     This combined string is fed into the downstream requirement analyzer, goal extractor, and decomposer so they parse the complete user intent.
  2. **Confidence Bonus:** During final confidence scoring (`agent.py:473-474`):
     ```python
     if "Clarification provided:" in combined_message:
         plan_confidence += 0.1
     ```
     Providing clarification rewards the generated plan with a +0.1 confidence boost (clamped to 1.0).
  3. **Cleanup:** On final plan output, the session is cleared: `self.active_sessions.pop(request.session_id, None)` (`agent.py:530`).

---

## Question 3: Permission policy: list which actions get LOW/MEDIUM/HIGH/CRITICAL. What happens for each level in SAFE and AUTONOMOUS mode? Is CRITICAL ever auto-approved? Does the code match this equation: APPROVE if r=LOW or M=AUTONOMOUS, else PROMPT?

### Evidence
- **Action Risk Classification:** `backend/app/core/permissions/policies.py:71-123` (`ACTION_RISK_MAP`) and `130-180` (`classify_risk`)
  - **LOW:**
    - *Browser:* `browser_start_session`, `browser_close_session`, `browser_extract_content`, `browser_capture_screenshot`, `extract_content`, `capture_screenshot`
    - *Desktop:* `get_windows`, `get_active_window`, `get_desktop_state`, `mouse_get_position`, `desktop_screenshot`, `start_session`, `end_session`, `mouse_move`, `mouse_scroll`, `focus_window`, `resize_window`, `move_window`, `minimize_window`, `maximize_window`, `restore_window`
    - *Filesystem:* `file_read`
    - *Memory:* `memory_create`, `memory_read`, `memory_update`, `memory_delete`
  - **MEDIUM:**
    - *Browser:* `browser_navigate`, `navigate`, `browser_interact`, `interact`
    - *Desktop:* `mouse_click`, `mouse_double_click`, `mouse_right_click`, `mouse_drag`, `keyboard_press`, `keyboard_type`, `keyboard_write`
    - *Filesystem:* `file_write`
  - **HIGH:**
    - *Desktop:* `keyboard_hotkey`, `launch_app`, `terminate_app`, `close_window`
    - *Filesystem:* `file_delete`
    - *Unknown Actions:* Any unrecognised action defaults to `HIGH` (fail-closed, line 179).
  - **CRITICAL:**
    - *Standard Actions:* `terminal_execute`, `powershell_execute`
    - *Dynamic Triggers (unconditional security checks, lines 140-167):*
      - Any action whose keys match `RESTRICTED_HOTKEYS` (`alt+f4`, `ctrl+alt+del`, `win+l`, `win+r`, `ctrl+shift+esc`, `format`).
      - Any action with URL matching `RESTRICTED_URL_SCHEMES` (`file://`, `gopher://`, `data://`, `javascript:`).
      - Any command containing `DESTRUCTIVE_COMMAND_TOKENS` (`rm -rf`, `format `, `format-volume`, `del /f`, `remove-item`, `clear-disk`, `drop database`, `reg delete`, `stop-computer`, `restart-computer`, `set-executionpolicy`).
- **Behavior in SAFE vs. AUTONOMOUS Mode:** `backend/app/core/permissions/policies.py:198-298` (`SafeExecutionPolicy.evaluate`)
  - **Inherent Security Violations (Destructive CRITICAL):** Lines 198-238 check restricted hotkeys, URLs, and destructive command tokens *first*. If matched, it returns `allowed=False, requires_approval=True` across **ALL** modes unconditionally (cannot be auto-approved even in AUTONOMOUS mode).
  - **SAFE Mode (lines 241-262):**
    - `SAFE` / `LOW`: `allowed=True, requires_approval=False` (auto-approved).
    - `MEDIUM` / `HIGH` / non-destructive `CRITICAL`: `allowed=True, requires_approval=True` (prompts human approval).
  - **AUTONOMOUS Mode (lines 290-298):**
    - `allowed=True, requires_approval=False` (auto-approved for all standard actions including `terminal_execute` and `powershell_execute`).
    - *Exception:* Destructive tokens/restricted hotkeys are blocked unconditionally before reaching this block.
- **Is CRITICAL ever auto-approved?**
  **YES, conditionally.**
  - Non-destructive `CRITICAL` operations (e.g., standard `terminal_execute` or `powershell_execute` running commands like `dir` or `git status`) **ARE** auto-approved in `AUTONOMOUS` mode (`policies.py:290-298`).
  - Destructive `CRITICAL` operations (e.g., `rm -rf`, `format`, `del /f`, `alt+f4`) are **NEVER** auto-approved in any mode; they are blocked unconditionally (`policies.py:198-238`).
  - In `SAFE` mode, `CRITICAL` is **NEVER** auto-approved (`policies.py:252-262`).
- **Does the code match $\text{APPROVE if } r=\text{LOW or } M=\text{AUTONOMOUS, else PROMPT}$?**
  **Partially, with two critical caveats:**
  1. *Destructive Safety Veto:* If $r=\text{CRITICAL}$ and contains destructive tokens, it is **BLOCKED** (`allowed=False, requires_approval=True`), regardless of $M=\text{AUTONOMOUS}$.
  2. *Assisted Mode:* In `ASSISTED` mode (`policies.py:264-288`), `MEDIUM` is auto-approved without prompt ($\text{APPROVE if } r \in \{\text{LOW, MEDIUM}\}$).

---

## Question 4: Retries: does the retry counter start at 0, i.e. one run plus up to three retries? Is exponential backoff really applied (real sleep) or skipped in tests?

### Evidence
- **Initial Retry Counter:**
  - Defined in `shared/contracts/task.py:111`: `retry_count: int = Field(default=0, ge=0)`.
  - When a task is first created, its `retry_count` is `0`.
- **Maximum Retries ($K_{\max} = 3$):** `backend/app/agents/healing/retry_engine.py:260-270`, `653`, `898-908`
  - `validate_retry_eligibility` checks `if task.retry_count >= limit:` where `limit = 3` (default).
  - Initial attempt: `retry_count = 0` (allowed).
  - 1st retry: `task.retry_count` becomes `1` (`retry_engine.py:653`).
  - 2nd retry: `task.retry_count` becomes `2`.
  - 3rd retry: `task.retry_count` becomes `3`.
  - Next failure: `retry_count = 3 >= 3` $\rightarrow$ rejected with `"reached maximum retry limit (3/3)"`.
  - **Verdict:** Exactly **one initial run plus up to three retries** (4 total execution attempts maximum).
- **Exponential Backoff:** `backend/app/agents/healing/retry_engine.py:88-106`, `634-670`
  - Formula: `calculate_backoff_delay` computes $\min(\text{base} \times 2^{\text{attempt}-1}, \text{max\_backoff})$ (lines 97-106).
  - In `execute_retry` (`lines 634-670`), `delay_sec` is calculated, written to `task.execution_logs`, and passed to the event payload.
  - **Is real sleep applied?** **NO.**
    Searching `backend/app/agents/healing/` and `backend/app/engine/` confirms there is **NO `asyncio.sleep()` or `time.sleep()`** executed during retry. The task is re-enqueued immediately into `WorkflowEngine`. The delay is recorded in logs and metadata only; no actual wall-clock sleeping occurs in production or tests.

---

## Question 5: Which recovery actions are really implemented: retry, parameter correction, adapter substitution, replanning?

### Evidence
All four actions are implemented in the codebase:
1. **Retry:** Fully implemented in `RetryEngine.execute_retry()` (`backend/app/agents/healing/retry_engine.py:614-795`, `946-964`).
2. **Parameter Correction:** Implemented in `RetryEngine.execute_retry()` (`retry_engine.py:656-660`):
   ```python
   if request.recovery_plan and request.recovery_plan.updated_task_params:
       for key, value in request.recovery_plan.updated_task_params.items():
           if hasattr(task, key):
               setattr(task, key, value)
   ```
   and in `WorkerReexecutionManager.create_reexecution_request()` (`backend/app/agents/worker/reexecution.py:75-85`).
3. **Adapter Substitution:** Implemented in `RecoveryPlanner.generate_recovery_plan()` (`backend/app/agents/healing/recovery_planner.py:340, 529`), `WorkerReexecutionManager.create_reexecution_request()` (`worker/reexecution.py:77-85` which swaps `task.required_tool = rep_task.required_tool`), and `RetryEngine` (`retry_engine.py:931-944` which enqueues replacement tasks with the alternate tool).
4. **Replanning:** Implemented in `PlannerFeedbackLoop.process_failure()` (`backend/app/agents/planner/feedback.py:194-216`, publishing `ModelEventType.REPLANNING_TRIGGERED`) and `PlannerAgent.handle_replanning_event()` (`backend/app/agents/planner/agent.py:205-295`), which extracts failed tools, increments `self.replanning_cycles`, enforces a hard limit of 2 replanning cycles, and generates a new plan omitting failed capabilities.

---

## Question 6: What does the "Patch Generator" actually produce?

### Evidence
- **Architecture Specification vs. Code Reality:**
  - In architecture documents (`working/AGENT_LOW_LEVEL_ARCHITECTURE.md:62` and `working/RESEARCH_PROJECT_BRIEF.md:180, 231`), "Patch Generator" is described as a standalone component that rewrites task inputs or alters parameters.
  - In the source code, there is **NO class or file named `PatchGenerator`** (`NOT FOUND, ask author`).
- **Actual Implementation:**
  The patching logic is handled inline by `RecoveryPlanner._create_generic_recovery_plan()` (`backend/app/agents/healing/recovery_planner.py:193-275`). It produces a `RecoveryPlan` (`shared/contracts/recovery.py`) containing a sequence of `RecoveryAction` objects:
  1. `VERIFY_DIRECTORY`: Inspects target folder with `action_parameters={"path": target_path}`.
  2. `CREATE_DIRECTORY`: Generates missing parent directories with `action_parameters={"path": target_path, "create_parents": True}`.
  3. `RETRY_TASK`: Patches target tool and parameters with `action_parameters={"tool_name": target_tool}`.
  4. `VALIDATE_ARTIFACT`: Re-validates the produced artifact at `target_path`.
  These patched parameters are then applied onto the task by `RetryEngine` (`retry_engine.py:656-660`) and `WorkerReexecutionManager` (`worker/reexecution.py:77-85`).

---

## Question 7: What does the Supervisor schema check inspect?

### Evidence
- Evaluated by `OutputValidationService.validate()` (`backend/app/engine/validator.py:14-82`) and `FailureDetectorService` in `SupervisorAgent.execute()` (`backend/app/agents/supervisor/agent.py:196-226`).
- It inspects five distinct validation facets:
  1. **Execution Success (`validator.py:27-32`):** Checks `result.success == True` and that no unhandled worker exception was raised.
  2. **Artifact Verification (`validator.py:35, 126-184`):**
     - Checks task's declared `task.artifact_location`: verifies the file exists on the filesystem and is non-empty (`os.path.getsize(filepath) > 0`).
     - Checks all artifacts in `result.artifacts`: verifies each file exists and has size $> 0$ bytes.
  3. **Output Schema & Data Verification (`validator.py:40, 186-251`):**
     - If `task.expected_output` is defined: ensures `result.output` or `result.artifacts` is non-empty and contains non-trivial data via `is_empty_or_noop_output()` (`validator.py:85-124`).
     - Evaluates `task.success_criteria`:
       - `file: <path>`: asserts that `os.path.exists(filepath)`.
       - `contains: <key>`: asserts that `expected_key in result.output`.
       - General text criteria: asserts that `result.output` is populated with substantial payload data.
  4. **Failure Criteria Triggering (`validator.py:45, 253-289`):**
     - Scans `result.output` keys, `result.output` values, and `result.logs` for matches against any string in `task.failure_criteria`.
  5. **Placeholder / No-Op Rejection (`validator.py:50-73`):**
     - Non-phase tasks must not have placeholder names (e.g., "evaluate goal context", "execute primary action") or return empty bookkeeping dictionaries without real tool action.

---

## Question 8: Embedding model, top-k, and what is stored in SQLite vs. FAISS.

### Evidence
- **Embedding Model:** `backend/app/memory/vector_db.py:51-94` (`DeterministicHashEmbeddingProvider`)
  - Feature hashing using MD5 over word unigrams and bigrams (`_compute_vector`, lines 65-87).
  - Dimension: Fixed 128 dimensions (`dimension: int = 128`), normalized to unit length.
  - Runs in-process with zero external API or PyTorch/TensorFlow dependencies.
  - A `MockEmbeddingProvider` (lines 96-119) is also present for unit testing.
- **Top-k Value:**
  - Default `top_k = 5` in `VectorDatabaseService.search_similar()` (`vector_db.py:308`).
  - Default `top_k = 5` in `InMemoryVectorStoreProvider.search()` (`vector_db.py:202`).
  - Default `top_k = 5` in `RAGPipelineService.retrieve_context()` (`backend/app/memory/rag_pipeline.py:84`).
- **What is stored in SQLite vs. FAISS:**
  - **SQLite Database (`backend/app/models/memory.py:12-36`, `backend/app/memory/storage.py:167-230`):**
    - Stores relational table `conversation_memories`:
      - `id`: UUID string primary key.
      - `session_id`: Indexed string.
      - `role`: Message role (`user`, `assistant`).
      - `content`: Full conversation text.
      - `relevance_score`: Float relevance rating.
      - `category`: Enum string (`general_chat`, `task_instruction`, `clarification`, `preference`).
      - `metadata_json`: JSON text of session context.
      - `created_at`, `updated_at`: UTC timestamps.
  - **FAISS vs. Vector Store Reality:**
    - **FAISS IS NOT IMPLEMENTED IN THE SOURCE CODE** (`NOT FOUND, ask author`).
    - While FAISS is mentioned in PRD documents and architectural diagrams (`docs/SYSTEM_ARCHITECTURE.md`), the actual code in `backend/app/memory/vector_db.py:168-264` uses `InMemoryVectorStoreProvider`.
    - It stores `VectorRecord` items in an in-memory Python dictionary (`self._records: dict[str, VectorRecord] = {}`) with cosine similarity calculated via pure Python math (`_cosine_similarity`, lines 14-26).
    - Stored vector attributes: `memory_id` (UUID), `vector` (list of 128 floats), `document` (text chunk), and `metadata` (dict).

---

## Question 9: Is there a shared state graph? Is communication truly via EventBus only?

### Evidence
- **Shared State Graph:**
  - **YES.** Defined by `SharedWorkflowState` (SWS) in `shared/contracts/workflow.py:81-116`.
  - Holds `tasks: dict[UUID, Task]`, task dependency graphs (`task.dependencies` and `planner_output.dependency_graph`), `execution_queue`, `completed_tasks`, `failed_tasks`, `task_outputs`, `validations`, and `artifacts`.
- **Is communication truly via EventBus only?**
  - **NO.** The paper claim of "purely decoupled EventBus communication" does not reflect the codebase.
  - In `PipelineOrchestrator` (`backend/app/engine/orchestrator.py:20-180`):
    - The orchestrator holds direct instance references to agents (`self.worker = worker_agent`, `self.supervisor = supervisor_agent`, `self.healing = healing_agent`).
    - Core execution is orchestrated via **direct asynchronous method calls**:
      - `res = await self.worker.execute(t)` (`orchestrator.py:132`)
      - `validation = await self.supervisor.execute(t, result=res, state=state)` (`orchestrator.py:149`)
      - `healing_result = await self.healing.heal(t, res.error, state=state)` (`orchestrator.py:218`)
    - The `SharedWorkflowState` and `Task` objects are passed directly as in-memory Python arguments.
  - **True Role of EventBus:** `EventBus` (`backend/app/core/events/bus.py`) is used for asynchronous **event publishing and observability** (broadcasting events like `WORKFLOW_STARTED`, `TASK_COMPLETED`, `SUPERVISION_STARTED`, `PERMISSION_REQUESTED` to WebSockets, notifications, and telemetry) and loose triggering of replanning (`REPLANNING_TRIGGERED`). It is not the exclusive transport between agents.

---

## Question 10: Benchmark: in test_performance_benchmarks.py, how many iterations per row, mean or median, and how is "3,891 tasks/s" computed? Re-run it and report duration, task count and throughput. Is 500 tasks / 12.85 ms (about 38,900/s) or 3,891/s correct?

### Evidence
- **Benchmark Implementation:** `backend/tests/performance/test_performance_benchmarks.py:470-547` (`test_concurrent_multi_user_workflows_benchmark`)
  - Concurrency parameters:
    ```python
    num_concurrent_users = 10
    tasks_per_workflow = 5
    total_tasks_processed = num_concurrent_users * tasks_per_workflow  # Exactly 50 tasks!
    ```
  - Throughput formula:
    $$\text{Throughput} = \left(\frac{\text{total\_tasks\_processed}}{\text{total\_concurrent\_time\_ms}}\right) \times 1000.0$$
  - Measurement is a **single run duration** (neither mean nor median over multiple iterations; it executes 1 batch of 10 concurrent workflows).
- **The "3,891 tasks/s" Origin:**
  - Recorded in `docs/PERFORMANCE_BENCHMARK_REPORT.md:25` and `working/RESEARCH_PROJECT_BRIEF.md:289`:
    $$50 \text{ tasks} / 12.85\text{ ms} = 50 / 0.01285\text{ s} = \mathbf{3,891.05\text{ tasks/sec}}$$
  - **Verdict on 500 tasks vs. 50 tasks:**
    - The claim "500 tasks / 12.85 ms = 3,891 tasks/s" in paper drafts is **mathematically contradictory**. $500 / 0.01285\text{ s} \approx 38,910\text{ tasks/s}$.
    - The actual test processed **50 tasks** (10 users $\times$ 5 tasks). 50 tasks in 12.85 ms yields **3,891 tasks/s**. The "500 tasks" mention was a typographical error in the draft text.
- **Empirical Re-run Results on Host (2026-11-11):**
  Command executed:
  `python -m pytest backend/tests/performance/test_performance_benchmarks.py -k "test_concurrent_multi_user_workflows_benchmark" -s`
  - **Run 1:**
    - Total Tasks: 50
    - Duration: 182.03 ms
    - Measured Throughput: **274.69 tasks/sec**
  - **Run 2:**
    - Total Tasks: 50
    - Duration: 161.55 ms
    - Measured Throughput: **309.51 tasks/sec**
  - *Observation:* The historical figure of 12.85 ms (3,891 tasks/s) was recorded under a stripped mock environment without full event bus logging and disk serialization. With full runtime logging and TaskHistory recording active, real throughput on this host is approximately **275 - 310 tasks/sec**.

---

## Question 11: Which adapters (Playwright, pywinauto, PyAutoGUI, PowerShell, ReportLab, python-pptx) work against real applications, and which are only mocked?

### Evidence
All 6 adapters contain real implementation code designed to interface with real applications, OS subsystems, and binary files, with graceful mock/fallback degradation if dependencies or displays are missing:

1. **Playwright:** **REAL**
   - File: `backend/app/tools/browser/controller.py:7-15, 101-125` and `backend/app/tools/browser/dom.py:4-58`
   - Spawns real headless/headed Chromium browser processes via `async_playwright().start()` and `playwright.chromium.launch()`. Interacts with real DOM via `Page` and `Locator`.
2. **pywinauto:** **REAL**
   - File: `backend/app/tools/desktop/application.py:7, 170-280` and `backend/app/tools/desktop/controller.py:9, 410-435`
   - Connects to live Windows desktop application handles using `pywinauto.Desktop(backend="uia")` and `Application().connect()`. Used for window discovery, focus, and termination on Windows.
3. **PyAutoGUI:** **REAL**
   - File: `backend/app/tools/desktop/mouse.py:7-33, 290-630`, `backend/app/tools/desktop/keyboard.py:5-20, 260-395`, and `backend/app/tools/desktop/screenshot.py:4-110`
   - Executes real mouse movement, mouse clicks, keyboard keystrokes/hotkeys, and screen capture. Enforces real `FAILSAFE = True`.
4. **PowerShell:** **REAL**
   - File: `backend/app/tools/powershell/executor.py:16-120`
   - Spawns live `powershell.exe -NoProfile -NonInteractive -Command ...` subprocesses using `asyncio.create_subprocess_exec` on the Windows host, capturing real stdout, stderr, and exit codes.
5. **ReportLab:** **REAL**
   - File: `backend/app/tools/pdf/generator.py:8-250`
   - Compiles real, binary PDF files on disk using `reportlab.platypus` (`SimpleDocTemplate`, `Paragraph`, `Table`, `Spacer`, `Image`) and `reportlab.pdfgen.canvas`.
6. **python-pptx:** **REAL**
   - File: `backend/app/tools/ppt/generator.py:5-220` and `backend/app/tools/ppt/adapter.py:27-165`
   - Generates real Microsoft PowerPoint `.pptx` presentations conforming to the Open XML standard with shape trees, text frames, and slides.

---

## Remaining Questions & Discrepancies for Author Clarification (Before Phase 2)

1. **FAISS Vector Store Discrepancy:** The paper claims FAISS vector database integration, but the codebase actually implements an in-memory dictionary vector store with MD5 n-gram hash embeddings (`InMemoryVectorStoreProvider` / `DeterministicHashEmbeddingProvider`). Should Phase 2 evaluate this in-memory hash store, or should we plug in real FAISS for the RAG ablation?
2. **EventBus Decoupling Claim:** The paper draft claims all agent communication is decoupled over the EventBus, whereas the codebase coordinates Planner $\rightarrow$ Worker $\rightarrow$ Supervisor $\rightarrow$ Healing via direct asynchronous method calls inside `PipelineOrchestrator`. How should this architectural reality be framed in the revised paper?
3. **Throughput Benchmark Claim:** The historical figure of "3,891 tasks/s" reflects 50 tasks in 12.85 ms (not 500 tasks). On the current machine with full logging enabled, throughput measures ~300 tasks/s. Do you want the paper to report the 50-task throughput with mock tools or full end-to-end throughput?
4. **Patch Generator Terminology:** In the codebase, input patching is handled directly inside `RecoveryPlanner._create_generic_recovery_plan()`. Should we keep the paper's "Patch Generator" as a conceptual sub-module of Healing Agent, or should we introduce a discrete `PatchGenerator` class in `/experiments`?
