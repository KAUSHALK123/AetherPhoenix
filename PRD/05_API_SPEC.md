# 05_API_SPEC.md

**Version:** 1.0

**Status:** Draft

**Last Updated:** July 2026

**Document Owner:** Project Team

---

# Related Documents

- 01_PROJECT_FOUNDATION.md
- 02_FEATURES_AND_PRD.md
- 03_SYSTEM_ARCHITECTURE.md
- 04_DATABASE.md
- 06_UI.md
- 09_AI_DEVELOPMENT_PLAN.md

---

# API Overview

## Purpose

The API layer acts as the communication bridge between the frontend, AI orchestration engine, desktop runtime, and persistent storage.

The API should expose only high-level operations.

Business logic must remain inside the backend services.

---

# API Design Principles

- REST First
- JSON Communication
- Stateless APIs
- JWT Authentication
- Versioned APIs
- Standardized Responses
- Structured Error Handling
- Async Support
- Secure by Default

---

# Base URL

Development

```
http://localhost:8000/api/v1
```

Future

```
https://api.project.com/v1
```

---

# Authentication

Version 1

- Local Authentication

Future

- Google OAuth
- GitHub OAuth
- Microsoft Login

---

# API Modules

```
Authentication

↓

User

↓

Conversation

↓

Workflow

↓

Planner

↓

Worker

↓

Supervisor

↓

Healing

↓

Permissions

↓

Tools

↓

Artifacts

↓

Logs

↓

Plugins

↓

Settings
```

---

# Standard API Response

Success

```json
{
  "success": true,
  "message": "Workflow created successfully.",
  "data": {},
  "timestamp": "",
  "request_id": ""
}
```

---

Failure

```json
{
  "success": false,
  "error": {
    "code": "",
    "message": "",
    "details": ""
  },
  "timestamp": "",
  "request_id": ""
}
```

---

# Authentication APIs

## Login

POST

```
/auth/login
```

Request

```json
{
  "username": "",
  "password": ""
}
```

Response

```json
{
  "access_token": "",
  "refresh_token": ""
}
```

---

## Logout

POST

```
/auth/logout
```

---

## Refresh Token

POST

```
/auth/refresh
```

---

# User APIs

## Get Current User

GET

```
/users/me
```

---

## Update Profile

PUT

```
/users/me
```

---

# Conversation APIs

## Create Conversation

POST

```
/conversations
```

---

## Get Conversations

GET

```
/conversations
```

---

## Get Conversation

GET

```
/conversations/{id}
```

---

## Delete Conversation

DELETE

```
/conversations/{id}
```

---

## Send Message

POST

```
/conversations/{id}/messages
```

Request

```json
{
    "message":"Create a presentation on AI."
}
```

---

# Workflow APIs

## Create Workflow

POST

```
/workflows
```

Purpose

Creates a workflow after Planner finishes.

---

## Get Workflow

GET

```
/workflows/{workflow_id}
```

---

## Workflow Status

GET

```
/workflows/{workflow_id}/status
```

Returns

- Current Task
- Progress
- Running Agent
- Estimated Time

---

## Pause Workflow

POST

```
/workflows/{workflow_id}/pause
```

---

## Resume Workflow

POST

```
/workflows/{workflow_id}/resume
```

---

## Cancel Workflow

POST

```
/workflows/{workflow_id}/cancel
```

---

## Retry Workflow

POST

```
/workflows/{workflow_id}/retry
```

---

# Planner APIs

## Generate Plan

POST

```
/planner/generate
```

Input

```json
{
    "goal":"Create PPT on AI"
}
```

Output

- Clarification Questions
- Workflow Graph
- Estimated Time
- Required Permissions
- Execution Summary

---

## Approve Plan

POST

```
/planner/approve
```

Purpose

Moves approved workflow to execution.

---

# Worker APIs

## Execute Task

POST

```
/worker/execute
```

Internal API

Not directly exposed to frontend.

---

## Task Result

POST

```
/worker/result
```

Worker updates execution results.

---

# Supervisor APIs

## Validate Task

POST

```
/supervisor/validate
```

Internal API

---

## Workflow Health

GET

```
/supervisor/health
```

Returns

- Running Tasks
- Failed Tasks
- Recovery Count

---

# Healing APIs

## Recover Task

POST

```
/healing/recover
```

Internal API

---

## Recovery History

GET

```
/healing/history/{workflow_id}
```

---

# Permission APIs

## Request Permission

POST

```
/permissions/request
```

Example

PowerShell

Browser

Registry

Internet

---

## Approve Permission

POST

```
/permissions/approve
```

---

## Reject Permission

POST

```
/permissions/reject
```

---

# Tool APIs

## List Installed Tools

GET

```
/tools
```

---

## Tool Details

GET

```
/tools/{tool_id}
```

---

## Tool Health

GET

```
/tools/{tool_id}/health
```

---

# Plugin APIs

## Installed Plugins

GET

```
/plugins
```

---

## Enable Plugin

POST

```
/plugins/{id}/enable
```

---

## Disable Plugin

POST

```
/plugins/{id}/disable
```

---

# Artifact APIs

## List Artifacts

GET

```
/artifacts/{workflow_id}
```

---

## Download Artifact

GET

```
/artifacts/download/{artifact_id}
```

---

## Delete Artifact

DELETE

```
/artifacts/{artifact_id}
```

---

# Log APIs

## Workflow Logs

GET

```
/logs/{workflow_id}
```

---

## Task Logs

GET

```
/logs/task/{task_id}
```

---

# Settings APIs

## Get Settings

GET

```
/settings
```

---

## Update Settings

PUT

```
/settings
```

---

# WebSocket APIs

Purpose

Real-time frontend updates.

Connection

```
ws://localhost:8000/ws
```

---

Supported Events

```
Workflow Started

Workflow Updated

Task Started

Task Completed

Task Failed

Permission Requested

Permission Granted

Permission Rejected

Healing Started

Healing Completed

Workflow Completed

Workflow Cancelled

Tool Installed

Plugin Enabled
```

---

# HTTP Status Codes

```
200 OK

201 Created

204 No Content

400 Bad Request

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

422 Validation Error

429 Too Many Requests

500 Internal Server Error
```

---

# Validation Rules

Every request should validate:

- JWT Token
- User Session
- Input Schema
- Required Fields
- Permissions
- Tool Availability
- Workflow State

---

# Pagination

Supported On

- Conversations
- Messages
- Logs
- Artifacts

Parameters

```
?page=1

&limit=20
```

---

# Filtering

Examples

```
status=completed

status=running

status=failed

tool=browser

agent=worker
```

---

# Sorting

Supported Fields

- Created Date
- Updated Date
- Workflow Status
- Execution Time

---

# Rate Limiting

Authentication

```
10 requests/minute
```

General APIs

```
100 requests/minute
```

Internal APIs

Unlimited

---

# API Versioning

Current

```
v1
```

Future

```
v2

v3
```

Backward compatibility should be maintained whenever possible.

---

# Error Codes

Examples

```
AUTH_001

WORKFLOW_001

WORKER_001

PLANNER_001

SUPERVISOR_001

HEALING_001

PERMISSION_001

TOOL_001
```

---

# Security

Every API must support

- JWT Authentication
- HTTPS (Future)
- Input Validation
- SQL Injection Protection
- Rate Limiting
- CSRF Protection
- XSS Prevention

---

# Future APIs

- Voice Commands
- Mobile Remote Control
- Plugin Marketplace
- Cloud Synchronization
- Team Collaboration
- AI Workflow Templates
- Workflow Scheduling
- Multi-Worker APIs

---

# Implementation Readiness Checklist

- [ ] REST endpoints finalized
- [ ] Authentication flow approved
- [ ] Response schema approved
- [ ] WebSocket events finalized
- [ ] Validation rules approved
- [ ] Error codes finalized
- [ ] Rate limiting approved
- [ ] Security review completed

**Status:** 🟡 Pending Team Approval

---

# Next Document

**06_UI.md**