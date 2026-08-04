# 08_WORKER_AGENT.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Owner:** AI Runtime Team

---

# Related Documents

- 04_ORCHESTRATOR.md
- 05_PLANNER_AGENT.md
- 06_WORKFLOW_COMPILER.md
- 07_SHARED_WORKFLOW_STATE.md
- 09_SUPERVISOR_AGENT.md
- 11_TOOL_REGISTRY.md

---

# Purpose

The Worker Agent is responsible for executing compiled workflow tasks.

It never performs reasoning.

It never modifies workflow logic.

It never decides what to do next.

It simply receives executable tasks from the Execution Engine and executes them using registered tools.

---

# Worker Philosophy

One Principle

> Execute exactly what was planned.

Never

- Think
- Guess
- Reorder tasks
- Skip tasks
- Retry automatically
- Modify workflow

---

# Worker Architecture

```
Compiled Task

↓

Execution Engine

↓

Worker Agent

↓

Tool Adapter

↓

Registered Tool

↓

Operating System

↓

Execution Result

↓

Shared Workflow State
```

---

# Responsibilities

The Worker is responsible for

- Receive compiled task
- Validate task format
- Load required tool
- Execute task
- Collect outputs
- Capture logs
- Capture execution metrics
- Return execution result
- Update Shared Workflow State

---

# Never Responsible For

The Worker must never

- Plan workflows
- Ask user questions
- Retry failed tasks
- Heal workflows
- Reorder execution
- Skip permissions
- Modify planner output

---

# Internal Modules

```
Worker Agent

├── Task Receiver
├── Task Validator
├── Tool Loader
├── Tool Executor
├── Output Collector
├── Artifact Collector
├── Metrics Collector
├── Log Collector
└── Result Publisher
```

---

# Worker Lifecycle

```
Receive Task

↓

Validate

↓

Load Tool

↓

Execute

↓

Capture Output

↓

Collect Metrics

↓

Publish Result

↓

Idle
```

---

# Step 1 — Task Reception

Input

Compiled Task

Checks

- Task ID
- Tool
- Dependencies
- Permissions
- Inputs

If validation fails

↓

Reject Task

↓

Notify Supervisor

---

# Step 2 — Tool Resolution

Worker requests

```
Tool Registry

↓

Browser Tool

↓

Version

↓

Health

↓

Ready
```

If unavailable

↓

Execution Failure

---

# Step 3 — Permission Check

Before execution

Worker checks

```
Permission State

↓

Approved?

↓

Yes

↓

Execute
```

If denied

↓

Task Cancelled

---

# Step 4 — Tool Initialization

Examples

Browser

↓

Launch Browser

PowerShell

↓

Create Session

Python

↓

Create Runtime

OCR

↓

Load Model

---

# Step 5 — Execution

Worker executes exactly one task.

Example

```
Task

↓

Open Browser

↓

Navigate URL

↓

Capture Data

↓

Return
```

Worker never chains unrelated tasks.

---

# Step 6 — Output Collection

Outputs may include

- Text
- Images
- Files
- JSON
- Screenshots
- Logs
- Exit Codes

---

# Step 7 — Artifact Collection

Generated artifacts

Examples

```
slides.pptx

report.pdf

output.py

image.png

logs.txt
```

Artifacts are registered with the Artifact Manager.

---

# Step 8 — Metrics Collection

Worker records

- Start Time
- End Time
- Duration
- Tool Used
- Memory Usage
- CPU Usage
- Exit Code

---

# Step 9 — Result Publishing

Worker updates

Shared Workflow State

↓

Execution Result

↓

Event Bus

↓

Supervisor

---

# Worker State Machine

```
Idle

↓

Waiting

↓

Preparing

↓

Executing

↓

Collecting

↓

Publishing

↓

Completed

↓

Idle
```

---

# Supported Task Types

- Browser Automation
- Desktop Automation
- File Operations
- Web Research
- OCR
- Vision
- Git
- PowerShell
- Python
- PPT Generation
- PDF Generation
- Code Generation
- File Compression
- Search

---

# Browser Workflow Example

```
Receive Task

↓

Browser Adapter

↓

Playwright

↓

Navigate

↓

Extract Data

↓

Return HTML

↓

Worker
```

---

# Desktop Workflow Example

```
Receive Task

↓

Desktop Adapter

↓

pywinauto

↓

Click

↓

Type

↓

Capture Result

↓

Worker
```

---

# Git Workflow Example

```
Receive Task

↓

Git Adapter

↓

GitPython

↓

Execute

↓

Collect Result
```

---

# PowerShell Workflow Example

```
Receive Task

↓

Permission Check

↓

PowerShell Adapter

↓

Execute

↓

Capture Output
```

---

# Error Categories

Recoverable

- Browser Timeout
- Network Failure
- Temporary File Lock
- Retryable API Error

Non-Recoverable

- Missing Tool
- Permission Denied
- Invalid Task
- Unsupported Capability

Worker reports errors.

Healing decides recovery.

---

# Worker Output

Worker returns

```
Task ID

Status

Output

Artifacts

Execution Time

Logs

Metrics

Exit Code

Errors
```

Worker never returns natural language reasoning.

---

# Logging

Every execution logs

- Tool
- Duration
- Task
- Inputs
- Outputs
- Errors
- Artifacts

---

# Security Rules

Worker must

- Never bypass permissions
- Never elevate privileges
- Never expose secrets
- Never modify compiled tasks
- Never execute unknown tools

---

# Performance Goals

Task Validation

<20 ms

Tool Resolution

<50 ms

Execution Startup

<100 ms

State Update

<20 ms

---

# Future Worker Features

- Worker Pool
- Remote Workers
- Cloud Workers
- GPU Workers
- Distributed Execution
- Containerized Workers
- Background Workers

---

# Design Principles

Worker should always remain

- Deterministic
- Stateless
- Modular
- Replaceable
- Observable
- Secure
- Fast

---

# Worker Contract

Every execution follows

```
Receive Task

↓

Validate

↓

Load Tool

↓

Execute

↓

Collect Output

↓

Publish Result

↓

Return
```

No exceptions.

---

# Implementation Readiness Checklist

- [ ] Worker lifecycle approved
- [ ] Execution pipeline approved
- [ ] Tool loading strategy approved
- [ ] Security rules approved
- [ ] Output schema approved
- [ ] Metrics collection approved
- [ ] Logging strategy approved
- [ ] Error categorization approved

**Status:** 🟡 Pending Team Approval

---

# Next Document

**09_SUPERVISOR_AGENT.md**