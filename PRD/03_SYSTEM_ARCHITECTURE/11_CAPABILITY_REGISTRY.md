# 11_CAPABILITY_REGISTRY.md

Version: 1.0

---

# Purpose

The Capability Registry defines **WHAT** the AI platform is capable of doing.

It is the first component queried by the Planner before creating a workflow.

Capabilities represent high-level skills rather than specific software implementations.

The Planner must never know which library or tool implements a capability.

---

# Philosophy

Think in terms of

"What can I do?"

NOT

"How do I do it?"

---

# Runtime Flow

User Goal

↓

Planner

↓

Capability Registry

↓

Available Capabilities

↓

Workflow Planning

---

# Responsibilities

- Register capabilities
- Enable/Disable capabilities
- Capability metadata
- Capability health
- Required permissions
- Supported execution modes
- Required tools
- Version tracking

---

# Capability Categories

## Browser

- Search Internet
- Navigate Website
- Fill Forms
- Upload Files
- Download Files
- Extract Data
- Login Automation

---

## Desktop

- Open Applications
- Click
- Keyboard Input
- Window Detection
- Screen Capture
- Clipboard

---

## Research

- Web Search
- Summarization
- Citation Collection
- PDF Reading

---

## Coding

- Generate Code
- Debug
- Git
- Refactoring
- Documentation

---

## Office

- PPT Generation
- PDF Generation
- DOCX
- Excel

---

## Windows

- Drivers
- Network
- Registry
- Services
- Device Manager
- PowerShell

---

## AI

- OCR
- Vision
- Speech
- Translation
- Embeddings

---

# Capability Metadata

Each capability stores

- Capability ID
- Name
- Description
- Version
- Enabled
- Risk Level
- Required Permissions
- Required Tools
- Supported Platforms

---

# Capability Lifecycle

Registered

↓

Available

↓

Planner Uses

↓

Worker Executes

↓

Deprecated

↓

Removed

---

# Planner Contract

Planner MUST

- Query registry first
- Ignore unavailable capabilities
- Inform user if capability missing

---

# Future

- Plugin capabilities
- Marketplace
- Dynamic loading
- Community capabilities