# AetherPhoenix — Post-Sprint Integration Recovery & Master Implementation Plan

> **Document Status**: Master Recovery Blueprint & Prompt Guide  
> **Target Branch**: `fix/agent-capability-routing`  
> **Scope**: End-to-End Intent Routing, Desktop/Terminal Execution, Visible Browser Research, Real Runtime Telemetry, and Full Capability Validation Matrix.

---

## 📌 Executive Summary

While the core multi-agent infrastructure (Planner, Worker, Supervisor, Healing, Permission Manager, Event Bus, Artifact Storage) exists and unit tests pass, real frontend integration testing revealed a **capability routing bottleneck**:
Natural-language user prompts are not reliably classified and routed to their corresponding backend tool adapters. For example, command execution requests (e.g. `"Run ipconfig on my laptop."`) can wrongly decompose into presentation/PDF workflows rather than invoking the terminal/PowerShell capability.

This blueprint establishes a mandatory 4-phase implementation guide to enforce **Intent → Capability → Permission → Execution → Validation → Real Telemetry** across all supported features.

---

## 📋 Comprehensive Execution Workflow

```
[ User Prompt ]
       │
       ▼
[ PlannerAgent ] ──► (Classifies Intent into TaskCategory & required_tool)
       │
       ▼ (Checks Permission & Safe Execution Mode)
[ PermissionManager ] ──► (Requests user approval if sensitive operation)
       │
       ▼
[ PipelineOrchestrator ]
       │
       ├───────────────────────────────┐
       ▼                               ▼
[ WorkerAgent ]              [ SupervisorAgent ]
  (Dispatches to Tool           (Validates Real Output &
   Adapter in Registry)          Enforces Outcome Criteria)
       │                               │
       ├───────────────────────────────┤ (If Failure Detected)
       ▼                               ▼
[ Execution Sandbox ]        [ HealingAgent ]
(PowerShell, Browser,         (Root Cause Analysis &
 FileExplorer, OCR, etc.)      Dynamic Strategy Retry)
       │
       ▼
[ Real Runtime Events ] ──► [ Frontend Dashboard ]
```

---

## 🔍 Phase 1 — Capability Routing & Planner Correction

### Objective
Ensure `PlannerAgent` and `decomposer.py` correctly parse intent and assign exact `TaskCategory`, `required_tool`, and `assigned_agent` contracts without defaulting or incorrectly falling back to PPT/PDF generation.

### Target Files & Architecture
- [`backend/app/planner/decomposer.py`](file:///d:/PROJECTS/Major/backend/app/planner/decomposer.py)
- [`backend/app/agents/planner/agent.py`](file:///d:/PROJECTS/Major/backend/app/agents/planner/agent.py)
- [`backend/app/tools/registry.py`](file:///d:/PROJECTS/Major/backend/app/tools/registry.py)
- [`backend/app/agents/planner/permission_engine.py`](file:///d:/PROJECTS/Major/backend/app/agents/planner/permission_engine.py)

### Capability Intent & Routing Matrix

| User Prompt Example | Target Intent | `TaskCategory` | `required_tool` | `assigned_agent` | Required Permission |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `"Run ipconfig on my laptop."` | System Command | `POWERSHELL_EXECUTION` / `TERMINAL_COMMAND` | `powershell_executor` / `terminal_tool` | `WorkerAgent` | `SYSTEM_COMMAND` |
| `"Open Notepad."` | Desktop App | `DESKTOP_AUTOMATION` | `desktop_tool` | `WorkerAgent` | `DESKTOP_AUTOMATION` |
| `"Open my Downloads folder."` | File Explorer | `FILE_SYSTEM` | `file_explorer` | `WorkerAgent` | `FILE_SYSTEM` |
| `"Search the web deeply about NVIDIA GPUs."` | Web Research | `WEB_RESEARCH` | `web_research_tool` | `WorkerAgent` | None / Low Risk |
| `"Research this topic and create a PDF."` | Research + PDF | `WEB_RESEARCH` ➔ `PDF_GENERATION` | `web_research_tool` ➔ `pdf_generator` | `WorkerAgent` | `FILE_SYSTEM` |
| `"Open VS Code and create a Python file."` | Dev Tools | `DESKTOP_AUTOMATION` / `FILE_SYSTEM` | `desktop_tool` / `file_explorer` | `WorkerAgent` | `DESKTOP_AUTOMATION` |
| `"Create a 5-slide PPT about electric vehicles."` | Presentation | `PPT_GENERATION` | `ppt_tool` | `WorkerAgent` | `FILE_SYSTEM` |
| `"Take this uploaded image and extract text."` | AI Vision | `OCR_PROCESSING` | `ocr_tool` | `WorkerAgent` | None / Read File |
| `"Create a GitHub issue describing this bug."` | Version Control | `GIT_OPERATIONS` | `git_tool` | `WorkerAgent` | `EXTERNAL_API` |

### Key Rule
**Zero Ambiguity Fallback**: The Planner must never route an unrecognized prompt to `PPT_GENERATION`. If intent is underspecified, trigger a `ClarificationRequest` event to the user.

---

## ⚡ Phase 2 — Desktop & Terminal Execution Infrastructure

### Objective
Verify and enforce live OS execution for PowerShell commands, desktop application launches, and local directory navigation with full `PermissionManager` clearance.

### Target Files
- [`backend/app/tools/terminal/adapter.py`](file:///d:/PROJECTS/Major/backend/app/tools/terminal/adapter.py)
- [`backend/app/tools/desktop/adapter.py`](file:///d:/PROJECTS/Major/backend/app/tools/desktop/adapter.py)
- [`backend/app/tools/file_explorer/adapter.py`](file:///d:/PROJECTS/Major/backend/app/tools/file_explorer/adapter.py)
- [`backend/app/core/permissions/manager.py`](file:///d:/PROJECTS/Major/backend/app/core/permissions/manager.py)

### Security & Safe Execution Enforcement
1. **No Simulated Output**: Shell commands must execute through native `subprocess` / `asyncio.create_subprocess_exec` and capture stdout/stderr.
2. **Permission Check**: Before executing system commands, verify `PermissionStatus.GRANTED`. Prompt user in frontend if unapproved.
3. **Safe Execution Policy**: Block high-risk commands (e.g. `rmdir /s /q c:\`, `Format-Volume`, destructive privilege escalations) via `SafeExecutionPolicy`.

---

## 🌐 Phase 3 — Visible Browser & Web Research Automation

### Objective
Differentiate between lightweight **Web Search** (API/DuckDuckGo), **Browser Automation** (Playwright active navigation), and **DOM Automation** (clicking, typing, submitting forms).

### Target Files
- [`backend/app/tools/browser/interface.py`](file:///d:/PROJECTS/Major/backend/app/tools/browser/interface.py)
- [`backend/app/tools/web_research/tool.py`](file:///d:/PROJECTS/Major/backend/app/tools/web_research/tool.py)
- [`backend/app/tools/dom_automation/`](file:///d:/PROJECTS/Major/backend/app/tools/dom_automation/)

### Execution Modes
- **Headless Mode**: Used for background data extraction and speed-optimized searches.
- **Visible Mode (`headless=False`)**: Used when the user requests visible browser interaction or manual review. Emits real-time URL change and DOM event telemetry over `EventBus`.

---

## 🔌 Phase 4 — Real Telemetry, Frontend Wiring & Final Validation

### Objective
Ensure the frontend React application consumes real backend `RuntimeEvent` streams over WebSocket/SSE instead of displaying fake mock state cards.

### Target Files
- [`frontend/src/pages/ExecutionPage.tsx`](file:///d:/PROJECTS/Major/frontend/src/pages/ExecutionPage.tsx)
- [`frontend/src/pages/ArtifactsPage.tsx`](file:///d:/PROJECTS/Major/frontend/src/pages/ArtifactsPage.tsx)
- [`frontend/src/components/chat/ArtifactPopcard.tsx`](file:///d:/PROJECTS/Major/frontend/src/components/chat/ArtifactPopcard.tsx)
- [`backend/app/api/endpoints/dashboard.py`](file:///d:/PROJECTS/Major/backend/app/api/endpoints/dashboard.py)

---

## 🧪 Master Validation Matrix

Run and verify the following 9 test prompts prior to merging:

| Test ID | User Prompt | Expected Classification | Expected Tool Adapter | Expected Output / Artifact |
| :---: | :--- | :--- | :--- | :--- |
| **TEST 1** | `"Create a 5-slide PPT about electric vehicles."` | `PPT_GENERATION` | `PPTToolAdapter` | Native `.pptx` file (5 slides) |
| **TEST 2** | `"Run ipconfig on my laptop."` | `POWERSHELL_EXECUTION` | `TerminalToolAdapter` | Live IP configuration stdout |
| **TEST 3** | `"Open Notepad."` | `DESKTOP_AUTOMATION` | `DesktopToolAdapter` | Notepad process launched |
| **TEST 4** | `"Open my Downloads folder."` | `FILE_SYSTEM` | `FileExplorerToolAdapter` | Directory listing / Explorer opened |
| **TEST 5** | `"Open VS Code."` | `DESKTOP_AUTOMATION` | `DesktopToolAdapter` | VS Code launched |
| **TEST 6** | `"Research NVIDIA GPU architecture and create a PDF."` | `WEB_RESEARCH` ➔ `PDF_GENERATION` | `WebResearchTool` ➔ `PDFToolAdapter` | Native `.pdf` document |
| **TEST 7** | `"Extract the text from this uploaded image."` | `OCR_PROCESSING` | `OCRToolAdapter` | Extracted text string payload |
| **TEST 8** | `"Create a GitHub issue describing this bug."` | `GIT_OPERATIONS` | `GitToolAdapter` | Issue URL / payload contract |
| **TEST 9** | `"Intentionally invalid prompt xyz123."` | `UNKNOWN` / `CLARIFICATION` | N/A | Clarification request / Healing retry failure |

---

## 🛑 Strict Execution Rules for Agents

1. **Git Isolation**: Create and execute all changes on branch `fix/agent-capability-routing`. Do NOT commit directly to `main` or `develop`.
2. **No Hardcoded Keyword Hacks**: Do NOT hardcode `"ipconfig"` or specific user strings into the Planner. Use generic intent recognition and pattern schemas.
3. **No Fake Telemetry or Mock Files**: Never generate fake text blobs with binary extensions (`.pptx`, `.pdf`). Use native binary streams (`FileResponse`).
4. **Mandatory Tests**: Run backend `pytest` and frontend `npm run build` after completing each phase.
5. **No Direct Merges**: Do NOT push or merge the branch upon completion. Provide a final summary and await human verification.
