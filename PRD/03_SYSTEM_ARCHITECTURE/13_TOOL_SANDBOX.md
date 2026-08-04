# 13_TOOL_SANDBOX.md

Version: 1.0

---

# Purpose

The Tool Sandbox is a secure execution environment between the Worker and the operating system.

Every tool execution must pass through the Tool Sandbox.

No tool may access the operating system directly.

---

# Runtime Flow

Worker

↓

Execution Engine

↓

Tool Sandbox

↓

Tool Adapter

↓

Operating System

---

# Responsibilities

- Parameter validation
- Timeout management
- Process isolation
- File restrictions
- Permission enforcement
- Resource limits
- Output capture
- Rollback checkpoints
- Telemetry

---

# Sandbox Pipeline

Task

↓

Validate

↓

Permission Check

↓

Create Sandbox

↓

Execute Tool

↓

Capture Output

↓

Cleanup

↓

Destroy Sandbox

---

# File Restrictions

Allow

Project Folder

Downloads

Temp Folder

User Approved Folder

Block

Windows Folder

Program Files

System32

Registry

Unless explicitly approved.

---

# Network Restrictions

Allow

Approved Domains

Block

Unknown Domains

Future

Enterprise Policies

---

# PowerShell Restrictions

Blocked by default.

Allow only after

Permission

↓

User Approval

↓

Execution

---

# Browser Restrictions

Allowed

- Navigation
- Search
- Download

Blocked

- Background execution
- Credential extraction
- Unsafe scripts

---

# Timeout Rules

Every task receives

Maximum Runtime

Example

Browser

120 sec

Git

60 sec

Research

300 sec

After timeout

↓

Terminate

↓

Supervisor

↓

Healing

---

# Resource Limits

Future

CPU

RAM

Disk

GPU

Network

---

# Rollback

Before execution

↓

Snapshot

↓

Execute

↓

Failure

↓

Rollback

---

# Output Capture

Capture

stdout

stderr

Logs

Screenshots

Artifacts

Metrics

---

# Telemetry

Collect

CPU

RAM

Execution Time

Tool

Errors

Warnings

---

# Future

- Docker Sandbox
- VM Sandbox
- Windows Sandbox
- Remote Sandbox