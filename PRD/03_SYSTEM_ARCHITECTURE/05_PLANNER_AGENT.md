# 05_PLANNER_AGENT.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Owner:** AI Architecture Team

---

# Related Documents

- 04_ORCHESTRATOR.md
- 06_WORKFLOW_COMPILER.md
- 07_SHARED_WORKFLOW_STATE.md
- 08_WORKER_AGENT.md
- 11_TOOL_REGISTRY.md

---

# Purpose

The Planner Agent is the intelligence layer responsible for transforming ambiguous human requests into deterministic execution workflows.

The Planner **never executes tasks**.

Its sole responsibility is to understand the user's intent, ask clarifying questions when required, analyze risks, discover available capabilities, construct an execution strategy, and generate a structured workflow specification that can later be compiled into executable runtime tasks.

The Planner is the only AI component responsible for reasoning about *what should be done*.

---

# Design Philosophy

The Planner follows one core principle:

> Think completely before execution begins.

Execution should never require additional reasoning.

The Planner must eliminate ambiguity before the Worker starts.

---

# Planner Responsibilities

The Planner is responsible for:

- Understanding user intent
- Identifying workflow objectives
- Asking clarification questions
- Discovering available capabilities
- Detecting unavailable features
- Estimating execution complexity
- Detecting risks
- Determining required permissions
- Creating dependency graphs
- Planning parallel execution
- Generating execution summaries
- Producing structured workflow specifications

---

# Planner Never

The Planner must never:

- Execute tools
- Open browsers
- Execute terminal commands
- Retry failures
- Heal workflows
- Modify runtime state
- Skip clarification when confidence is low

---

# Planner Pipeline

The Planner is internally divided into multiple logical stages.

```
User Goal

↓

Intent Analyzer

↓

Context Analyzer

↓

Conversation Analyzer

↓

Goal Validator

↓

Clarification Engine

↓

Capability Discovery

↓

Tool Discovery

↓

Risk Analysis

↓

Permission Prediction

↓

Dependency Planner

↓

Parallel Planner

↓

Workflow Optimizer

↓

Time Estimator

↓

Cost Estimator

↓

Workflow Validator

↓

Execution Summary Generator

↓

Workflow Specification
```

Each stage performs one responsibility.

---

# Stage 1 — Intent Analyzer

Purpose

Determine the primary objective.

Examples

```
Create PowerPoint

Research Topic

Fix Windows

Write Code

Install Software

Organize Files
```

Outputs

- Intent
- Confidence Score

---

# Stage 2 — Context Analyzer

Purpose

Understand contextual information.

Example

```
User uploaded image

↓

Windows Error Screenshot

↓

Task Context

↓

Driver Troubleshooting
```

Context Sources

- Images
- Files
- Previous Conversation
- Current Prompt

---

# Stage 3 — Conversation Analyzer

Purpose

Understand ongoing conversation.

Determine

- Previous tasks
- Previous workflows
- Existing outputs
- Existing artifacts

---

# Stage 4 — Goal Validator

Purpose

Check if the request is valid.

Examples

Supported

```
Create a PPT

Fix WiFi

Research AI
```

Unsupported

```
Hack a bank

Delete Windows
```

Unsupported goals are rejected immediately.

---

# Stage 5 — Clarification Engine

Purpose

Remove ambiguity.

Example

User

```
Create PPT
```

Planner asks

- Number of slides?
- Presentation style?
- Theme?
- Images?
- Speaker notes?
- Output format?

Planner continues asking until confidence exceeds the configured threshold.

---

# Confidence Score

Planner computes a confidence score.

Example

```
User Goal

↓

Confidence

↓

0.42

↓

Needs Clarification
```

Threshold

```
>= 0.90

Proceed

< 0.90

Ask Questions
```

---

# Stage 6 — Capability Discovery

Purpose

Discover available platform capabilities.

Examples

```
Browser

Desktop

OCR

PowerShell

Git

Vision

Python

PPT

PDF
```

Planner must never plan unsupported workflows.

---

# Stage 7 — Tool Discovery

Purpose

Identify required tools.

Example

```
PPT

↓

Research Tool

↓

Browser Tool

↓

PPT Tool

↓

PDF Tool
```

---

# Stage 8 — Risk Analysis

Purpose

Detect workflow risks.

Risk Levels

- Safe
- Low
- Medium
- High
- Critical

Examples

Safe

```
Research
```

Medium

```
Delete Files
```

Critical

```
Registry

Drivers

System Restore
```

---

# Stage 9 — Permission Prediction

Planner predicts required permissions.

Examples

Browser

Internet

Downloads

PowerShell

Administrator

Clipboard

Desktop

Permissions are requested before execution.

---

# Stage 10 — Dependency Planner

Purpose

Determine execution order.

Example

```
Research

↓

Summary

↓

Slides

↓

PDF
```

Dependencies become a DAG.

---

# Stage 11 — Parallel Planner

Purpose

Identify tasks that can execute simultaneously.

Example

```
Research

↓

├── Download Images

├── Collect References

├── Create Outline

↓

Merge Results
```

---

# Stage 12 — Workflow Optimizer

Purpose

Reduce execution time.

Strategies

- Merge duplicate tasks
- Parallel execution
- Remove unnecessary operations
- Cache reusable outputs

---

# Stage 13 — Time Estimator

Purpose

Predict execution duration.

Example

```
Research

2 min

Images

1 min

Slides

3 min

Export

30 sec
```

Estimated Total

```
6.5 minutes
```

---

# Stage 14 — Cost Estimator

Future Component.

Estimate

- LLM Tokens
- API Calls
- Browser Sessions
- Processing Time

Useful for cloud deployments.

---

# Stage 15 — Workflow Validator

Purpose

Validate workflow correctness.

Checks

- Missing dependencies
- Unsupported tools
- Circular dependencies
- Invalid permissions
- Invalid outputs

---

# Stage 16 — Execution Summary Generator

Generates

- Goal
- Total Tasks
- Estimated Time
- Risks
- Permissions
- Expected Outputs

Shown to the user before execution.

---

# Planner Output

The Planner never returns plain text.

Instead it returns a structured **Workflow Specification**.

```
Workflow

↓

Metadata

↓

Tasks

↓

Dependencies

↓

Permissions

↓

Risks

↓

Artifacts

↓

Execution Summary
```

---

# Planner State Machine

```
Idle

↓

Understanding

↓

Clarifying

↓

Planning

↓

Validating

↓

Completed
```

Planner exits after workflow generation.

---

# Hallucination Prevention

Planner must never:

- Assume unavailable tools
- Assume permissions
- Invent APIs
- Skip clarification
- Guess missing information

Instead

Ask

↓

Validate

↓

Plan

---

# Planner Evaluation Metrics

Planning Accuracy

Task Completeness

Dependency Accuracy

Risk Detection Accuracy

Permission Accuracy

Clarification Quality

Execution Success Rate

---

# Future Planner Features

- Learning User Preferences
- Workflow Templates
- Multi-language Planning
- Voice Planning
- Personalized Planning
- Cost-aware Planning
- Multi-worker Planning
- Distributed Planning

---

# Design Principles

The Planner should always remain:

- Deterministic
- Explainable
- Modular
- Replaceable
- Observable
- Testable

---

# Implementation Readiness Checklist

- [ ] Pipeline approved
- [ ] Confidence system approved
- [ ] Clarification strategy approved
- [ ] Risk analysis approved
- [ ] Permission prediction approved
- [ ] Dependency planning approved
- [ ] Parallel planning approved
- [ ] Workflow specification approved

**Status:** 🟡 Pending Team Approval

---

# Next Document

**06_WORKFLOW_COMPILER.md**
