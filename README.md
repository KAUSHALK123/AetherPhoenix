# AetherPhoenix — AI Desktop Assistant

> An autonomous multi-agent desktop assistant platform capable of goal understanding, task planning, interactive clarification, secure execution, continuous supervision, self-healing, and multi-format document export.

---

## 📌 Implementation Status Matrix

| Subsystem / Feature | Status | Description |
| :--- | :---: | :--- |
| **Multi-Agent Architecture** | ✅ Implemented | Planner, Worker, Supervisor, and Healing agents integrated via Pipeline Orchestrator. |
| **Planner & Goal Engine** | ✅ Implemented | Goal parsing, clarification engine, DAG task decomposition, risk analysis, and priority ranking. |
| **Worker Execution Engine** | ✅ Implemented | Capability Registry & Tool Adapters (Browser, Desktop, File System, OCR, PDF/PPTX Export, Web Research, PowerShell). |
| **Supervisor Agent** | ✅ Implemented | Step validation, outcome quality checks, and real-time failure detection. |
| **Self-Healing Loop** | ✅ Implemented | Root cause analysis, error classification, dynamic retry strategy, and recovery plan execution. |
| **Permission System & Safe Mode** | ✅ Implemented | Fine-grained permission approvals, safe execution policies, URL scheme validation, and restricted hotkey enforcement. |
| **Memory & RAG Pipeline** | ✅ Implemented | Conversation memory, task history persistence, vector embeddings (FAISS/ChromaDB), and context retrieval. |
| **Frontend Web Dashboard** | ✅ Implemented | React 19 + TypeScript + Tailwind CSS interface featuring interactive chat, plan review, permission approvals, and observability. |
| **Export Engine** | ✅ Implemented | PDF generation (ReportLab), PowerPoint generation (`python-pptx`), JSON, and Markdown artifact exports. |
| **Browser Extension Integration** | 🟡 Partially Implemented | WebSocket bridge and API contract established; live store extension installation pending. |
| **Distributed Multi-Worker Execution** | 🔮 Planned | Scaling execution across multiple remote worker nodes (Version 2.0). |
| **Plugin Marketplace** | 🔮 Planned | Community plugin distribution ecosystem (Version 2.0). |

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: `3.10` or higher
- **Node.js**: `18.0` or higher (npm `9+`)
- **OS**: Windows 10/11 (for Desktop & PowerShell automation capabilities)

---

### 1. Repository Setup

```bash
git clone https://github.com/KAUSHALK123/AetherPhoenix.git
cd AetherPhoenix
```

---

### 2. Backend Setup & Startup

```bash
cd backend

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Run database migrations (SQLite database created automatically at backend/aether_phoenix.db)
python -m alembic upgrade head

# Start FastAPI backend server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

> **Backend API Docs**: Swagger UI is accessible at [http://localhost:8000/docs](http://localhost:8000/docs).

---

### 3. Frontend Setup & Startup

In a separate terminal:

```bash
cd frontend

# Install Node.js dependencies
npm install

# Start Vite development server
npm run dev
```

> **Frontend Application**: Open [http://localhost:5173](http://localhost:5173) in your web browser.

---

## 🏗 System Architecture Overview

AetherPhoenix is built on a modular, event-driven multi-agent execution pipeline:

```
[ User Request ]
       │
       ▼
[ Planner Agent ] ──► (Generates Clarification Questions if ambiguous)
       │
       ▼ (Produces DAG Task Decomposition)
[ Permission Manager ] ──► (Requests user consent for sensitive actions)
       │
       ▼
[ Pipeline Orchestrator ]
       │
       ├─────────────────────────┐
       ▼                         ▼
[ Worker Agent ]        [ Supervisor Agent ]
  (Capability Registry)    (Step Output Validation)
       │                         │
       ├─────────────────────────┤ (If Failure Detected)
       ▼                         ▼
 [ Tools Sandbox ]       [ Healing Agent ]
 (Browser, Desktop,        (Root Cause Analysis &
  PDF, PPT, OCR, etc.)      Dynamic Recovery Strategy)
       │
       ▼
[ Generated Artifacts & Final Result ]
```

### Core Architecture Components

1. **Planner Agent** ([docs/SYSTEM_ARCHITECTURE.md](file:///c:/Users/dhany/majorproject/AetherPhoenix/docs/SYSTEM_ARCHITECTURE.md)): Analyzes natural language goals, extracts intent, asks clarifying questions when needed, and produces structured DAG execution plans.
2. **Worker Agent & Capability Registry**: Dispatches atomic tasks to registered tool adapters (`browser_automation`, `desktop_automation`, `pdf_generator`, `ppt_generator`, `ocr_tool`, `file_explorer`, `powershell_executor`).
3. **Supervisor Agent**: Monitors execution in real time, validates output data quality against expected criteria, and flags execution failures.
4. **Healing Agent**: Analyzes failure stack traces, identifies root causes, formulates recovery strategies, and triggers automated re-execution.
5. **Permission Manager**: Enforces Safe Execution policies, asking for explicit user approval before executing sensitive operations (e.g. system commands, desktop automation, browser navigation).
6. **Memory Subsystem**: Manages short-term conversation context, persistent task execution logs, vector embeddings, and RAG retrieval.

---

## 🧪 Testing & Quality Standards

### Running Backend Tests & Linters

```bash
cd backend

# Run complete pytest suite
.\.venv\Scripts\python.exe -m pytest

# Run fast unit tests only
.\.venv\Scripts\python.exe -m pytest -m "not integration"

# Run code linter (Ruff)
.\.venv\Scripts\python.exe -m ruff check .

# Run code formatter check (Black)
.\.venv\Scripts\python.exe -m black --check .
```

### Running Frontend Tests & Linters

```bash
cd frontend

# Run unit and component tests (Vitest)
npm test

# Run code linter (Oxlint)
npm run lint

# Verify TypeScript types and production build
npm run build
```

---

## 📦 Artifact Storage & Data Locations

- **Database File**: `backend/aether_phoenix.db` (SQLite)
- **Generated Artifacts**: `backend/artifacts/<workflow_id>/<task_id>/`
- **Execution Logs**: `backend/logs/app.log`
- **Vector DB Storage**: `backend/artifacts/vector_db/`

---

## 🐳 Docker Deployment

To run the complete system using Docker Compose:

```bash
# Build and start services in detached mode
docker-compose up --build -d

# Stop services
docker-compose down
```

---

## 🔧 Troubleshooting

### 1. `ModuleNotFoundError` during pytest
**Solution**: Ensure the virtual environment is activated and dependencies are installed in `.venv`:
```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Frontend API Connection Refused (`http://localhost:8000`)
**Solution**: Verify that the FastAPI backend server is running on port 8000 and CORS middleware is active.

### 3. PyAutoGUI / pywinauto GUI Automation Errors
**Solution**: Desktop automation tools require an active Windows display session. Ensure you are not running inside a headless SSH session without a GUI display context.

---

## 📚 Complete Documentation Index

For detailed architectural and API specifications, refer to the documentation inside `docs/`:

- [System Architecture](file:///c:/Users/dhany/majorproject/AetherPhoenix/docs/SYSTEM_ARCHITECTURE.md)
- [API Specification](file:///c:/Users/dhany/majorproject/AetherPhoenix/docs/API_SPEC.md)
- [Technology Stack](file:///c:/Users/dhany/majorproject/AetherPhoenix/docs/TECH_STACK.md)
- [Product Requirements (PRD)](file:///c:/Users/dhany/majorproject/AetherPhoenix/docs/PRD.md)
- [Development Guide](file:///c:/Users/dhany/majorproject/AetherPhoenix/docs/IMPLEMENTATION/DEV_GUIDE.md)

---

## 📄 License

Internal Project Repository — Proprietary / All Rights Reserved.