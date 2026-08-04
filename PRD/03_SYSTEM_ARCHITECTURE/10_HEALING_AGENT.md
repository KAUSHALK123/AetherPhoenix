# 10_HEALING_AGENT.md

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
- 08_WORKER_AGENT.md
- 09_SUPERVISOR_AGENT.md

---

# Purpose

The Healing Agent is responsible for recovering failed workflow execution.

Unlike the Worker, the Healing Agent is allowed to reason about failures.

It analyzes why a task failed, determines the root cause, generates a recovery strategy, produces new executable tasks, and hands those tasks back to the Execution Engine.

The Healing Agent never executes recovery itself.

---

# Design Philosophy

The Healing Agent follows one principle.

> Failures are expected.
>
> Recover intelligently.

Failures should not immediately terminate workflows.

Instead, they should become opportunities for autonomous recovery.

---

# Responsibilities

The Healing Agent is responsible for

- Failure Analysis
- Root Cause Detection
- Recovery Planning
- Retry Strategy
- Generate Recovery Tasks
- Escalation Decision
- Recovery Logging
- Learning Recovery Patterns (Future)

---

# Never Responsible For

Healing never

- Executes tools
- Runs PowerShell
- Opens browsers
- Modifies Planner workflow
- Changes user intent
- Bypasses permissions

---

# Runtime Position

```
Worker

↓

Supervisor

↓

Healing

↓

Execution Engine

↓

Worker
```

Healing always sits between Supervisor and Worker.

---

# Healing Lifecycle

```
Failure Detected

↓

Receive Failure Report

↓

Analyze

↓

Determine Root Cause

↓

Generate Recovery Plan

↓

Generate Recovery Tasks

↓

Submit Tasks

↓

Wait

↓

Monitor Result

↓

Success

OR

Retry Again

OR

Escalate User
```

---

# Healing Pipeline

```
Failure Report

↓

Error Parser

↓

Context Analyzer

↓

Root Cause Analyzer

↓

Recovery Strategy Generator

↓

Task Generator

↓

Validation

↓

Execution Queue

↓

Worker
```

---

# Stage 1 — Failure Report

Healing receives

```
Task ID

Workflow ID

Error Message

Execution Logs

Runtime Metrics

Current State

Artifacts

Tool Used
```

Healing never guesses.

It receives complete execution context.

---

# Stage 2 — Error Parser

Purpose

Normalize errors.

Example

Worker returns

```
Playwright Timeout
```

Parser converts

```
NETWORK_TIMEOUT
```

---

# Supported Categories

Browser

Desktop

Git

Python

PowerShell

OCR

Vision

Filesystem

Network

Permissions

Plugins

Unknown

---

# Stage 3 — Context Analyzer

Collects

- Previous Task
- Current Task
- Next Task
- Runtime State
- Workflow Graph
- Dependency Graph

Healing understands the complete execution context.

---

# Stage 4 — Root Cause Analysis

Determine

Why did the task fail?

Examples

```
Website Offline

↓

Network

```

```
Permission Denied

↓

User Rejected

```

```
Browser Closed

↓

Runtime Failure

```

---

# Root Cause Categories

Infrastructure

Tool

Permission

Network

Runtime

User

Workflow

External API

Unknown

---

# Stage 5 — Recovery Strategy

Healing chooses a strategy.

Examples

Retry

Restart Tool

Wait

Alternative Tool

Alternative Website

Alternative API

Request Permission Again

Escalate User

Cancel Workflow

---

# Recovery Decision Tree

```
Recoverable?

↓

YES

↓

Generate Recovery

↓

Retry

↓

Success
```

---

```
Recoverable?

↓

NO

↓

Escalate User
```

---

# Retry Policy

Maximum Retry

```
5
```

Example

```
Attempt 1

↓

Failed

↓

Attempt 2

↓

Failed

↓

Attempt 3

↓

Success
```

---

# Exponential Backoff

Example

```
Retry 1

5 sec

Retry 2

10 sec

Retry 3

20 sec

Retry 4

40 sec
```

---

# Stage 6 — Recovery Task Generation

Healing generates

Executable Tasks

Examples

```
Restart Browser

↓

Reload Website

↓

Continue
```

```
Restart PowerShell

↓

Execute Command Again
```

---

# Stage 7 — Validation

Healing validates

- Tool Exists
- Permission Exists
- Recovery Safe
- Retry Count

---

# Stage 8 — Queue Submission

Recovery Tasks

↓

Execution Queue

↓

Worker

Healing never executes.

---

# Recovery Types

Automatic

Manual

Hybrid

---

# Automatic Recovery

Examples

Restart Browser

Retry Download

Reconnect Network

Reload File

---

# Manual Recovery

Examples

Insert USB

Connect WiFi

Approve Permission

Restart Computer

Healing explains exactly what the user must do.

---

# Hybrid Recovery

Example

```
Restart VPN

↓

User

↓

Continue Workflow
```

---

# Escalation

Healing escalates when

- Retry Limit Reached
- Unsupported Error
- User Rejected Permission
- Missing Tool
- Hardware Failure

---

# Recovery Report

Healing generates

```
Failure

Root Cause

Recovery

Retry Count

Outcome

Recommendations
```

Stored in database.

---

# Learning Memory (Future)

Healing stores

Successful Recovery

↓

Recovery Library

↓

Future Similar Failure

↓

Reuse Strategy

This improves recovery over time.

---

# Healing State Machine

```
Idle

↓

Analyzing

↓

Planning

↓

Generating Tasks

↓

Waiting

↓

Completed

OR

Escalated
```

---

# State Updates

Healing updates

```
Healing Status

Retry Count

Recovery Tasks

Recovery Logs

Recovery Result
```

---

# Events

Publishes

```
Healing Started

Recovery Planned

Retry Started

Retry Completed

Healing Success

Healing Failed

Escalation Requested
```

---

# Performance Goals

Failure Analysis

<500 ms

Recovery Plan

<2 sec

Task Generation

<500 ms

Retry Submission

<100 ms

---

# Security

Healing must never

- Ignore permissions
- Execute hidden commands
- Delete user files
- Escalate privileges
- Bypass approval

---

# Future Features

- AI Recovery Knowledge Base
- Community Recovery Packs
- Predictive Failure Detection
- Automatic Workflow Optimization
- Recovery Recommendation Engine
- Visual Failure Diagnosis
- Distributed Healing

---

# Design Principles

Healing should always be

- Safe
- Explainable
- Deterministic
- Modular
- Recoverable
- Observable

---

# Acceptance Criteria

Healing is complete when

- Root causes are classified
- Recovery plans are generated
- Recovery tasks are executable
- Retry policy works
- Escalation functions correctly
- Reports are generated
- Workflow resumes successfully

---

# Implementation Readiness Checklist

- [ ] Failure classification approved
- [ ] Recovery pipeline approved
- [ ] Retry strategy approved
- [ ] Recovery task generation approved
- [ ] Escalation strategy approved
- [ ] Learning memory design approved
- [ ] Event publishing approved
- [ ] Security review completed

**Status:** 🟡 Pending Team Approval

---

# Next Document

**11_TOOL_REGISTRY.md**