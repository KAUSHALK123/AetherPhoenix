# 02_ARCHITECTURE_LAYERS.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Owner:** Architecture Team

---

# Related Documents

- README.md
- 01_SYSTEM_OVERVIEW.md
- 03_RUNTIME_COMPONENTS.md
- 04_ORCHESTRATOR.md
- 07_SHARED_WORKFLOW_STATE.md

---

# Purpose

This document defines the layered architecture of the AI Desktop Assistant platform.

The objective of the layered architecture is to ensure every subsystem has a single responsibility while maintaining loose coupling, modularity, scalability, and maintainability.

Each layer communicates only with its immediate neighboring layers.

No layer should bypass another.

---

# Why Layered Architecture?

The platform is expected to grow from a simple desktop assistant into a complete AI Operating Platform.

Using layers provides:

- Separation of Concerns
- Easier Testing
- Independent Development
- Better Scalability
- Lower Coupling
- Easier Debugging
- Future Plugin Support
- Replaceable Components

---

# Complete Architecture

```

+-----------------------------------------------------------+
| PRESENTATION LAYER |
| React UI • Mobile UI • Dashboard • Notifications |
+-----------------------------------------------------------+
|
v
+-----------------------------------------------------------+
| SESSION LAYER |
| Authentication • Conversations • User Context |
+-----------------------------------------------------------+
|
v
+-----------------------------------------------------------+
| RUNTIME KERNEL |
| Runtime State • Event Bus • Scheduler • Memory |
+-----------------------------------------------------------+
|
v
+-----------------------------------------------------------+
| ORCHESTRATION LAYER |
| Workflow Manager • Lifecycle • Dispatching |
+-----------------------------------------------------------+
|
v
+-----------------------------------------------------------+
| PLANNING LAYER |
| Planner • Capability Discovery • Risk Analysis |
+-----------------------------------------------------------+
|
v
+-----------------------------------------------------------+
| WORKFLOW COMPILER |
| Validation • DAG Builder • Task Generator |
+-----------------------------------------------------------+
|
v
+-----------------------------------------------------------+
| EXECUTION LAYER |
| Execution Engine • Worker • Supervisor • Healing |
+-----------------------------------------------------------+
|
v
+-----------------------------------------------------------+
| TOOL LAYER |
| Browser • Desktop • Git • OCR • Vision • Python |
+-----------------------------------------------------------+
|
v
+-----------------------------------------------------------+
| OPERATING SYSTEM |
| Windows • Browser • Files • Registry • Network |
+-----------------------------------------------------------+
|
v
+-----------------------------------------------------------+
| PERSISTENCE LAYER |
| SQLite • Logs • Artifacts • Conversations |
+-----------------------------------------------------------+

```

---

# Layer 1 — Presentation Layer

## Purpose

Provides the user interface.

This layer never performs business logic.

---

## Responsibilities

- Display chats
- Display progress
- Display execution timeline
- Display planner summary
- Display logs
- Display workflow graph
- File uploads
- Permission dialogs
- Notifications
- Settings

---

## Technologies

- React
- TypeScript
- Tailwind CSS
- React Query
- Zustand
- Framer Motion

---

## Never Responsible For

- Planning
- Execution
- Database
- AI Reasoning

---

# Layer 2 — Session Layer

## Purpose

Manages user sessions and conversations.

---

## Responsibilities

- Authentication
- Chat History
- User Preferences
- Active Session
- Workflow Ownership

---

## Components

- Session Manager
- Conversation Manager

---

# Layer 3 — Runtime Kernel

## Purpose

Acts as the operating system of the AI platform.

The Runtime Kernel coordinates every running workflow.

---

## Responsibilities

- Runtime Lifecycle
- Active Workflows
- Event Publishing
- Shared Memory
- Workflow Cache
- Scheduler
- Resource Tracking

---

## Components

- Runtime Manager
- Memory Manager
- Event Manager
- Scheduler

---

## Why Runtime Kernel Exists

Without this layer:

- Agents become tightly coupled.
- State becomes inconsistent.
- Scaling becomes difficult.

---

# Layer 4 — Orchestration Layer

## Purpose

Coordinates the complete workflow lifecycle.

---

## Responsibilities

- Start Workflow
- Stop Workflow
- Pause Workflow
- Resume Workflow
- Dispatch Tasks
- Route Events
- Manage Workflow Status

---

## Components

- Orchestrator
- Workflow Manager
- Queue Manager

---

# Layer 5 — Planning Layer

## Purpose

Convert human intent into structured workflow plans.

---

## Components

- Planner Agent
- Intent Analyzer
- Clarification Engine
- Capability Manager
- Permission Detector
- Risk Analyzer
- Dependency Planner

---

## Responsibilities

- Think
- Clarify
- Plan

Never execute.

---

# Layer 6 — Workflow Compiler

## Purpose

Transform high-level plans into executable runtime tasks.

---

## Responsibilities

- Validate Workflow
- Build DAG
- Generate IDs
- Validate Dependencies
- Generate Execution Metadata

---

## Output

Compiled Workflow

↓

Executable Tasks

↓

Execution Queue

---

# Layer 7 — Execution Layer

## Purpose

Execute compiled tasks.

---

## Components

Worker

Supervisor

Healing

Execution Engine

---

## Responsibilities

Worker

Execute

Supervisor

Validate

Healing

Recover

Execution Engine

Coordinate execution

---

# Layer 8 — Tool Layer

## Purpose

Provide reusable execution capabilities.

---

## Tool Categories

Browser

Desktop

Git

Python

OCR

Vision

Research

PowerShell

PPT

PDF

Networking

Windows

Compression

File System

---

## Tool Adapter Pattern

```

Execution Engine

↓

Browser Adapter

↓

Playwright

```

Later

```

Execution Engine

↓

Browser Adapter

↓

Selenium

```

Execution Engine never changes.

---

# Layer 9 — Operating System Layer

## Purpose

Interface with external software.

---

## Resources

Windows

File System

Registry

Terminal

PowerShell

Browser

Network

Clipboard

Desktop Applications

---

# Layer 10 — Persistence Layer

## Purpose

Store permanent information.

---

## Stores

Users

Chats

Workflows

Logs

Artifacts

Permissions

Recovery History

Tool Registry

Plugin Registry

---

# Layer Communication Rules

Allowed

```

Presentation

↓

Session

↓

Runtime

↓

Orchestrator

↓

Planning

↓

Compiler

↓

Execution

↓

Tools

↓

Operating System

```

Forbidden

```

Presentation

↓

Worker

```

```

Planner

↓

Operating System

```

```

Worker

↓

Database

```

Everything flows through the Runtime Kernel and Orchestrator.

---

# Dependency Rules

Every layer may depend only on:

- Itself
- The layer immediately below
- Shared interfaces

Never on higher layers.

---

# Error Flow

```

Worker Failure

↓

Supervisor

↓

Healing

↓

Execution Engine

↓

Worker Retry

```

Planner is never recalled.

---

# Permission Flow

```

Planner

↓

Permission Detector

↓

Permission Manager

↓

User Approval

↓

Execution

```

---

# Event Flow

```

Planner Finished

↓

Event Bus

↓

Runtime Kernel

↓

Frontend

```

---

# Data Flow

```

User Goal

↓

Planner

↓

Workflow Compiler

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

Artifacts

↓

Database

↓

Conversation

```

---

# Benefits

This architecture provides:

- Modular Development
- AI Independence
- Tool Independence
- Plugin Support
- Runtime Stability
- Easier Debugging
- Better Testing
- Future Scalability

---

# Trade-offs

Advantages

- Highly Modular
- Easy to Extend
- Easy to Replace Components
- Clear Responsibilities

Disadvantages

- More Components
- Slightly Higher Complexity
- More Initial Development Time

The long-term maintainability outweighs the additional complexity.

---

# Layer Responsibilities Summary

| Layer | Responsibility |
|---------|---------------|
| Presentation | User Interface |
| Session | User Context |
| Runtime | Runtime Management |
| Orchestration | Workflow Lifecycle |
| Planning | AI Planning |
| Compiler | Workflow Compilation |
| Execution | Execute Tasks |
| Tools | Capabilities |
| Operating System | System Interaction |
| Persistence | Long-Term Storage |

---

# Implementation Readiness Checklist

- [ ] Layer boundaries approved
- [ ] Runtime Kernel approved
- [ ] Communication rules approved
- [ ] Dependency rules approved
- [ ] Tool Adapter pattern approved
- [ ] Error flow approved
- [ ] Permission flow approved
- [ ] Event flow approved

**Status:** 🟡 Pending Team Approval

---

# Next Document

**03_RUNTIME_COMPONENTS.md**
