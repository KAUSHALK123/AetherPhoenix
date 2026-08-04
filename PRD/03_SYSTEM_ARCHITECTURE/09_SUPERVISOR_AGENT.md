# 09_SUPERVISOR_AGENT.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Owner:** Runtime Architecture Team

---

# Related Documents

- 04_ORCHESTRATOR.md
- 07_SHARED_WORKFLOW_STATE.md
- 08_WORKER_AGENT.md
- 10_HEALING_AGENT.md
- 13_EVENT_BUS.md

---

# Purpose

The Supervisor Agent is responsible for monitoring every workflow execution and ensuring that each task has completed correctly before allowing the workflow to continue.

The Supervisor acts as the **Quality Assurance (QA) layer** of the runtime.

It continuously observes execution, validates outputs, detects failures, and determines whether the workflow should:

- Continue
- Wait
- Pause
- Trigger Healing
- Escalate to the User

---

# Design Philosophy

The Supervisor follows one principle.

> Trust nothing. Verify everything.

Every completed task must be validated.

Nothing proceeds without verification.

---

# Responsibilities

The Supervisor is responsible for

- Monitor workflow execution
- Validate task completion
- Verify generated artifacts
- Detect execution failures
- Detect incorrect outputs
- Detect missing outputs
- Detect timeouts
- Detect stuck workflows
- Monitor parallel execution
- Publish validation reports
- Trigger Healing when required

---

# Never Responsible For

The Supervisor never

- Plans workflows
- Executes tasks
- Calls tools
- Retries execution
- Modifies workflows
- Changes task order

---

# Internal Modules

```
Supervisor

├── Task Monitor
├── Output Validator
├── Artifact Validator
├── Timeout Detector
├── Parallel Monitor
├── Dependency Checker
├── State Validator
├── Failure Detector
├── Report Generator
└── Healing Dispatcher
```

---

# Runtime Position

```
Execution Engine

↓

Worker

↓

Supervisor

↓

Shared Workflow State

↓

Orchestrator
```

The Worker finishes execution.

The Supervisor decides if execution was actually successful.

---

# Supervisor Lifecycle

```
Wait

↓

Receive Task Result

↓

Validate

↓

Generate Report

↓

Decision

↓

Publish Event

↓

Idle
```

---

# Validation Pipeline

```
Execution Result

↓

Schema Validation

↓

Output Validation

↓

Artifact Validation

↓

Dependency Validation

↓

Runtime Validation

↓

Decision
```

---

# Step 1 — Task Monitoring

Supervisor waits for

```
TaskCompleted Event
```

It never polls the Worker directly.

---

# Step 2 — Schema Validation

Checks

- Task ID
- Output Format
- Status
- Exit Code
- Metadata

Rejects malformed results immediately.

---

# Step 3 — Output Validation

Verify

Expected Output

↓

Actual Output

Example

Expected

```
slides.pptx
```

Actual

```
slides.pptx
```

Success

---

Expected

```
report.pdf
```

Actual

```
NULL
```

Failure

---

# Step 4 — Artifact Validation

Checks

- File Exists
- Correct Size
- Readable
- Not Empty
- Correct Format

Example

```
presentation.pptx

↓

Exists

↓

Readable

↓

Valid
```

---

# Step 5 — Dependency Validation

Ensure dependent tasks have completed.

Example

```
Slides

↓

PDF Export
```

PDF export cannot succeed if slides are missing.

---

# Step 6 — Runtime Validation

Checks

- Task Duration
- Memory Usage
- Exit Codes
- Unexpected Warnings
- Tool Health

---

# Step 7 — Timeout Detection

Example

Expected

```
30 seconds
```

Actual

```
5 minutes
```

↓

Timeout Detected

↓

Healing

---

# Parallel Workflow Monitoring

Example

```
Research

├── Images

├── References

├── Outline

↓

Merge
```

The merge task starts only after every parallel branch is validated.

---

# Failure Detection

Recoverable

- Browser Timeout
- Temporary Network Error
- File Locked
- Retryable API Failure

Non-Recoverable

- Invalid Workflow
- Missing Tool
- Invalid Permission
- Unsupported Capability

Supervisor classifies every failure.

Healing decides recovery.

---

# Validation Report

Every completed task generates

```
Task ID

Status

Validation Result

Artifacts

Warnings

Errors

Metrics

Decision
```

---

# Decision Engine

Possible outcomes

```
Continue

↓

Healing

↓

Pause

↓

Cancel

↓

Escalate User
```

---

# Healing Trigger

Supervisor creates

```
Failure Report

↓

Root Cause Candidates

↓

Execution Context

↓

Logs

↓

Artifacts

↓

Healing Agent
```

Healing receives complete context.

---

# State Synchronization

Supervisor updates

```
Shared Workflow State

↓

Task Status

↓

Workflow Progress

↓

Validation Result
```

---

# Event Publishing

Examples

```
TaskValidated

TaskRejected

WorkflowHealthy

WorkflowFailed

HealingRequested

TimeoutDetected

ArtifactVerified
```

---

# Logging

Supervisor records

- Validation Time
- Validation Result
- Runtime Metrics
- Decision
- Healing Requests

---

# Performance Goals

Validation

<100 ms

Artifact Validation

<200 ms

Decision Generation

<50 ms

Failure Classification

<100 ms

---

# Security

Supervisor verifies

- Permission Compliance
- Tool Compliance
- Execution Integrity
- Artifact Integrity

---

# Future Features

- AI-Based Validation
- Automatic Screenshot Comparison
- Visual Output Verification
- OCR-Based Validation
- Workflow Quality Scoring
- Performance Benchmarking
- Intelligent Timeout Prediction

---

# Design Principles

The Supervisor must always be

- Independent
- Deterministic
- Fast
- Observable
- Explainable
- Reliable

---

# Supervisor State Machine

```
Idle

↓

Monitoring

↓

Validating

↓

Decision

↓

Publishing

↓

Idle
```

---

# Communication Contract

Supervisor communicates only through

- Shared Workflow State
- Event Bus

Never directly with

- Planner
- Worker
- Tools

---

# Acceptance Criteria

The Supervisor is complete when

- Every task is validated
- Every artifact is verified
- Every timeout is detected
- Every failure is classified
- Healing receives complete reports
- Runtime metrics are recorded
- Workflow quality is guaranteed

---

# Implementation Readiness Checklist

- [ ] Validation pipeline approved
- [ ] Failure classification approved
- [ ] Timeout strategy approved
- [ ] Artifact validation approved
- [ ] Parallel monitoring approved
- [ ] Healing trigger approved
- [ ] Runtime metrics approved
- [ ] Event publishing approved

**Status:** 🟡 Pending Team Approval

---

# Next Document

**10_HEALING_AGENT.md**