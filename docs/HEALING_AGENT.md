# Healing Agent & Self-Healing Loop

**Version:** 1.0.0  
**Status:** Active  
**Component:** Backend Agent System (`backend/app/agents/healing`)

---

## Overview

The **Self-Healing Loop** coordinates the complete autonomous failure recovery lifecycle in AetherPhoenix after the Supervisor Agent detects a task execution failure or output validation failure.

It connects modular healing subcomponents into a structured, safe execution recovery pipeline:

```
Worker
  ↓
Supervisor
  ↓
Failure Detection
  ↓
Error Parser
  ↓
Root Cause Analyzer
  ↓
Recovery Planner
  ↓
Retry Engine
  ↓
Worker
  ↓
Supervisor
```

---

## Component Architecture

The `SelfHealingLoop` agent orchestrates four primary modules:

1. **Error Parser (`error_parser.py`)**
   - Normalizes raw exceptions, `ExecutionResult`, `TaskError`, and `TaskFailureReport` instances.
   - Categorizes failures into `ErrorCategory` (`BROWSER`, `DESKTOP`, `GIT`, `PYTHON`, `POWERSHELL`, `OCR`, `VISION`, `FILESYSTEM`, `NETWORK`, `PERMISSIONS`, `PLUGINS`, `TOOL`, `UNKNOWN`).
   - Identifies transient error flags and standardized error codes.

2. **Root Cause Analyzer (`root_cause_analyzer.py`)**
   - Analyzes normalized errors along with task and workflow context.
   - Classifies failure root causes into `RootCauseCategory` (`INFRASTRUCTURE`, `TOOL`, `PERMISSION`, `NETWORK`, `RUNTIME`, `USER`, `WORKFLOW`, `EXTERNAL_API`, `UNKNOWN`).
   - Evaluates recoverability and generates recommended strategies.

3. **Recovery Planner (`recovery_planner.py`)**
   - Formulates a `RecoveryPlan` with candidate strategies (`RETRY`, `RESTART_TOOL`, `WAIT`, `ALTERNATIVE_TOOL`, `ALTERNATIVE_WEBSITE`, `ALTERNATIVE_API`, `REQUEST_PERMISSION_AGAIN`, `ESCALATE_USER`, `CANCEL_WORKFLOW`).
   - Produces and validates executable replacement tasks when alternative tools are required.

4. **Retry Engine (`retry_engine.py`)**
   - Enforces configurable maximum task retry limits (`max_retries`) and maximum workflow healing attempt limits (`max_healing_attempts`).
   - Prevents infinite healing loops by tracking repeated failure signatures per task and root cause.
   - Re-enqueues tasks or replacement tasks into `SharedWorkflowState` using `WorkflowEngine`.

---

## State Machine

The Self-Healing Loop operates as a state machine (`HealingState`):

- **`IDLE`**: Initial state before failure processing.
- **`ANALYZING`**: Parsing error and detecting root cause.
- **`PLANNING`**: Formulating recovery strategy and replacement tasks.
- **`GENERATING_TASKS`**: Generating validated replacement tasks.
- **`RETRYING`**: Re-enqueueing task into `WorkflowEngine`.
- **`COMPLETED`**: Recovery plan successfully enqueued.
- **`FAILED`**: Unrecoverable failure or recovery execution failure.
- **`EXHAUSTED`**: Retry or healing attempt limits exceeded.

---

## Events & Observability

The Self-Healing Loop emits standard `RuntimeEvent` objects on the system `EventBus`:

- **`HEALING_STARTED`**: Emitted when healing lifecycle begins.
- **`HEALING_COMPLETED`**: Emitted on successful recovery.
- **`HEALING_FAILED`**: Emitted on unrecoverable failure or limit exhaustion.

Every recovery attempt appends a structured `HealingResult` object to `state.healing_history` for full persistence and auditability.

---

## Constraints & Safety Rules

- **No Second Worker**: Healing Agent never executes tools or tasks directly. All execution remains with the Worker Agent.
- **Workflow Engine Gate**: Tasks are re-enqueued strictly via `WorkflowEngine(state).enqueue(...)`.
- **Permission Enforcement**: Healing Agent respects all permission boundaries and escalates if permissions are missing or denied.
- **Infinite Loop Protection**: Signature tracking halts retries if identical failure signatures recur.
