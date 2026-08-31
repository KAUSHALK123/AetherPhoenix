# AetherPhoenix System Architecture Specification

**Version:** 1.0  
**Status:** Implemented (Sprint 10)  
**Single Source of Truth Document**

---

## 1. Executive Architectural Overview

AetherPhoenix is designed as an autonomous, event-driven multi-agent desktop automation platform inspired by modern AI software engineering and task automation architectures.

Rather than running unchecked terminal or script commands directly, AetherPhoenix follows a governed multi-agent execution pipeline:
1. **Goal Formulation**: Natural language user intent is extracted and analyzed.
2. **Interactive Clarification**: Ambiguous requests trigger clarifying questions before plan execution.
3. **Structured Task Decomposition**: Goals are decomposed into a Directed Acyclic Graph (DAG) of atomic subtasks.
4. **Governance & Permissions**: Every sensitive action undergoes fine-grained permission checks and safe-mode policy validation.
5. **Worker Execution**: Tasks are dispatched to specialized tool adapters via a unified Capability Registry.
6. **Supervisor Monitoring**: Steps are continuously monitored for output validity, quality, and runtime exceptions.
7. **Automated Self-Healing**: Failed tasks trigger root cause analysis, retry strategies, and dynamic recovery plans.
8. **Artifact Delivery**: Results are persisted, tracked in conversation memory, and exported into structured deliverables (PDF, PPTX, JSON, Markdown).

---

## 2. Layered System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                              │
│         React 19 + TypeScript + Vite + Tailwind CSS Web Dashboard      │
│   (Interactive Chat, Plan Review, Permissions Modal, Observability)   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ REST API / Server-Sent Events (SSE)
┌──────────────────────────────────▼─────────────────────────────────────┐
│                         RUNTIME KERNEL & API                           │
│                 FastAPI App Server (app/main.py)                       │
│    (Routers: /planner, /dashboard, /permissions, /notifications)      │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────────────┐
│                      PIPELINE ORCHESTRATOR                             │
│     (app/engine/orchestrator.py - State & DAG Workflow Queue)          │
└────────┬─────────────────────────┼──────────────────────────┬──────────┘
         │                         │                          │
┌────────▼────────┐       ┌────────▼────────┐        ┌────────▼────────┐
│  PLANNER AGENT  │       │  WORKER AGENT   │        │ SUPERVISOR AGENT│
│ Intent Parsing, │       │ Tool Sandbox &  │        │ Output Quality  │
│ Clarification,  │       │ Capability      │        │ & Step Failure  │
│ Task DAG        │       │ Execution       │        │ Monitoring      │
└────────┬────────┘       └────────┬────────┘        └────────┬────────┘
         │                         │                          │
         │                         │                 (Failure Event)
         │                         │                          │
         │                         ▼                          ▼
         │               ┌──────────────────┐       ┌──────────────────┐
         │               │ PERMISSION ENGINE│       │  HEALING AGENT   │
         │               │ Safe Execution   │◄──────┤ Root Cause,      │
         │               │ Policy & Consent │       │ Retry Engine &   │
         │               └──────────────────┘       │ Recovery Plan    │
         │                                          └──────────────────┘
         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        MEMORY & STORAGE SUBSYSTEM                      │
│   SQLite Database (SQLAlchemy/Alembic) | FAISS Vector DB | Artifacts  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Subsystem Architecture

### 3.1 Planner Subsystem (`app/planner/`)

- **Goal Engine (`goal_engine.py`)**: Entry point for natural language requests. Converts user prompts into structured goal objects.
- **Clarifier (`clarifier.py`)**: Evaluates goal completeness. If required parameters are missing or ambiguous, generates structured clarification cards.
- **Decomposer (`decomposer.py`)**: Uses `TaskDecompositionEngine` to split goals into hierarchical DAG task structures (Phase tasks and Leaf tasks). Validates DAG topology using Kahn's algorithm to prevent cycles.
- **Risk & Priority Analysis (`risk_analysis.py`, `priority.py`)**: Assesses execution risk (LOW, MEDIUM, HIGH, CRITICAL) and assigns execution priorities.

### 3.2 Execution Engine & Worker Agent (`app/agents/worker/`, `app/engine/`)

- **Pipeline Orchestrator (`app/engine/orchestrator.py`)**: Manages the execution lifecycle of `SharedWorkflowState`. Maintains `ready`, `in_progress`, `completed`, and `failed` task sets.
- **Worker Agent (`app/agents/worker/agent.py`)**: Core execution worker. Resolves required tool adapters from the `CapabilityRegistry` and executes tasks within a sandboxed environment.
- **Tool Adapter Architecture**:
  - `BrowserAdapter` (`app/tools/browser/`): Automated browser control via Playwright.
  - `DesktopToolAdapter` (`app/tools/desktop/`): Windows application, window handle, mouse (`PyAutoGUI`), and keyboard (`pywinauto`) control.
  - `FileExplorerAdapter` (`app/tools/file_explorer/`): Safe filesystem operations (list, search, copy, move, structure analysis).
  - `OCRAdapter` (`app/tools/ocr/`): Optical Character Recognition for image-to-text extraction.
  - `PDFGeneratorAdapter` / `PPTGeneratorAdapter` (`app/tools/pdf/`, `app/tools/ppt/`): Structured document creation using ReportLab and `python-pptx`.
  - `PowerShellAdapter` (`app/tools/powershell/`): Controlled PowerShell command execution with output parsing.
  - `WebResearchAdapter` (`app/tools/web_research/`): Multi-source web search, scraping, and information extraction.

### 3.3 Supervisor Subsystem (`app/agents/supervisor/`)

- **Supervisor Agent (`agent.py`)**: Validates every task output after worker completion.
- **Failure Detector (`failure_detector.py`)**: Inspects return payload status, execution duration, and log outputs to detect subtle runtime failures.
- **Quality Inspector**: Ensures output data matches expected task contracts before marking a task as `COMPLETED`.

### 3.4 Self-Healing Subsystem (`app/agents/healing/`)

- **Healing Agent (`agent.py`)**: Invoked automatically when the Supervisor detects a task failure.
- **Root Cause Analyzer (`root_cause_analyzer.py`)**: Parses error tracebacks and categorizes failures into error types (e.g. `TIMEOUT`, `PERMISSION_DENIED`, `ELEMENT_NOT_FOUND`, `SYNTAX_ERROR`).
- **Retry Engine & Recovery Planner (`retry_engine.py`, `recovery_planner.py`)**: Implements exponential backoff retry strategies, alternative tool selection, or dynamic replacement workflow branches.

### 3.5 Permission Manager & Safe Execution Mode (`app/core/permissions/`)

- **Permission Manager (`manager.py`)**: Enforces access control policies across permission categories (`DESKTOP_AUTOMATION`, `BROWSER_ACCESS`, `FILE_SYSTEM`, `POWERSHELL`, `INTERNET`).
- **Safe Execution Mode**: Restricts dangerous operations:
  - Blocks unsafe hotkeys (e.g. `Alt+F4`, `Win+L`, system format commands).
  - Blocks local file scheme URLs (`file:///`) in browser navigation.
  - Requires explicit user approval in the UI for elevated operations.

### 3.6 Memory & RAG Subsystem (`app/memory/`)

- **Conversation Memory (`conversation_memory.py`)**: Maintains short-term turn history across chat sessions.
- **Task History Manager (`task_history.py`)**: Persists historical workflow execution stats into SQLite (`aether_phoenix.db`).
- **Vector Database & RAG (`vector_db.py`, `rag_pipeline.py`)**: Embeds workflow history and document context using FAISS / vector embeddings for semantic context retrieval.

### 3.7 Artifact Storage (`app/services/artifact_storage.py`)

- Manages deliverable output files.
- Organizes generated files under `backend/artifacts/<workflow_id>/<task_id>/`.
- Provides export handlers for PDF, PPTX, JSON, and Markdown files.

---

## 4. Architecture Implementation Status Matrix

| Layer / Component | Status | Implementation Details |
| :--- | :---: | :--- |
| **Planner & Goal Engine** | ✅ Implemented | Goal parsing, clarification cards, DAG decomposer, risk analysis. |
| **Pipeline Orchestrator** | ✅ Implemented | Event-driven execution loop, queue management, state persistence. |
| **Worker Agent** | ✅ Implemented | Capability Registry, sandboxed tool dispatch. |
| **Desktop Automation** | ✅ Implemented | PyAutoGUI mouse control, pywinauto keyboard control, application launching. |
| **Browser Automation** | ✅ Implemented | Playwright navigation, DOM interaction, page scraping. |
| **Supervisor Agent** | ✅ Implemented | Output contract validation, real-time failure detection. |
| **Healing Agent** | ✅ Implemented | Error parsing, exponential backoff retries, self-healing loop. |
| **Permission Manager** | ✅ Implemented | Safe Execution Mode, interactive approval workflows, hotkey protection. |
| **Memory & RAG** | ✅ Implemented | SQLite task history, FAISS vector embeddings, RAG context retrieval. |
| **Document Export Engine** | ✅ Implemented | ReportLab PDF generator, `python-pptx` deck generator, JSON/MD export. |
| **Web Dashboard (Frontend)** | ✅ Implemented | React 19, TypeScript, Vite, Tailwind CSS, Zustand stores. |
| **Browser Extension Bridge** | 🟡 Partially Implemented | Backend endpoints and websocket contracts defined; store package pending. |
| **Multi-Worker Distributed Node** | 🔮 Planned | Distributed worker execution across remote nodes (v2.0). |

---

## 5. Architectural Contracts & Security Boundaries

1. **Immutability of Task DAG During Execution**: The initial DAG is generated by the Planner. Dynamic alterations are permitted only via the Healing Agent during recovery.
2. **Permission Boundary**: Tool adapters MUST NOT execute system-altering commands without evaluating `PermissionManager.check_permission()`.
3. **Data Isolation**: All execution state is localized to the active session and stored locally (`aether_phoenix.db` and `backend/artifacts/`).
