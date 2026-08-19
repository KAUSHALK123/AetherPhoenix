"""Validation tests for the 3 P0 Self-Healing Integration fixes:
- F3: Unknown tool error classified as TOOL_NOT_FOUND and non-retryable
- F4: EscalationHandler invoked on retry exhaustion and non-retryable failures
- F5: REPLANNING_TRIGGERED event subscriber wired into PlannerAgent
"""

import asyncio
import uuid

import pytest
from shared.contracts.event import EventType as ContractEventType
from shared.contracts.execution import (
    ExecutionResult,
    TaskError,
)
from shared.contracts.feedback import (
    CapabilityFailureInfo,
    FailureSummary,
    PlannerFeedback,
    ReplanningContext,
)
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.escalation import EscalationHandler
from app.agents.healing.self_healing_loop import SelfHealingLoop
from app.agents.planner.agent import PlannerAgent
from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus
from app.core.events.models import Event as ModelEvent
from app.core.events.models import EventType as ModelEventType
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_f3_unknown_tool_non_retryable():
    """F3: Missing/unregistered tool produces TOOL_NOT_FOUND,

    is non-retryable, and triggers no retry loops.
    """
    event_bus = EventBus()
    registry = ToolRegistry()  # Empty registry
    worker = WorkerAgent(tool_registry=registry)

    wf_id = uuid.uuid4()
    task_id = uuid.uuid4()

    task = Task(
        task_id=task_id,
        workflow_id=wf_id,
        task_name="Test Unknown Tool Task",
        description="Task requesting nonexistent tool",
        required_tool="TEST_NONEXISTENT_TOOL",
        expected_output="Output",
        category=TaskCategory.OTHER,
        status=TaskStatus.CREATED,
    )

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(workflow_id=wf_id, goal="Test F3 Unknown Tool"),
        tasks={task_id: task},
    )

    # 1. Execute task with Worker
    result: ExecutionResult = await worker.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "TOOL_NOT_FOUND"
    assert result.error.is_recoverable is False
    assert "not found in registry" in result.error.error_message.lower()

    # 2. Verify Supervisor & SelfHealing classify it as non-retryable
    healing_loop = SelfHealingLoop(event_bus=event_bus, max_retries=3)
    can_retry, reason = healing_loop.retry_engine.can_retry(
        task=task,
        state=state,
        root_cause=healing_loop.root_cause_analyzer.analyze(
            parsed_error=healing_loop.error_parser.parse(result, task=task),
            task=task,
            state=state,
        ),
    )

    assert can_retry is False
    assert (
        "non-retryable" in reason.lower()
        or "not eligible" in reason.lower()
        or "tool" in reason.lower()
    )


@pytest.mark.asyncio
async def test_f4_escalation_handler_on_retry_exhaustion():
    """F4: EscalationHandler is invoked when healing retries

    are exhausted or blocked.
    """
    event_bus = EventBus()
    escalation_events = []

    async def on_escalation(event):
        escalation_events.append(event)

    event_bus.subscribe(ContractEventType.ESCALATION_REQUESTED, on_escalation)
    event_bus.subscribe(ModelEventType.ESCALATION_REQUESTED, on_escalation)

    escalation_handler = EscalationHandler(event_bus=event_bus)
    healing_loop = SelfHealingLoop(
        event_bus=event_bus,
        escalation_handler=escalation_handler,
        max_retries=2,
        max_healing_attempts=2,
    )

    wf_id = uuid.uuid4()
    task_id = uuid.uuid4()

    task = Task(
        task_id=task_id,
        workflow_id=wf_id,
        task_name="Exhaustion Task",
        description="Task that exhausts retries",
        required_tool="dummy_tool",
        expected_output="Output",
        category=TaskCategory.OTHER,
        status=TaskStatus.FAILED,
        retry_count=2,  # Already reached max_retries
    )

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(workflow_id=wf_id, goal="Test F4 Escalation"),
        tasks={task_id: task},
    )

    # Trigger failure processing on already-exhausted task
    failure_input = ExecutionResult(
        task_id=task_id,
        workflow_id=wf_id,
        success=False,
        error=TaskError(
            error_code="TIMEOUT",
            error_message="Network timeout exceeded",
            is_recoverable=True,
        ),
    )

    healing_result = await healing_loop.process_failure(task, failure_input, state)

    assert healing_result.success is False
    assert healing_loop.current_state.value in ("EXHAUSTED", "FAILED", "ESCALATED")

    # Verify EscalationHandler was invoked and escalation event was published
    assert len(escalation_events) >= 1
    assert state.metadata.status in (
        WorkflowStatus.FAILED,
        WorkflowStatus.ESCALATED,
        WorkflowStatus.BLOCKED,
    )


@pytest.mark.asyncio
async def test_f5_replanning_event_triggers_planner():
    """F5: REPLANNING_TRIGGERED event is received by PlannerAgent

    and generates an updated plan.
    """
    from shared.contracts.execution import FailureType

    event_bus = EventBus()
    planner = PlannerAgent(event_bus=event_bus)

    wf_id = uuid.uuid4()
    session_id = f"sess-f5-{uuid.uuid4()}"

    feedback = PlannerFeedback(
        workflow_id=wf_id,
        failure_summary=FailureSummary(
            task_id=uuid.uuid4(),
            task_name="Scrape Web Data",
            tool_used="browser_automation",
            failure_type=FailureType.TOOL_UNAVAILABLE,
            error_message="Browser driver failed to connect",
        ),
        capability_failure=CapabilityFailureInfo(
            tool_name="browser_automation",
            category="BROWSER",
            is_permanent=True,
            details="Driver missing",
        ),
        replanning_context=ReplanningContext(
            trigger_reason="Permanent browser automation failure; fallback required",
            original_goal="Create a PowerPoint presentation about EV technology",
            suggested_alternative_tools=["ppt_tool"],
        ),
    )

    # Publish REPLANNING_TRIGGERED event on event bus
    event = ModelEvent(
        workflow_id=str(wf_id),
        event_type=ModelEventType.REPLANNING_TRIGGERED,
        source_component="PlannerFeedbackLoop",
        payload={
            "trigger_reason": feedback.replanning_context.trigger_reason,
            "feedback": feedback.model_dump(mode="json"),
            "workflow_id": str(wf_id),
            "session_id": session_id,
            "goal": "Create a PowerPoint presentation about EV technology",
        },
    )

    await event_bus.publish(event)
    await asyncio.sleep(0.1)  # Allow async event handler to execute

    # Verify PlannerAgent processed the event and generated an updated plan
    assert str(wf_id) in planner.latest_replanning_responses
    response = planner.latest_replanning_responses[str(wf_id)]
    assert response.status == "ready"
    assert response.action == "execute_plan"
    assert response.session_id == session_id
