"""
End-to-End Integration Tests for Healing Agent (Issue #128).

Tests the complete execution lifecycle:
USER -> PLANNER -> WORKFLOW ENGINE -> WORKER -> TOOL -> SUPERVISOR -> SUCCESS

And failure recovery lifecycle:
SUPERVISOR -> FAILURE -> ERROR PARSER -> ROOT CAUSE ANALYZER -> RECOVERY PLANNER
-> RETRY ENGINE -> WORKER RE-EXECUTION -> SUPERVISOR -> SUCCESS / ESCALATION
-> PLANNER FEEDBACK LOOP
"""

from typing import List
from uuid import uuid4

import pytest
from shared.contracts.event import RuntimeEvent
from shared.contracts.execution import (
    ExecutionResult,
    FailureType,
    SupervisorDecision,
    TaskError,
    TaskFailureReport,
)
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.self_healing_loop import HealingState, SelfHealingLoop
from app.agents.planner.feedback import PlannerFeedbackLoop
from app.agents.supervisor.agent import SupervisorAgent
from app.core.events.bus import EventBus


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def workflow_state() -> SharedWorkflowState:
    meta = WorkflowMetadata(
        workflow_id=uuid4(),
        goal="Autonomous Web Intelligence Gathering",
        status=WorkflowStatus.RUNNING,
    )
    return SharedWorkflowState(metadata=meta)


@pytest.fixture
def healing_loop(event_bus: EventBus) -> SelfHealingLoop:
    return SelfHealingLoop(
        event_bus=event_bus,
        max_retries=3,
        max_healing_attempts=5,
    )


@pytest.fixture
def supervisor(event_bus: EventBus, healing_loop: SelfHealingLoop) -> SupervisorAgent:
    return SupervisorAgent(
        event_bus=event_bus,
        healing_loop=healing_loop,
        max_retries=3,
    )


@pytest.fixture
def feedback_loop(event_bus: EventBus) -> PlannerFeedbackLoop:
    return PlannerFeedbackLoop(event_bus=event_bus)


@pytest.mark.anyio
async def test_successful_execution_without_healing(supervisor, workflow_state):
    """
    Test standard execution where task succeeds and Supervisor verifies it
    without triggering the Self-Healing Loop.
    """
    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_state.metadata.workflow_id,
        task_name="Scrape Target Webpage",
        description="Extract raw html data from source",
        required_tool="browser_tool",
        category=TaskCategory.WEB_SCRAPING,
        priority=TaskPriority.HIGH,
        expected_output="HTML document",
        status=TaskStatus.COMPLETED,
    )
    workflow_state.tasks[task.task_id] = task

    # Task completes successfully
    result = ExecutionResult(
        task_id=task.task_id,
        workflow_id=workflow_state.metadata.workflow_id,
        success=True,
        output={"result": "HTML document retrieved successfully"},
    )

    validation = await supervisor.execute(
        task=task,
        result=result,
        state=workflow_state,
    )

    assert validation.is_valid is True
    assert validation.decision == SupervisorDecision.PASSED
    assert task.task_id not in workflow_state.failed_tasks
    assert len(workflow_state.healing_history) == 0


@pytest.mark.anyio
async def test_transient_failure_recovery_and_reexecution(
    supervisor, workflow_state, event_bus
):
    """
    Test transient network/timeout failure:
    Worker Failure -> Supervisor Detection -> Error Parser -> Root Cause ->
    Recovery Plan -> Retry Engine Re-enqueues -> Supervisor Verification -> SUCCESS
    """
    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_state.metadata.workflow_id,
        task_name="Download Dataset",
        description="Download remote telemetry dataset",
        required_tool="browser_tool",
        category=TaskCategory.WEB_RESEARCH,
        priority=TaskPriority.MEDIUM,
        expected_output="Dataset file",
        status=TaskStatus.FAILED,
    )
    workflow_state.tasks[task.task_id] = task
    workflow_state.failed_tasks.append(task.task_id)

    published_events: List[RuntimeEvent] = []

    async def capture(evt: RuntimeEvent):
        published_events.append(evt)

    event_bus.subscribe_all(capture)

    # 1. Task fails with transient timeout
    err = TaskError(
        error_code="TIMEOUT",
        error_message="Network connection timed out after 30000ms",
        is_recoverable=True,
    )

    # 2. Supervisor detects failure and routes to Healing
    healed = await supervisor.execute(task, workflow_state, error=err)
    assert healed is True

    # 3. Task is queued for re-execution
    assert task.retry_count == 1
    assert task.status == TaskStatus.WAITING
    assert task.task_id in workflow_state.execution_queue
    assert task.task_id not in workflow_state.failed_tasks
    assert len(workflow_state.healing_history) == 1
    assert workflow_state.healing_history[0].success is True

    # 4. Re-execution simulation: worker runs attempt 2 and succeeds
    task.status = TaskStatus.RUNNING
    exec_success = ExecutionResult(
        task_id=task.task_id,
        workflow_id=workflow_state.metadata.workflow_id,
        success=True,
        output={"result": "Dataset file downloaded"},
    )
    validation = await supervisor.execute(
        task=task,
        result=exec_success,
        state=workflow_state,
    )
    assert validation.is_valid is True
    assert validation.decision == SupervisorDecision.PASSED


@pytest.mark.anyio
async def test_tool_unavailable_alternative_recovery(healing_loop, workflow_state):
    """
    Test unavailable tool scenario:
    Tool fails -> Root Cause classifies TOOL_UNAVAILABLE ->
    Recovery Planner formulates replacement task with alternative tool.
    """
    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_state.metadata.workflow_id,
        task_name="Scrape Pricing Table",
        description="Scrape pricing structure from portal",
        required_tool="browser_tool",
        category=TaskCategory.WEB_SCRAPING,
        expected_output="Pricing table JSON",
        status=TaskStatus.FAILED,
    )
    workflow_state.tasks[task.task_id] = task
    workflow_state.failed_tasks.append(task.task_id)

    failure_report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=workflow_state.metadata.workflow_id,
        failure_type=FailureType.TOOL_UNAVAILABLE,
        message="browser_tool is disabled by system policy",
        retryability=False,
    )

    result = await healing_loop.process_failure(task, failure_report, workflow_state)

    assert result.success is True
    assert len(result.replacement_tasks) == 1
    alt_task = result.replacement_tasks[0]
    assert alt_task.required_tool in ("web_research_tool", "web_research")
    assert alt_task.task_id in workflow_state.execution_queue


@pytest.mark.anyio
async def test_max_retries_exhaustion_escalation(
    healing_loop, workflow_state, feedback_loop
):
    """
    Test retry limit exhaustion:
    Repeated failures reach limit -> Healing halts -> Escalates ->
    Planner receives structured recovery failure signal.
    """
    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_state.metadata.workflow_id,
        task_name="Query Protected Endpoint",
        description="Fetch sensitive endpoint payload",
        required_tool="api_tool",
        category=TaskCategory.OTHER,
        expected_output="Payload",
        status=TaskStatus.FAILED,
        retry_count=3,  # Already at maximum retry threshold
    )
    workflow_state.tasks[task.task_id] = task
    workflow_state.failed_tasks.append(task.task_id)

    err = TaskError(
        error_code="SERVICE_UNAVAILABLE",
        error_message="HTTP 503 Service Unavailable",
        is_recoverable=True,
    )

    result = await healing_loop.process_failure(task, err, workflow_state)

    assert result.success is False
    assert healing_loop.current_state in (HealingState.EXHAUSTED, HealingState.FAILED)

    # Process feedback into Planner Feedback Loop
    feedback = feedback_loop.generate_feedback(
        state=workflow_state,
        failure_report=TaskFailureReport(
            task_id=task.task_id,
            workflow_id=workflow_state.metadata.workflow_id,
            failure_type=FailureType.WORKER_FAILURE,
            message="HTTP 503 Service Unavailable",
            retryability=False,
        ),
        healing_result=result,
    )
    assert feedback is not None
    assert feedback.workflow_id == workflow_state.metadata.workflow_id
    assert feedback.healing_summary is not None
    assert feedback.healing_summary.outcome == "UNRECOVERABLE"


@pytest.mark.anyio
async def test_permission_denial_unrecoverable_flow(healing_loop, workflow_state):
    """
    Test permission denial:
    Permission rejected -> Diagnosed as non-recoverable ->
    Self-Healing Loop transitions to FAILED and marks result unsuccessful.
    """
    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_state.metadata.workflow_id,
        task_name="Modify System Registry",
        description="Write registry key for telemetry",
        required_tool="powershell_executor",
        category=TaskCategory.POWERSHELL,
        expected_output="Registry Key",
        status=TaskStatus.FAILED,
    )
    workflow_state.tasks[task.task_id] = task

    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=workflow_state.metadata.workflow_id,
        failure_type=FailureType.PERMISSION_DENIED,
        message="User rejected REGISTRY write permission request",
        retryability=False,
    )

    result = await healing_loop.process_failure(task, report, workflow_state)

    assert result.success is False
    assert result.root_cause == "PERMISSION"
    assert healing_loop.current_state == HealingState.FAILED


@pytest.mark.anyio
async def test_infinite_loop_prevention(healing_loop, workflow_state):
    """
    Test loop protection:
    Exact duplicate failures on same task signature are halted at limit 3.
    """
    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_state.metadata.workflow_id,
        task_name="Crashing Script",
        description="Script with memory fault",
        required_tool="powershell_executor",
        category=TaskCategory.OTHER,
        expected_output="Done",
        status=TaskStatus.FAILED,
    )
    workflow_state.tasks[task.task_id] = task

    err = TaskError(
        error_code="INTERNAL_CRASH",
        error_message="Segmentation fault (core dumped)",
        is_recoverable=True,
    )

    sig = (
        str(task.task_id),
        "RUNTIME",
        "General runtime execution failure during task processing.",
    )
    healing_loop.retry_engine._failure_signature_counts[sig] = 3

    result = await healing_loop.process_failure(task, err, workflow_state)

    assert result.success is False
    assert healing_loop.current_state == HealingState.FAILED
