# 07_IMPLEMENTATION_GUIDE.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Document Owner:** Project Team

---

# Related Documents

- 00_ARCHITECTURE_PRINCIPLES.md
- 01_PROJECT_FOUNDATION.md
- 02_FEATURES_AND_PRD.md
- 03_SYSTEM_ARCHITECTURE.md
- 04_DATABASE.md
- 05_API_SPEC.md
- 06_UI.md
- 08_DEVELOPMENT_ROADMAP.md
- 09_AI_DEVELOPMENT_PLAN.md

---

# Purpose

This document defines the engineering standards, folder organization, coding conventions, module responsibilities, development workflow, and implementation rules that every developer must follow.

Its objective is to ensure consistency across all Pull Requests and maintain a production-quality codebase.

---

# Development Philosophy

The project should be developed incrementally.

Never build everything together.

Always complete one module before integrating it with the next.

Each module should be:

- Independent
- Testable
- Reusable
- Well documented
- Loosely coupled

---

# Technology Stack

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Zustand
- React Query
- Framer Motion

---

## Backend

- Python 3.12+
- FastAPI
- LangGraph
- Pydantic
- SQLAlchemy
- Alembic
- Uvicorn

---

## Database

- SQLite (V1)
- PostgreSQL (Future)

---

## AI

- Ollama (Preferred)
- Gemini API
- OpenRouter
- Local Models

---

## Browser Automation

- Playwright

---

## Desktop Automation

- PyAutoGUI
- pywinauto
- keyboard
- mouse

---

## OCR

- PaddleOCR
- OpenCV

---

## Git

- GitPython

---

## Document Generation

- python-pptx
- python-docx
- ReportLab

---

# Repository Structure

```
project-root/

docs/

frontend/

backend/

tests/

scripts/

tools/

assets/

README.md

.env.example

.gitignore

docker-compose.yml
```

---

# Backend Structure

```
backend/

app/

agents/

planner/

worker/

supervisor/

healing/

core/

orchestrator/

permissions/

rollback/

capabilities/

artifacts/

events/

memory/

models/

schemas/

services/

repositories/

tools/

browser/

desktop/

git/

powershell/

research/

ppt/

pdf/

ocr/

vision/

api/

routers/

middleware/

database/

config/

utils/

tests/
```

---

# Frontend Structure

```
frontend/

src/

components/

pages/

layouts/

hooks/

services/

api/

store/

types/

contexts/

constants/

assets/

styles/

utils/

routes/
```

---

# Naming Convention

Classes

```
PlannerAgent
```

Files

```
planner_agent.py
```

Folders

```
planner
```

Functions

```
generate_plan()
```

Variables

```
workflow_state
```

Constants

```
MAX_RETRY_COUNT
```

---

# Coding Standards

Every module should:

- Have one responsibility
- Use dependency injection
- Avoid global variables
- Return structured objects
- Handle exceptions gracefully
- Follow SOLID principles

---

# Module Responsibilities

## Planner

Responsible for

- Intent understanding
- Clarification
- Workflow generation

Never

- Execute tasks

---

## Worker

Responsible for

- Task execution

Never

- Think
- Retry
- Plan

---

## Supervisor

Responsible for

- Validation
- Monitoring
- Progress

---

## Healing

Responsible for

- Recovery
- Retry
- Root cause analysis

---

## Orchestrator

Responsible for

- Workflow lifecycle
- State management
- Scheduling
- Event publishing

---

# Shared State Rules

Every module must:

Read

↓

Update

↓

Return

Never modify another module's internal data directly.

---

# API Rules

Every endpoint should

- Validate input
- Return consistent responses
- Handle errors
- Log requests

No business logic inside routers.

---

# Database Rules

- Repository Pattern
- ORM only
- No raw SQL unless required
- Transactions where necessary
- UUID Primary Keys

---

# Error Handling

Every module should

- Catch expected exceptions
- Log unexpected exceptions
- Return structured errors
- Never expose stack traces to users

---

# Logging Standards

Every important event should be logged.

Levels

- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

---

# Configuration

Environment variables only.

Never hardcode

- API Keys
- Passwords
- Secrets
- Database URLs

---

# Code Documentation

Every public function must include

- Purpose
- Parameters
- Returns
- Exceptions

---

# Pull Request Rules

Every PR must

- Build successfully
- Pass tests
- Follow naming conventions
- Update documentation
- Include screenshots (Frontend)
- Include logs (Backend)

---

# Commit Message Format

```
feat(planner): add workflow validation

fix(worker): fix browser execution

docs(api): update authentication

refactor(core): simplify workflow manager
```

---

# Branch Strategy

```
main

develop

feature/<name>

bugfix/<name>

hotfix/<name>

release/<version>
```

---

# Code Review Checklist

Reviewer must verify

- Code quality
- Documentation
- Security
- Performance
- Error handling
- Tests
- UI consistency

---

# Testing Rules

Every module should include

- Unit Tests
- Integration Tests

Critical workflows require

- End-to-End Tests

---

# Performance Guidelines

Backend

- Async where possible
- Avoid blocking operations
- Cache repeated computations

Frontend

- Lazy loading
- Code splitting
- Memoization where required

---

# Security Guidelines

- Validate all input
- Sanitize file paths
- Restrict dangerous commands
- Encrypt secrets
- Use JWT authentication

---

# Development Workflow

```
Create Issue

↓

Create Branch

↓

Implement Feature

↓

Local Testing

↓

Update Documentation

↓

Create Pull Request

↓

Code Review

↓

Merge into Develop

↓

Integration Testing

↓

Merge into Main
```

---

# Definition of Done

A task is complete only if

- Feature works
- Tests pass
- Documentation updated
- PR approved
- No critical bugs
- Code reviewed
- Logs verified

---

# Best Practices

Always

- Keep functions small
- Prefer composition over inheritance
- Write readable code
- Keep modules independent
- Use meaningful names

Never

- Duplicate logic
- Hardcode values
- Skip validation
- Ignore exceptions
- Commit secrets

---

# Future Improvements

- Dockerized Development
- CI/CD Pipeline
- Automated Testing
- Static Code Analysis
- Plugin SDK
- Internal Package Registry

---

# Implementation Readiness Checklist

- [ ] Folder structure approved
- [ ] Coding standards approved
- [ ] Naming conventions finalized
- [ ] PR workflow approved
- [ ] Branch strategy approved
- [ ] Logging standards approved
- [ ] Security guidelines reviewed
- [ ] Team responsibilities assigned

**Status:** 🟡 Pending Team Approval

---

# Next Document

**08_DEVELOPMENT_ROADMAP.md**