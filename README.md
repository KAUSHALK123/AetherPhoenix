# AI Desktop Assistant

> An AI-powered autonomous desktop assistant built using a multi-agent architecture capable of planning, executing, supervising, and self-healing complex workflows.

---

# Project Overview

AI Desktop Assistant is an intelligent desktop automation platform inspired by modern AI coding agents such as VS Code Agent, Manus, and OpenHands.

Instead of executing commands directly, the system first understands the user's goal, creates an execution plan, performs the required tasks, verifies every step, automatically recovers from failures, and finally delivers the requested result.

The platform is designed around a modular multi-agent architecture consisting of:

- Planner Agent
- Workflow Compiler
- Worker Agent
- Supervisor Agent
- Healing Agent
- Runtime Kernel

The long-term vision is to build an AI Operating System capable of safely automating desktop tasks while remaining transparent, explainable, and secure.

---

# Core Features

- Multi-Agent Architecture
- Intelligent Task Planning
- Browser Automation
- Desktop Automation
- Windows Automation
- AI-Powered Research
- PowerPoint Generation
- PDF Generation
- Code Generation
- Git Automation
- PowerShell Automation
- OCR & Vision Support
- Self-Healing Execution
- Permission-Based Security
- Workflow Monitoring
- Runtime Logs
- Memory Architecture
- Event-Driven Runtime

---

# Architecture Overview

The project follows a layered architecture.

```
Presentation Layer

↓

Runtime Kernel

↓

Orchestrator

↓

Planner Agent

↓

Workflow Compiler

↓

Execution Engine

↓

Worker Agent

↓

Supervisor Agent

↓

Healing Agent

↓

Tool Sandbox

↓

Operating System
```

Detailed architecture documentation is available inside the **docs/** directory.

---

# Tech Stack

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Zustand
- TanStack Query

## Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- SQLAlchemy
- Alembic

## AI & Agent Framework

- LangGraph
- LangChain (where applicable)
- Ollama
- Gemini API
- Instructor
- Pydantic AI

## Automation

- Playwright
- PyAutoGUI
- pywinauto
- Requests
- BeautifulSoup
- httpx

## Database

- SQLite (Development)
- PostgreSQL (Future)
- ChromaDB / FAISS (Knowledge Memory)

## DevOps

- Docker
- Docker Compose
- GitHub Actions (Future)

---

# Repository Structure

```
AI-Desktop-Assistant/

├── frontend/
├── backend/
├── shared/
├── docs/
├── scripts/
├── docker/
├── .github/
├── .gitignore
├── README.md
└── LICENSE
```

Detailed folder structure will be documented separately.

---

# Quick Start

## Clone Repository

```bash
git clone <repository-url>
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

## Backend

```bash
cd backend

uv sync

uv run uvicorn app.main:app --reload
```

---

## Verify

Open

```
http://localhost:5173
```

and

```
http://localhost:8000/docs
```

---

# Development Guide

## Branch Strategy

Never commit directly to **main**.

Development flow:

```
main

↓

develop

↓

feature/*
```

### Branch Naming

```
feature/planner-agent

feature/frontend-layout

feature/runtime-kernel

feature/database

docs/readme-update

bugfix/sidebar

hotfix/login
```

---

## Development Workflow

1. Pull latest `develop`
2. Create a new feature branch
3. Implement the assigned issue
4. Commit changes
5. Push the branch
6. Open a Pull Request targeting `develop`
7. Wait for review
8. Merge only after approval

---

## Pull Request Rules

Every Pull Request must include:

- Linked GitHub Issue
- Clear Description
- Testing Performed
- Screenshots (if UI changes)
- Updated Documentation (if required)

---

## Commit Message Convention

Examples:

```
feat: add planner workflow compiler

fix: resolve browser timeout issue

docs: update architecture diagrams

refactor: improve runtime state management

test: add planner unit tests
```

---

# Documentation

The complete project documentation is available inside the **docs/** directory.

Important documents include:

- Product Requirements Document (PRD)
- Software Requirements Specification (SRS)
- System Architecture
- AI Architecture
- Database Design
- API Specification
- User Flows
- UI Guidelines
- Test Plan
- Implementation Roadmap

The documentation should be considered the **Single Source of Truth** for the project.

---

# Team Workflow

This project follows a GitHub Issue → Pull Request workflow.

```
Issue

↓

Feature Branch

↓

Development

↓

Pull Request

↓

Code Review

↓

Merge into develop

↓

Testing

↓

Merge into main
```

No code should be merged directly into `main`.

---

# Roadmap

Current Status

- Documentation ✅
- Architecture Design ✅
- Repository Setup 🚧
- Sprint 0 – Foundation ⏳
- Sprint 1 – Core Runtime ⏳
- Sprint 2 – AI Agents ⏳
- Sprint 3 – Desktop Automation ⏳
- Sprint 4 – Integration & Testing ⏳

---

# Team

| Role | Responsibility |
|------|----------------|
| Team Lead | Architecture, Reviews, Integration |
| Frontend Developer | UI & React |
| Backend Developer | APIs & Runtime |
| AI/Database Developer | Agents, Memory, Database |

---

# License

License information will be added before the first public release.

---

## Note

Before contributing, please read the documentation inside the **docs/** directory.

The documentation defines the architecture, implementation guidelines, and coding standards that all contributors must follow.