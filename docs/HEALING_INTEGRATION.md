# Healing Agent End-to-End Integration Architecture

## Overview

The Healing Agent subsystem integrates with the AetherPhoenix execution pipeline to provide autonomous fault tolerance, root cause diagnosis, recovery planning, safe worker re-execution, escalation handling, and planner feedback.

```
+-----------------------------------------------------------------------------------+
|                            Normal Execution Flow                                  |
|                                                                                   |
|  USER -> PLANNER -> WORKFLOW ENGINE -> WORKER -> TOOL -> SUPERVISOR -> SUCCESS    |
+-----------------------------------------------------------------------------------+
                                                                 |
                                                          (on failure)
                                                                 v
+-----------------------------------------------------------------------------------+
|                         Integrated Self-Healing Lifecycle                         |
|                                                                                   |
|     +-------------------------+                                                   |
|     |     SUPERVISOR          | (Centralized failure detection & validation)      |
|     +-------------------------+                                                   |
|                  |                                                                |
|                  v                                                                |
|     +-------------------------+                                                   |
|     |      ERROR PARSER       | (Normalizes raw errors/exceptions/exit codes)     |
|     +-------------------------+                                                   |
|                  |                                                                |
|                  v                                                                |
|     +-------------------------+                                                   |
|     |   ROOT CAUSE ANALYZER   | (Multi-heuristic pattern matching & ranking)      |
|     +-------------------------+                                                   |
|                  |                                                                |
|                  v                                                                |
|     +-------------------------+                                                   |
|     |    RECOVERY PLANNER     | (Constructs validated & risk-assessed plan)       |
|     +-------------------------+                                                   |
|                  |                                                                |
|                  +--------------------+                                           |
|                  |                    |                                           |
|        (viable recovery)      (non-recoverable / exhausted)                       |
|                  |                    |                                           |
|                  v                    v                                           |
|     +-----------------------+ +---------------------+                             |
|     |     RETRY ENGINE      | | ESCALATION HANDLER  |                             |
|     | (Loop check, backoff, | | (Severity triage,   |                             |
|     |  enqueue re-execution)| |  human notification)|                             |
|     +-----------------------+ +---------------------+                             |
|                  |                    |                                           |
|                  v                    v                                           |
|     +-----------------------+ +---------------------+                             |
|     | WORKER RE-EXECUTION   | |   PLANNER FEEDBACK  |                             |
|     | (Re-run / replacement)| |  (Replanning signal)|                             |
|     +-----------------------+ +---------------------+                             |
+-----------------------------------------------------------------------------------+
```

---

## Key Components

### 1. Error Parser (`app.agents.healing.error_parser.py`)
- Normalizes diverse runtime failures into unified `NormalizedError` structures.
- Parses exit codes, stack traces, HTTP errors, and permission failures.
- Categorizes errors and determines immediate retryability.

### 2. Root Cause Analyzer (`app.agents.healing.root_cause_analyzer.py`)
- Executes multi-step heuristic inspection across task context, execution logs, dependencies, and environment.
- Ranks candidate causes using confidence scoring.
- Outputs structured `RootCauseAnalysis` / `RootCauseResult` with diagnostic evidence.

### 3. Recovery Planner (`app.agents.healing.recovery_planner.py`)
- Synthesizes ordered sequences of `RecoveryAction` objects based on root cause diagnosis.
- Evaluates risk levels (`SAFE`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- Validates pre-conditions, success criteria, and capability requirements.
- Supports alternative tool generation for unavailable tools.

### 4. Retry Engine (`app.agents.healing.retry_engine.py`)
- Implements exponential backoff with jitter.
- Enforces maximum retry thresholds per task and workflow.
- Detects infinite healing loops using failure signatures.
- Updates task lifecycle states and enqueues tasks / replacement tasks for re-execution.

### 5. Escalation Handler (`app.agents.healing.escalation.py`)
- Formulates structured escalation requests for unrecoverable errors or exhausted retries.
- Triages severity levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- Emits runtime events for human-in-the-loop intervention.

### 6. Planner Feedback Loop (`app.agents.planner.feedback.py`)
- Packages execution summaries, healing attempts, and capability failures into structured `PlannerFeedback`.
- Sanitizes sensitive credentials and secrets.
- Informs the Planner Agent for dynamic re-planning when needed.

---

## Verification & Testing

End-to-end integration is validated in:
- [`backend/tests/integration/test_healing_integration.py`](file:///d:/PROJECTS/Major/backend/tests/integration/test_healing_integration.py)
- [`backend/tests/agents/healing/test_self_healing_loop.py`](file:///d:/PROJECTS/Major/backend/tests/agents/healing/test_self_healing_loop.py)
- [`backend/tests/agents/supervisor/test_supervisor.py`](file:///d:/PROJECTS/Major/backend/tests/agents/supervisor/test_supervisor.py)
- [`backend/tests/agents/healing/test_recovery_planner.py`](file:///d:/PROJECTS/Major/backend/tests/agents/healing/test_recovery_planner.py)
- [`backend/tests/agents/healing/test_retry_engine.py`](file:///d:/PROJECTS/Major/backend/tests/agents/healing/test_retry_engine.py)
