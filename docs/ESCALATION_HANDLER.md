# Escalation Handler Documentation

**Version:** 1.0  
**Module:** `app.agents.healing.escalation`  
**Owner:** AI Runtime & Healing Team  

---

## Overview

The **Escalation Handler** processes task execution failures that cannot be safely or automatically recovered by the Healing Agent. It provides a strict, controlled boundary between autonomous recovery and human/user intervention.

Instead of retrying failures indefinitely or silently bypassing security constraints, the Escalation Handler ensures that unrecoverable, high-risk, or permission-blocked tasks are clearly classified, logged, emitted via system events, and reflected in the Shared Workflow State (SWS).

---

## Architecture & Integration

```
  +------------------+
  |  Worker Failure  |
  +--------+---------+
           |
           v
  +------------------+
  | Supervisor Agent |
  +--------+---------+
           |
           v
  +------------------+
  |  Healing Agent   |
  +--------+---------+
           |
     Is Recoverable?
      /         \
    YES          NO
    /             \
   v               v
Execute      +--------------------+
Recovery     | Escalation Handler |
             +---------+----------+
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
   Emit Events   Update SWS      Log Details
 (Bus Pub/Sub)  (Status/Queue)  (ERROR/WARN)
```

---

## Escalation Triggers

An escalation request is dispatched under any of the following conditions:

1. **Permission Denial (`PERMISSION_DENIED`)**:
   - Explicit user rejection or required tool permission not granted.
2. **Maximum Task Retries Exceeded (`MAX_RETRIES_EXCEEDED`)**:
   - Task execution failed consecutively up to maximum allowed retries.
3. **Maximum Healing Attempts Reached (`MAX_HEALING_ATTEMPTS_EXCEEDED`)**:
   - Healing Agent recovery strategies executed without resolving the task failure.
4. **High-Risk Operation (`HIGH_RISK_OPERATION`)**:
   - Operation risk assessment level evaluates to `HIGH` or `CRITICAL`.
5. **Unknown Critical Failure (`UNKNOWN_CRITICAL_FAILURE`)**:
   - System error or unhandled runtime exception encountered.
6. **Hardware/Device Failure (`HARDWARE_FAILURE`)**:
   - Required physical hardware device unavailable.
7. **User Intervention Required (`USER_INTERVENTION_REQUIRED`)**:
   - Task explicitly requires human input (e.g. manual approval, visual captcha).

---

## Data Contracts

### EscalationReason
Enum representing the classified reason for escalation:
- `PERMISSION_DENIED`
- `MAX_RETRIES_EXCEEDED`
- `MAX_HEALING_ATTEMPTS_EXCEEDED`
- `HIGH_RISK_OPERATION`
- `UNKNOWN_CRITICAL_FAILURE`
- `UNSUPPORTED_ERROR`
- `USER_INTERVENTION_REQUIRED`
- `HARDWARE_FAILURE`
- `DUPLICATE_ESCALATION`

### EscalationSeverity
Enum representing failure severity:
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

### EscalationRequest
Input payload passed to `EscalationHandler.handle_escalation()`:
- `request_id: UUID`
- `workflow_id: UUID`
- `task_id: UUID`
- `reason: EscalationReason`
- `details: str`
- `failure_context: Dict[str, Any]` (preserves error message, error code, stack trace, tool details)
- `healing_history: List[HealingResult]` (preserves previous recovery attempts)
- `attempt_number: int`
- `risk_level: Optional[RiskLevel]`

### EscalationResult
Structured output produced by Escalation Handler:
- `escalation_id: UUID`
- `workflow_id: UUID`
- `task_id: UUID`
- `reason: EscalationReason`
- `severity: EscalationSeverity`
- `requires_user_intervention: bool`
- `user_action_required: Optional[str]`
- `failure_context: Dict[str, Any]`
- `healing_history: List[HealingResult]`
- `timestamp: datetime`

---

## Workflow State Transitions

Upon processing an escalation:

1. **Task Status**: Updated to `TaskStatus.BLOCKED` (if user intervention is required) or `TaskStatus.ESCALATED`.
2. **Workflow Status**: Updated to `WorkflowStatus.BLOCKED` or `WorkflowStatus.ESCALATED`.
3. **Queue Handoff**: The failed task is removed from `execution_queue` and `running_tasks`, and appended to `failed_tasks`.
4. **History Preservation**: Complete `failure_context` and `healing_history` are preserved in `SharedWorkflowState.escalations`.
5. **No Automatic Retries**: All automatic scheduling and retries for the escalated task are terminated immediately.

---

## Event Pub/Sub Integration

The Escalation Handler emits the following runtime events on the `EventBus`:

- `EventType.ESCALATION_REQUESTED` (`"EscalationRequested"`)
- `EventType.HEALING_ESCALATED` (`"HealingEscalated"`)

Source component is set to `EventSource.HEALING`.

---

## Security Boundaries & Safety Guarantees

The Escalation Handler guarantees:
- Never bypasses security or permission controls.
- Never conceals critical failures or marks failed tasks as completed.
- Never performs unauthorized high-risk operations.
- Guarantees idempotent duplicate request handling (cached responses without double event emissions).
