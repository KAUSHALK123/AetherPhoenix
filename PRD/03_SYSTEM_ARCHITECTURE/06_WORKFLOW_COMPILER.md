# 06_WORKFLOW_COMPILER.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Owner:** AI Architecture Team

---

# Related Documents

- 05_PLANNER_AGENT.md
- 07_SHARED_WORKFLOW_STATE.md
- 08_WORKER_AGENT.md
- 11_TOOL_REGISTRY.md

---

# Purpose

The Workflow Compiler acts as the bridge between AI reasoning and deterministic execution.

The Planner produces an intelligent workflow specification.

The Workflow Compiler transforms that specification into executable runtime instructions that the Worker can execute without making decisions.

The compiler guarantees correctness before execution begins.

---

# Design Philosophy

The Workflow Compiler follows one principle:

> Validate once. Execute many.

The Worker should never validate or interpret the workflow.

Every executable task should already be complete, verified, and deterministic.

---

# Why a Workflow Compiler?

Without a compiler:

```
Planner

↓

Worker
```

Problems

- Worker must interpret instructions
- Different workers may behave differently
- Difficult to debug
- Hard to retry
- Hidden assumptions

---

With a compiler:

```
Planner

↓

Workflow Compiler

↓

Executable Workflow

↓

Worker
```

Benefits

- Deterministic execution
- Consistent task format
- Easier testing
- Easier debugging
- Better validation
- Language-independent execution

---

# Compiler Responsibilities

The Workflow Compiler is responsible for:

- Validate workflow specification
- Validate schema
- Generate workflow ID
- Generate task IDs
- Build dependency graph (DAG)
- Detect circular dependencies
- Generate execution metadata
- Generate retry metadata
- Validate tool availability
- Validate permissions
- Validate outputs
- Generate executable tasks

---

# Compiler Never

The compiler never:

- Executes tasks
- Makes AI decisions
- Asks clarification questions
- Heals workflows
- Changes user intent

---

# Compiler Pipeline

```
Workflow Specification

↓

Schema Validation

↓

Capability Validation

↓

Permission Validation

↓

Dependency Validation

↓

Tool Resolution

↓

Task Normalization

↓

Task ID Generation

↓

DAG Builder

↓

Retry Metadata

↓

Execution Metadata

↓

Compiled Workflow
```

---

# Stage 1 — Schema Validation

Purpose

Ensure Planner output follows the required Pydantic schema.

Checks

- Required fields
- Data types
- Enum values
- Missing values
- Duplicate IDs

---

# Stage 2 — Capability Validation

Verify that every requested capability exists.

Example

Planner requests

```
Generate PPT
```

Compiler checks

```
Capability Registry

↓

PPT Available

↓

Yes
```

If unavailable

↓

Compilation Error

---

# Stage 3 — Permission Validation

Purpose

Ensure required permissions are defined.

Example

```
PowerShell

↓

Permission Required

↓

YES
```

Compiler attaches permission metadata to the workflow.

---

# Stage 4 — Dependency Validation

Purpose

Validate task ordering.

Checks

- Missing dependencies
- Invalid dependency IDs
- Duplicate dependencies
- Circular dependencies

---

# Circular Dependency Detection

Invalid

```
Task A

↓

Task B

↓

Task C

↓

Task A
```

Compilation stops immediately.

---

# Stage 5 — Tool Resolution

Planner selects capabilities.

Compiler resolves actual tools.

Example

Capability

```
Research
```

Resolved Tool

```
Browser Tool
```

---

# Stage 6 — Task Normalization

Purpose

Convert every task into a standard execution format.

Every task should have

- ID
- Name
- Description
- Inputs
- Outputs
- Tool
- Priority
- Retry Policy
- Estimated Time
- Dependencies
- Status

---

# Stage 7 — Task ID Generation

Every task receives a globally unique identifier.

Example

```
TASK-001

TASK-002

TASK-003
```

The Worker never generates IDs.

---

# Stage 8 — DAG Builder

Purpose

Build a Directed Acyclic Graph.

Example

```
Research

↓

Generate Content

↓

Generate Slides

↓

Export PPT

↓

Export PDF
```

Parallel Example

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

---

# Stage 9 — Retry Metadata

Compiler assigns retry information.

Example

```
Retry Count

↓

5

↓

Exponential Backoff

↓

Healing Strategy
```

The Worker does not decide retry behavior.

---

# Stage 10 — Execution Metadata

Compiler generates

- Estimated Runtime
- Priority
- Resource Requirements
- Required Permissions
- Expected Outputs

---

# Compiled Workflow

Every compiled workflow contains

Workflow Metadata

↓

Execution Metadata

↓

Task List

↓

Dependencies

↓

Permissions

↓

Retry Policies

↓

Expected Artifacts

↓

Validation Summary

---

# Compiled Task Structure

Every task contains

```
Task ID

Title

Description

Assigned Tool

Execution Type

Inputs

Outputs

Dependencies

Priority

Risk Level

Estimated Time

Retry Policy

Permission Requirement

Expected Artifact

Status
```

This structure is identical for every task.

---

# Execution Types

Supported execution types

- Sequential
- Parallel
- Conditional
- Manual Approval
- Background

Future

- Scheduled
- Event Triggered

---

# Validation Rules

The compiler rejects workflows that contain

- Missing tools
- Missing permissions
- Circular dependencies
- Duplicate task IDs
- Unsupported capabilities
- Invalid outputs

---

# Compiler Output

The Worker receives

ONLY

Compiled Workflow

Never Planner Output

---

# Error Handling

Compilation Errors

Examples

```
Missing Tool

Circular Dependency

Invalid Permission

Unknown Capability

Schema Error
```

Compilation never proceeds after validation failure.

---

# Performance Goals

Compilation Time

< 500 ms

Schema Validation

< 100 ms

Dependency Analysis

< 100 ms

Tool Resolution

< 100 ms

---

# Future Features

- Workflow Optimization
- Automatic Task Merging
- Cost Optimization
- AI-Assisted Compilation
- Distributed Workflow Compilation
- Workflow Compression

---

# Design Principles

The Workflow Compiler must always be

- Deterministic
- Stateless
- Testable
- Predictable
- Fast
- Explainable

---

# Implementation Readiness Checklist

- [ ] Compiler pipeline approved
- [ ] Validation rules approved
- [ ] DAG generation approved
- [ ] Task schema approved
- [ ] Retry metadata approved
- [ ] Execution metadata approved
- [ ] Error handling approved

**Status:** 🟡 Pending Team Approval

---

# Next Document

**07_SHARED_WORKFLOW_STATE.md**