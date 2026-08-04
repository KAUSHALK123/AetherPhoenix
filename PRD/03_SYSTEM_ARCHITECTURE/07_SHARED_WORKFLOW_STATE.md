# 07_SHARED_WORKFLOW_STATE.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Owner:** Runtime Architecture Team

---

# Related Documents

- 04_ORCHESTRATOR.md
- 05_PLANNER_AGENT.md
- 06_WORKFLOW_COMPILER.md
- 08_WORKER_AGENT.md
- 09_SUPERVISOR_AGENT.md
- 10_HEALING_AGENT.md
- 13_EVENT_BUS.md

---

# Purpose

The Shared Workflow State (SWS) is the central runtime object that coordinates communication between every runtime component.

Instead of allowing agents to communicate directly with one another, every component interacts only through the Shared Workflow State.

The Shared Workflow State acts as the **single source of truth** during workflow execution.

---

# Design Philosophy

One Rule:

> Nobody talks directly.

Every component

```
Reads State

↓

Updates State

↓

Publishes Event
```

No runtime component calls another runtime component directly.

---

# Why Does It Exist?

Without Shared Workflow State

```
Planner

↓

Worker

↓

Supervisor

↓

Healing
```

Problems

- Tight coupling

- Hard debugging

- Impossible replay

- Race conditions

- Hidden state

---

With Shared Workflow State

```
Planner

↓

Shared Workflow State

↓

Execution Engine

↓

Worker

↓

Supervisor

↓

Healing

↓

UI

↓

Database Sync
```

Everything becomes observable.

---

# Runtime Philosophy

Workflow execution should behave like an operating system.

The Shared Workflow State is similar to:

- Redux Store
- Kubernetes Desired State
- LangGraph State
- Operating System Process Table

---

# Responsibilities

The Shared Workflow State owns

- Workflow Status
- Current Task
- Completed Tasks
- Failed Tasks
- Pending Tasks
- Active Worker
- Progress
- Permissions
- Runtime Logs
- Artifacts
- Recovery Status
- Execution Metadata

---

# Never Stores

- AI Prompts
- LLM Internal Thoughts
- Model Weights
- API Keys
- Secrets

---

# High Level Structure

```
Shared Workflow State

│

├── Workflow Metadata

├── Planner Output

├── Execution Queue

├── Runtime State

├── Task State

├── Progress

├── Permissions

├── Artifacts

├── Logs

├── Healing State

├── Runtime Metrics

├── Events

└── UI State
```

---

# Workflow Metadata

Contains

- Workflow ID

- Goal

- Conversation ID

- User ID

- Created Time

- Estimated Duration

- Execution Mode

---

# Planner Section

Stores

- Workflow Specification

- Dependency Graph

- Estimated Time

- Risks

- Required Permissions

- Expected Outputs

Planner writes once.

Never modifies again.

---

# Execution Queue

Stores

```
Ready

Running

Blocked

Completed

Failed

Cancelled
```

Execution Engine owns this section.

---

# Task State

Each task contains

```
Task ID

Status

Priority

Assigned Tool

Assigned Worker

Dependencies

Retry Count

Started Time

Finished Time

Output

Expected Output

Artifact

```

---

# Task Status

Supported

```
CREATED

READY

WAITING

RUNNING

PAUSED

FAILED

HEALING

COMPLETED

CANCELLED
```

---

# Progress State

Stores

```
Total Tasks

Completed

Running

Failed

Pending

Overall %

Estimated Remaining Time
```

Used directly by UI.

---

# Permission State

Stores

```
Permission Type

Reason

Risk Level

Approved

Rejected

Expires

```

Permission Manager owns this section.

---

# Artifact State

Stores

Generated

- PPT

- PDF

- Reports

- Images

- Logs

- Code

- ZIP

Each artifact stores

```
Name

Location

Size

Checksum

Created Time

```

---

# Runtime Log State

Stores

Every runtime event.

Example

```
10:00

Planner Finished

10:01

Worker Started

10:02

Browser Opened

10:03

Task Completed
```

---

# Healing State

Stores

```
Root Cause

Recovery Strategy

Retry Count

Recovery Result

```

Healing Agent owns this section.

---

# Runtime Metrics

Stores

```
Execution Time

Memory Usage

CPU Usage

Browser Count

Running Workers

Current Tool
```

Future

GPU Usage

---

# Event State

Every event generated during execution.

Examples

```
WorkflowCreated

WorkflowStarted

PlanningCompleted

TaskStarted

TaskCompleted

HealingStarted

HealingFinished

WorkflowCompleted
```

---

# UI State

Frontend reads

```
Workflow Status

Current Task

Progress

Logs

Timeline

Artifacts

Estimated Time

```

No API polling required.

WebSocket updates automatically.

---

# State Ownership

| Section | Owner |
|----------|-------|
| Workflow | Planner |
| Queue | Execution Engine |
| Tasks | Worker |
| Progress | Execution Engine |
| Permissions | Permission Manager |
| Logs | Runtime Kernel |
| Healing | Healing Agent |
| Artifacts | Artifact Manager |
| Metrics | Runtime Kernel |

Only owners may modify their section.

Everyone else has read-only access.

---

# State Update Rules

Every update follows

```
Read

↓

Validate

↓

Modify

↓

Publish Event

↓

Save Snapshot

```

---

# Immutable Updates

Runtime components should never modify objects directly.

Instead

```
Old State

↓

Copy

↓

Modify Copy

↓

Replace

```

Benefits

- Undo

- Replay

- Debugging

- Thread Safety

---

# Snapshot System

Snapshots created

- Workflow Start

- Planning Complete

- Before Execution

- Before Healing

- Workflow Complete

Future

Resume from snapshots.

---

# Database Synchronization

Runtime State

↓

Sync Service

↓

SQLite

Database is **not** the runtime.

Database stores history.

Runtime stores live execution.

---

# Event Synchronization

Every state update

↓

Publishes Event

↓

Frontend

↓

Supervisor

↓

Logs

↓

Analytics

---

# Thread Safety

Multiple Workers may update the state simultaneously.

Rules

- Atomic Updates

- Lock per Workflow

- No Global Locks

- Version Numbers

---

# Parallel Execution Example

```
Research

├── Images

├── References

├── Outline

↓

Merge

↓

Slides
```

Each parallel task updates only its own task state.

---

# Rollback State

Stores

```
Rollback Point

Changed Files

Changed Registry

Changed Variables

Previous Values
```

Rollback Manager owns this section.

---

# Cleanup

Workflow Finished

↓

Archive Snapshot

↓

Persist Database

↓

Release Memory

↓

Destroy Runtime State

---

# Security

Never expose

- Secrets

- Passwords

- Tokens

- Internal Prompts

- Hidden Reasoning

State visible to UI should contain only execution information.

---

# Performance Goals

State Read

<10 ms

State Write

<20 ms

Snapshot

<100 ms

WebSocket Update

<50 ms

---

# Future Features

- Distributed State

- Cloud Sync

- Multi-Device Runtime

- Worker Pool

- Live Collaboration

- Runtime Replay

- Time Travel Debugging

---

# Design Principles

The Shared Workflow State must always be

- Immutable

- Observable

- Predictable

- Serializable

- Recoverable

- Thread Safe

- Event Driven

---

# Runtime Contract

Every runtime component must follow

```
Read State

↓

Validate

↓

Update Own Section

↓

Publish Event

↓

Return
```

Breaking this contract results in undefined runtime behavior.

---

# Implementation Readiness Checklist

- [ ] State structure approved

- [ ] Ownership approved

- [ ] Snapshot strategy approved

- [ ] Thread safety approved

- [ ] Event synchronization approved

- [ ] Database synchronization approved

- [ ] Rollback state approved

- [ ] Runtime contract approved

Status: 🟡 Pending Team Approval

---

# Next Document

08_WORKER_AGENT.md
