# 04_ORCHESTRATOR.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Owner:** Architecture Team

---

# Related Documents

- 03_RUNTIME_COMPONENTS.md
- 05_PLANNER_AGENT.md
- 06_WORKFLOW_COMPILER.md
- 07_SHARED_WORKFLOW_STATE.md
- 13_EVENT_BUS.md

---

# Purpose

The Orchestrator is the central runtime coordinator responsible for managing the lifecycle of every workflow.

It is **NOT** an AI agent.

It performs **zero reasoning**.

Its only responsibility is coordinating execution between runtime components.

Think of it as the operating system scheduler for the AI platform.

---

# Design Philosophy

The Orchestrator answers one question repeatedly:

> **What should happen next?**

It never answers

> **How should this task be performed?**

That responsibility belongs to other components.

---

# Why Does The Orchestrator Exist?

Without an Orchestrator:

- Components become tightly coupled.
- Planner would call Worker directly.
- Worker would know Supervisor.
- Healing would communicate with Planner.
- Runtime becomes impossible to debug.

Instead

```
Planner

↓

Workflow State

↓

Orchestrator

↓

Execution Engine

↓

Worker

↓

Supervisor

↓

Healing
```

Everything flows through one coordinator.

---

# Responsibilities

The Orchestrator owns:

- Workflow Lifecycle
- Workflow Scheduling
- Task Scheduling
- State Synchronization
- Event Dispatching
- Workflow Queue
- Execution Queue
- Cancellation
- Pause
- Resume
- Cleanup
- Recovery Routing

---

# Never Responsible For

The Orchestrator NEVER

- Plans workflows
- Executes tasks
- Calls Playwright
- Generates prompts
- Recovers failures
- Makes AI decisions

---

# Internal Modules

```
Orchestrator

├── Workflow Manager
├── Workflow Scheduler
├── Task Scheduler
├── Execution Queue
├── Lifecycle Manager
├── Pause Manager
├── Resume Manager
├── Cancellation Manager
├── Timeout Manager
├── Cleanup Manager
├── Checkpoint Manager
└── Event Dispatcher
```

Each module has exactly one responsibility.

---

# Workflow Lifecycle

```
Created

↓

Planning

↓

Compiled

↓

Waiting Approval

↓

Queued

↓

Running

↓

Paused

↓

Healing

↓

Running

↓

Completed

↓

Archived
```

---

# Workflow States

| State | Description |
|---------|------------|
| CREATED | Workflow initialized |
| PLANNING | Planner generating workflow |
| COMPILING | Workflow Compiler validating |
| WAITING_PERMISSION | Waiting for user approval |
| READY | Ready to execute |
| RUNNING | Active execution |
| PAUSED | User paused |
| HEALING | Recovery active |
| COMPLETED | Successfully finished |
| FAILED | Unrecoverable failure |
| CANCELLED | Cancelled by user |
| ARCHIVED | Stored in history |

---

# Workflow Scheduler

Purpose

Determine which workflow should execute next.

---

Responsibilities

- Maintain workflow queue
- Priority ordering
- Resume paused workflows
- Queue new workflows
- Cancel workflows

---

Example

```
Workflow 1

Running

Workflow 2

Waiting

Workflow 3

Paused
```

---

# Task Scheduler

Purpose

Determine which task executes next.

---

Responsibilities

- Read DAG
- Check Dependencies
- Detect Parallel Tasks
- Queue Ready Tasks
- Delay Blocked Tasks

---

Example

```
Research

↓

Generate Text

↓

Generate PPT

↓

Export PDF
```

Only executable tasks enter the Execution Queue.

---

# Execution Queue

Purpose

Store tasks waiting for execution.

---

Queue Example

```
Task 1

Task 2

Task 3
```

Future

Priority Queue

```
High

↓

Medium

↓

Low
```

---

# Priority Levels

```
Critical

High

Medium

Low

Background
```

Planner assigns priority.

Orchestrator respects it.

---

# Lifecycle Manager

Responsibilities

- Create Workflow
- Update Status
- Complete Workflow
- Archive Workflow

---

# Pause Manager

Supports

```
Pause Workflow
```

Behavior

- Stop scheduling new tasks.
- Preserve current state.
- Resume from checkpoint.

---

# Resume Manager

Supports

```
Resume Workflow
```

Behavior

Restore

↓

Shared State

↓

Execution Queue

↓

Continue

---

# Cancellation Manager

Supports

```
Cancel Workflow
```

Behavior

- Stop execution.
- Release resources.
- Archive logs.
- Store artifacts.

---

# Timeout Manager

Purpose

Prevent infinite execution.

---

Responsibilities

- Detect stalled tasks.
- Detect deadlocks.
- Trigger Healing.

---

Example

```
Task Timeout

↓

Supervisor

↓

Healing
```

---

# Checkpoint Manager

Purpose

Create recovery checkpoints.

---

Stores

- Current Task
- Completed Tasks
- Shared State
- Execution Queue

Future

Resume after application restart.

---

# Cleanup Manager

Runs after workflow completion.

Responsibilities

- Free Memory
- Archive Workflow
- Store Artifacts
- Delete Temporary Files

---

# Event Dispatcher

Publishes runtime events.

Examples

```
Workflow Started

Workflow Paused

Workflow Resumed

Workflow Cancelled

Task Started

Task Completed

Healing Started

Healing Finished
```

---

# Workflow Creation

```
User Request

↓

Session Manager

↓

Planner

↓

Workflow Compiler

↓

Orchestrator

↓

Execution Queue
```

---

# Execution Flow

```
Execution Queue

↓

Execution Engine

↓

Worker

↓

Supervisor

↓

Workflow State

↓

Orchestrator

↓

Next Task
```

---

# Recovery Flow

```
Worker Failed

↓

Supervisor

↓

Healing

↓

Recovery Task

↓

Execution Queue

↓

Worker Retry
```

Planner is NOT recalled.

---

# Parallel Execution

Future Versions

```
Task A

↓

Worker 1

Task B

↓

Worker 2

Task C

↓

Worker 3
```

The Orchestrator coordinates synchronization.

---

# Resource Management

Future

Track

- CPU Usage
- Memory Usage
- Browser Instances
- Active Tools
- Network Usage

Prevent system overload.

---

# Safety Rules

The Orchestrator never bypasses

- Permission Manager
- Rollback Manager
- Shared Workflow State

---

# Communication Rules

The Orchestrator communicates through

- Shared Workflow State
- Event Bus

Never directly with tools.

---

# Inputs

- Compiled Workflow
- Workflow Events
- Shared State Updates
- User Commands

---

# Outputs

- Execution Queue
- Runtime Events
- Workflow Status
- Scheduling Decisions

---

# Error Handling

If an internal runtime error occurs

```
Pause Workflow

↓

Log Error

↓

Notify User

↓

Create Recovery Report
```

---

# Performance Targets

Workflow Scheduling

<100 ms

Task Scheduling

<50 ms

Pause

<100 ms

Resume

<100 ms

Cancellation

<200 ms

---

# Future Improvements

- Distributed Scheduler
- Worker Pool
- Multi-Device Execution
- Cloud Runtime
- AI Load Balancer
- Workflow Prioritization AI
- Background Scheduling

---

# Design Principles

The Orchestrator must always remain

- Deterministic
- Stateless where possible
- Event-driven
- Thread-safe
- Extensible
- Testable

---

# Implementation Readiness Checklist

- [ ] Workflow lifecycle approved
- [ ] Scheduler approved
- [ ] Queue design approved
- [ ] Timeout strategy approved
- [ ] Pause/Resume approved
- [ ] Event Dispatcher approved
- [ ] Checkpoint strategy approved
- [ ] Cleanup strategy approved

**Status:** 🟡 Pending Team Approval

---

# Next Document

**05_PLANNER_AGENT.md**