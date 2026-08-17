# 15_MEMORY_ARCHITECTURE.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Owner:** AI Architecture Team

---

# Related Documents

- 05_PLANNER_AGENT.md
- 07_SHARED_WORKFLOW_STATE.md
- 10_HEALING_AGENT.md
- 11_CAPABILITY_REGISTRY.md
- 13_EVENT_BUS.md

---

# Purpose

The Memory Architecture defines how information is stored, retrieved, updated, reused, and forgotten throughout the lifecycle of the AI Desktop Assistant.

Unlike a traditional chatbot that stores only conversation history, this platform maintains multiple specialized memory systems.

Each memory has its own responsibility, lifecycle, storage mechanism, and retrieval strategy.

The objective is to improve planning quality, execution efficiency, recovery accuracy, and overall user experience without modifying or retraining the underlying language model.

---

# Memory Philosophy

The system follows one principle:

> Learn from execution, not just conversation.

Memory should improve future workflows while remaining transparent, controllable, and privacy-friendly.

---

# Memory Hierarchy

```
Memory Architecture

│

├── Session Memory

├── Conversation Memory

├── Runtime Memory

├── Workflow Memory

├── Planner Memory

├── Knowledge Memory

├── Artifact Memory

├── Healing Memory

├── User Preference Memory

├── Cache Memory

└── Future Long-Term Memory
```

Each memory type has one responsibility.

---

# Memory Flow

```
User Request

↓

Memory Router

↓

Relevant Memory Sources

↓

Planner

↓

Workflow

↓

Execution

↓

Memory Update

↓

Persist

↓

Future Reuse
```

---

# Memory Manager

## Purpose

The Memory Manager acts as the central controller responsible for all memory operations.

---

## Responsibilities

- Memory Routing
- Memory Retrieval
- Memory Storage
- Memory Cleanup
- Memory Expiration
- Similarity Search
- Context Building
- Cache Management

---

# 1. Session Memory

## Purpose

Stores temporary information for the current application session.

---

## Lifetime

Application Start

↓

Application Exit

---

## Stores

- Current Workflow
- Current Planner Context
- Active Tasks
- Temporary Variables
- Running Tool Information

---

## Cleared

Automatically when the application closes.

---

# 2. Conversation Memory

## Status

Implemented ✅ (`app.memory.conversation_memory`, `shared.contracts.memory`)

---

## Purpose

Stores structured chat conversations and long-term context entries for future planner retrieval.

---

## Stores

- User Messages
- AI Responses
- User Preferences
- Task Decisions & Instructions
- Project Context & Clarifications

---

## Used By

Planner Agent

UI

Conversation Manager

---

# 3. Runtime Memory

## Purpose

Stores live execution information.

---

## Stores

- Active Workflow
- Running Tasks
- Worker Status
- Supervisor Status
- Healing Status
- Runtime Metrics

---

## Owner

Runtime Kernel

---

## Lifetime

Workflow Start

↓

Workflow End

---

# 4. Workflow Memory

## Purpose

Stores completed workflow metadata.

---

## Stores

- Workflow Goal
- Planner Output
- Execution Time
- Success Rate
- Recovery Count
- Final Artifacts

---

## Example

```
Workflow

↓

Create PPT

↓

Completed

↓

Stored
```

Planner may reuse successful workflows.

---

# 5. Planner Memory

## Purpose

Stores successful planning strategies.

This is **not** conversation history.

It stores reusable planning knowledge.

---

## Examples

User prefers

- 10 slides
- Minimal design
- Blue theme
- Bullet points

Future Planner

↓

Reuse

↓

Less clarification

---

## Stores

- Preferred workflow structure
- Preferred output formats
- Successful planning templates
- Common dependency graphs

---

# 6. Knowledge Memory

## Purpose

Stores searchable knowledge.

---

## Sources

- Uploaded Documents
- PDFs
- Notes
- Repositories
- Manuals
- Web Research

---

## Future

RAG

↓

Embeddings

↓

Vector Search

---

## Recommended

ChromaDB

FAISS

SQLite Metadata

---

# 7. Artifact Memory

## Purpose

Tracks generated outputs.

---

## Stores

- PPT
- PDF
- Images
- Reports
- ZIP
- Code
- Screenshots

---

## Metadata

- Name
- Type
- Size
- Path
- Created Time
- Workflow

---

# 8. Healing Memory

## Purpose

Stores previous failures and successful recovery strategies.

---

## Example

```
Playwright Timeout

↓

Restart Browser

↓

Success

↓

Store
```

Next time

↓

Reuse

↓

Faster Recovery

---

## Stores

- Error Type
- Root Cause
- Recovery Plan
- Retry Count
- Outcome

---

# 9. User Preference Memory

## Purpose

Stores user preferences.

---

## Examples

Preferred

- Theme
- Output Folder
- Safe Mode
- Preferred LLM
- Preferred PPT Style
- Preferred Coding Style

---

## Never Stores

- Passwords
- Secrets
- API Keys

---

# 10. Cache Memory

## Purpose

Temporary high-speed storage.

---

## Stores

- Recent Research
- Recent Searches
- Planner Results
- Tool Health
- Capability Lookup

---

## Lifetime

Short-term

Automatically expires.

---

# Memory Routing

```
Planner Request

↓

Memory Router

↓

Planner Memory

↓

Knowledge Memory

↓

Conversation Memory

↓

Return Context
```

Only relevant memory is returned.

---

# Context Builder

Purpose

Construct the final context sent to the LLM.

---

## Sources

Conversation

+

Planner Memory

+

Knowledge Memory

+

User Preferences

↓

Merged Context

↓

Planner

---

# Similarity Search

Future

```
Current Goal

↓

Embedding

↓

Vector Search

↓

Similar Workflows

↓

Planner
```

---

# Memory Lifecycle

```
Created

↓

Updated

↓

Retrieved

↓

Archived

↓

Deleted
```

---

# Memory Ownership

| Memory | Owner |
|---------|-------|
| Session | Session Manager |
| Conversation | Conversation Manager |
| Runtime | Runtime Kernel |
| Workflow | Workflow Manager |
| Planner | Planner |
| Knowledge | Knowledge Manager |
| Artifact | Artifact Manager |
| Healing | Healing Agent |
| Preferences | User Manager |
| Cache | Memory Manager |

---

# Storage Strategy

| Memory | Storage |
|----------|---------|
| Session | RAM |
| Runtime | RAM |
| Cache | RAM |
| Conversation | SQLite |
| Workflow | SQLite |
| Preferences | SQLite |
| Artifacts | File System |
| Knowledge | ChromaDB / FAISS |
| Healing | SQLite |

---

# Memory Expiration

Session

↓

Application Close

Runtime

↓

Workflow End

Cache

↓

TTL

Conversation

↓

Manual Delete

Knowledge

↓

Manual Management

---

# Privacy

Memory must never store

- Passwords
- Authentication Tokens
- Credit Card Numbers
- Sensitive System Secrets
- Hidden LLM Reasoning

Users should always be able to

- View Memory
- Delete Memory
- Clear Conversation
- Clear Knowledge Base
- Reset Preferences

---

# Future Memory Features

- Memory Compression
- Workflow Embeddings
- Semantic Workflow Search
- Long-Term Learning
- Personalized Planning
- Cross-Device Sync
- Cloud Memory
- Shared Team Memory
- AI Memory Analytics

---

# Performance Goals

Memory Lookup

<50 ms

Cache Lookup

<10 ms

Vector Search

<500 ms

Conversation Retrieval

<100 ms

Workflow Retrieval

<100 ms

---

# Design Principles

Memory should always be

- Modular
- Secure
- Explainable
- Searchable
- Observable
- Privacy-First
- Replaceable
- Extensible

---

# Memory Contract

Every memory operation follows

```
Request

↓

Memory Router

↓

Relevant Memories

↓

Context Builder

↓

Return Context

↓

Planner / Runtime

↓

Update Memory

↓

Persist
```

No component directly accesses another memory store.

---

# Acceptance Criteria

The Memory Architecture is complete when

- Session memory works
- Runtime memory synchronizes correctly
- Planner reuses previous workflows
- Healing reuses successful recovery strategies
- Knowledge memory supports semantic retrieval
- User preferences personalize planning
- Memory remains privacy-safe
- Memory retrieval is fast and deterministic

---

# Implementation Readiness Checklist

- [ ] Memory hierarchy approved
- [ ] Memory routing approved
- [ ] Planner memory approved
- [ ] Healing memory approved
- [ ] Knowledge memory approved
- [ ] Storage strategy approved
- [ ] Privacy model approved
- [ ] Performance targets approved

**Status:** 🟡 Pending Team Approval

---

# Next Steps

The core architecture is now substantially complete.

The remaining documents (Plugin Architecture, Folder Structure, Sequence Diagrams, Design Decisions, Scalability, Future Roadmap) can be treated as supporting documentation and generated later or condensed as needed.

The next practical milestone is to begin defining:

- Production Prompt Library
- GitHub Project Structure
- Sprint & Issue Breakdown
- Module-wise implementation prompts for AI coding agents