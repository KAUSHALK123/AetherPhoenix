# AetherPhoenix REST API Specification

**Version:** 1.0  
**Base URL:** `http://localhost:8000/api/v1`  
**OpenAPI / Interactive Specs:** `http://localhost:8000/docs`

---

## 1. System Health

### `GET /health`
- **Description**: Verifies backend service status.
- **Response**: `200 OK`
```json
{
  "status": "ok"
}
```

---

## 2. Planner & Execution Endpoints (`/api/v1/planner`)

### `POST /api/v1/planner/submit`
- **Description**: Submits a natural language goal request to the Planner Agent.
- **Request Body**:
```json
{
  "session_id": "string (optional)",
  "message": "Create a PowerPoint presentation on Quantum Computing"
}
```
- **Response**: `200 OK`
```json
{
  "status": "ready | needs_clarification",
  "workflow_id": "uuid-string",
  "reply": "JSON string containing DAG task decomposition plan or assistant message",
  "clarification": {
    "question_id": "uuid-string",
    "question": "How many slides should the presentation contain?",
    "options": ["3-5 slides", "5-10 slides"],
    "is_multi_select": false
  }
}
```

### `POST /api/v1/planner/clarify`
- **Description**: Answers an interactive clarification question.
- **Request Body**:
```json
{
  "workflow_id": "uuid-string",
  "question_id": "uuid-string",
  "answers": ["5-10 slides"]
}
```
- **Response**: `200 OK` (returns updated `PlannerResponse` with ready workflow DAG plan).

---

## 3. Permission Management Endpoints (`/api/v1/permissions`)

### `GET /api/v1/permissions/pending`
- **Description**: Retrieves all pending user permission approval requests.
- **Response**: `200 OK`
```json
[
  {
    "request_id": "uuid-string",
    "workflow_id": "uuid-string",
    "task_id": "uuid-string",
    "permission_type": "DESKTOP_AUTOMATION | BROWSER_ACCESS | FILE_SYSTEM | POWERSHELL",
    "reason": "Requesting permission to launch text editor application",
    "status": "PENDING",
    "requested_at": "2026-08-31T20:20:00Z"
  }
]
```

### `POST /api/v1/permissions/approve`
- **Description**: Approves a pending permission request.
- **Request Body**:
```json
{
  "request_id": "uuid-string"
}
```

### `POST /api/v1/permissions/deny`
- **Description**: Denies a pending permission request with optional rationale.
- **Request Body**:
```json
{
  "request_id": "uuid-string",
  "reason": "User rejected application launch"
}
```

### `GET /api/v1/permissions/mode`
- **Description**: Gets current system execution policy mode (`SAFE`, `STRICT`, `UNRESTRICTED`).

### `POST /api/v1/permissions/mode`
- **Description**: Updates policy execution mode.

---

## 4. Dashboard & Observability Endpoints (`/api/v1/dashboard`)

### `GET /api/v1/dashboard/workflows`
- **Description**: Returns execution history and status of all workflows.

### `GET /api/v1/dashboard/workflows/{workflow_id}`
- **Description**: Retrieves workflow state, task tree, and current execution queue.

### `GET /api/v1/dashboard/logs`
- **Description**: Fetches execution logs with optional filtering by severity or workflow ID.

### `GET /api/v1/dashboard/analytics`
- **Description**: Retrieves performance metrics (total runs, success rate, self-healing recoveries).

---

## 5. Notification Endpoints (`/api/v1/notifications`)

### `GET /api/v1/notifications`
- **Description**: Lists active system notifications and alert banners.

### `POST /api/v1/notifications/{id}/read`
- **Description**: Marks a specific notification as read.

### `GET /api/v1/notifications/stream`
- **Description**: Real-time Server-Sent Events (SSE) stream for live workflow progress updates.

---

## 6. Document & Export Engine Endpoints (`/api/v1/export`)

### `POST /api/v1/export/pdf`
- **Description**: Converts content or workflow report to downloadable PDF artifact.

### `POST /api/v1/export/pptx`
- **Description**: Generates presentation slide deck file (`.pptx`).

### `POST /api/v1/export/json` & `POST /api/v1/export/markdown`
- **Description**: Exports workflow data in structured JSON or Markdown format.

---

## 7. Browser Extension Bridge Endpoints (`/api/v1/browser-extension`)

### `POST /api/v1/browser-extension/sync-tab`
- **Description**: Synchronizes active browser tab URL, title, and metadata.

### `POST /api/v1/browser-extension/dom-capture`
- **Description**: Receives captured DOM tree snapshot from extension helper.
