# AetherPhoenix Technology Stack Specification

**Version:** 1.0  
**Status:** Implemented (Sprint 10)

---

## 1. Backend Subsystem

| Category | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Language** | Python | `>=3.10` | Core backend runtime and agent framework |
| **Web Framework** | FastAPI | `>=0.141.1` | REST API routes, SSE streaming, OpenAPI generation |
| **ASGI Server** | Uvicorn | `>=0.52.1` | Asynchronous production web server |
| **Data Validation** | Pydantic | `>=2.13.4` | Data schemas, API contracts, settings validation |
| **ORM & Database** | SQLAlchemy | `>=2.0.0` | Relational database mapping & models |
| **Migrations** | Alembic | `>=1.13.0` | Database schema migration tracking |
| **HTTP Client** | HTTPX | `>=0.28.1` | Async HTTP requests for web scraping & API calls |

---

## 2. Desktop & Web Automation Engine

| Technology | Purpose |
| :--- | :--- |
| **Playwright** (`>=1.42.0`) | Chromium browser automation, page navigation, DOM selectors |
| **PyAutoGUI** (`>=0.9.54`) | Cross-platform mouse movements, click dispatching, screen bounds |
| **pywinauto** (`>=0.6.8`) | Native Windows GUI control, window handle inspection, keyboard input |
| **BeautifulSoup4** (`>=4.12.0`) | HTML content parsing, web scraping text extraction |
| **ReportLab** (`>=4.0.0`) | Programmatic PDF document generation |
| **python-pptx** (`>=1.0.2`) | PowerPoint presentation slide deck generation |

---

## 3. Frontend Subsystem

| Category | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **UI Library** | React | `19.2.8` | Declarative component framework |
| **Language** | TypeScript | `6.0.2` | Type-safe application development |
| **Build Tool** | Vite | `8.2.0` | Fast dev server & production client bundling |
| **Styling** | Tailwind CSS | `4.3.3` | Utility-first CSS styling system |
| **State Management** | Zustand | `5.0.14` | Global state stores (chat, permissions, workflow) |
| **Data Fetching** | TanStack Query | `5.101.4` | Asynchronous server state management |
| **Iconography** | Lucide React | `1.32.0` | Modern SVG icons |

---

## 4. Memory & Vector DB Subsystem

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Relational Database** | SQLite | `aether_phoenix.db` for task history, permissions, & logs |
| **Vector DB** | FAISS / ChromaDB | Local vector store for document embeddings and semantic RAG |
| **File Storage** | Local Filesystem | Artifact storage at `backend/artifacts/` |

---

## 5. Development & Testing Tools

| Tool | Subsystem | Purpose |
| :--- | :--- | :--- |
| **pytest** (`9.1.1`) | Backend | Unit, integration, and agent testing framework |
| **Ruff** (`0.16.1`) | Backend | Fast Python linter |
| **Black** (`26.5.1`) | Backend | Python code formatter |
| **Vitest** (`4.1.10`) | Frontend | React component & unit testing runner |
| **Oxlint** (`1.75.0`) | Frontend | Lightning-fast JavaScript/TypeScript linter |
| **Docker Compose** | DevOps | Multi-container service orchestration |
