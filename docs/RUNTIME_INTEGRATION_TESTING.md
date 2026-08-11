# Runtime Integration Testing Documentation

## Overview

The **Runtime Integration Test Suite** (`backend/tests/integration/test_runtime_integration.py`) validates that all foundational Sprint 1 runtime infrastructure modules operate together as a cohesive, production-ready execution environment.

It ensures interoperability between the Runtime Kernel, Workflow Engine, Capability Registry, Tool Registry, Permission Manager, Event Bus, Logging Framework, Configuration Manager, and Shared Exceptions.

---

## Architecture & Integration Scope

The integration test suite validates the interaction boundaries across the layered runtime architecture:

```
                  ┌─────────────────────────────────────┐
                  │           Runtime Kernel            │
                  └──────────────────┬──────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
┌──────────▼──────────┐   ┌──────────▼──────────┐   ┌──────────▼──────────┐
│   Workflow Engine   │   │ Capability Registry │   │    Tool Registry    │
└──────────┬──────────┘   └──────────┬──────────┘   └──────────┬──────────┘
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                                    │                                    │
│   ┌───────────────────┐  ┌─────────▼─────────┐  ┌───────────────────┐   │
│   │ PermissionManager │  │    Event Bus      │  │ Structured Logger │   │
│   └───────────────────┘  └───────────────────┘  └───────────────────┘   │
│                        Core Runtime Services                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tested Components & Test Scenarios

### 1. Runtime Kernel (`app.runtime.kernel`)
- **Initialization & Lifecycle**: Validates kernel startup (`initialize()`), agent registration (`register_agent()`), context creation (`create_context()`), context isolation, retrieval, cleanup (`remove_context()`), and orderly shutdown (`shutdown()`).

### 2. Workflow Engine & Queue (`app.engine.workflow`, `app.engine.queue`)
- **State Machine Transitions**: Validates transitions between `CREATED` -> `RUNNING` -> `PAUSED` -> `RUNNING` -> `COMPLETED` / `FAILED`.
- **Task Queue Operations**: Enqueuing tasks (`enqueue()`), FIFO dequeuing (`dequeue()`), and tracking task status updates (`WAITING` -> `RUNNING` -> `COMPLETED`/`FAILED`).

### 3. Capability Registry & Tool Registry (`app.engine.registry`, `app.tools.registry`)
- **Interoperability & Validation**: Registering capabilities and concrete tool adapters, validating required task capabilities (`validate_capabilities()`), updating tool lifecycle state (`ToolState`), and monitoring tool health (`ToolHealth`).

### 4. Permission Manager (`app.core.permissions`)
- **Security & Authorization**: Handling permission requests (`request_permission()`), evaluating risk levels (`RiskLevel`), auto-approving low-risk requests, manual approval (`grant_permission()`) and rejection (`reject_permission()`), event emission, and enforcing permissions with `PermissionDeniedException`.

### 5. Event System (`app.core.events`)
- **Asynchronous Event Propagation**: Publishing events across workflow, task, permission, and tool domains. Validates routed delivery to specific subscribers as well as global event monitoring callbacks (`subscribe_all()`).

### 6. Centralized Logging Framework (`app.core.logging`)
- **Contextual Logging**: Structured JSON logging (`StructuredLogger`) with dynamic field binding (`workflow_id`, `agent_id`, `task_id`) during runtime execution.

### 7. Configuration Manager (`app.core.config`)
- **Runtime Settings**: Validates configuration loading (`ConfigurationManager`, `RuntimeSettings`), default value enforcement, and dynamic environment overrides.

### 8. Shared Exceptions (`app.core.exceptions`)
- **Error Hierarchy & Mapping**: Validates root `AetherPhoenixException` base class, status codes, and context detail payloads for `PermissionDeniedException`, `WorkflowRuntimeException`, `ToolNotFoundException`, and `ValidationException`.

---

## Execution Guide

### Prerequisites
Ensure Python environment dependencies are installed:
```bash
python -m pip install pytest pytest-asyncio anyio pydantic pydantic-settings
```

### Running the Integration Tests
Execute the integration test suite via `pytest`:
```bash
$env:PYTHONPATH="C:\Users\dhany\majorproject\AetherPhoenix;C:\Users\dhany\majorproject\AetherPhoenix\backend"
python -m pytest backend/tests/integration/test_runtime_integration.py -v
```

### Running the Entire Backend Test Suite
```bash
$env:PYTHONPATH="C:\Users\dhany\majorproject\AetherPhoenix;C:\Users\dhany\majorproject\AetherPhoenix\backend"
python -m pytest backend/tests -v
```
