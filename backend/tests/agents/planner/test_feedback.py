import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from shared.contracts.event import EventType as SharedEventType
from shared.contracts.execution import FailureType, HealingResult, TaskError, TaskFailureReport
from shared.contracts.feedback import PlannerFeedback
from shared.contracts.planner import PlannerRequest
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata, WorkflowStatus

from app.agents.planner.agent import PlannerAgent
from app.agents.planner.feedback import PlannerFeedbackLoop, sanitize_sensitive_data
from app.core.events.bus import EventBus
from app.core.events.models import EventType as ModelEventType


def test_sensitive_data_filtering():
    # API key filtering
    text1 = "Error: api_key='abcd1234efgh' is invalid"
    assert "abcd1234efgh" not in sanitize_sensitive_data(text1)
    assert "[REDACTED]" in sanitize_sensitive_data(text1)

    # Password filtering
    text2 = "Failed to connect to db with postgres://admin:supersecret123@localhost:5432/mydb"
    assert "supersecret123" not in sanitize_sensitive_data(text2)
    assert "[REDACTED]" in sanitize_sensitive_data(text2)

    # Authorization header filtering
    text3 = "Authorization: Bearer xyz123secret"
    assert "xyz123secret" not in sanitize_sensitive_data(text3)
    assert "[REDACTED]" in sanitize_sensitive_data(text3)

    # Private key block filtering
    text4 = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQE...\n-----END RSA PRIVATE KEY-----"
    assert "-----BEGIN RSA PRIVATE KEY-----" not in sanitize_sensitive_data(text4)
    assert "[REDACTED]" in sanitize_sensitive_data(text4)


def test_empty_feedback_validation():
    # If failure_summary, healing_summary and capability_failure are all None, it should raise ValidationError
    with pytest.raises(ValidationError):
        PlannerFeedback(workflow_id=uuid4())


def test_invalid_feedback_validation():
    # Invalid failure_type string instead of FailureType enum
    with pytest.raises(ValidationError):
        PlannerFeedback(
            workflow_id=uuid4(),
            failure_summary={"task_id": uuid4(), "failure_type": "NOT_A_REAL_TYPE"},
        )


def test_successful_recovery_feedback():
    workflow_id = uuid4()
    task_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Create slide deck",
        )
    )
    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="generate-ppt-slides",
        description="Task to generate slide deck",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="pptx presentation",
    )
    state.tasks[task_id] = task

    failure_report = TaskFailureReport(
        task_id=task_id,
        workflow_id=workflow_id,
        failure_type=FailureType.TOOL_ERROR,
        message="Transient slide generation error",
        retryability=True,
    )

    healing_result = HealingResult(
        task_id=task_id,
        workflow_id=workflow_id,
        root_cause="Transient slide generation error",
        recovery_strategy="Retry slide creation",
        attempt_number=1,
        success=True,
    )

    loop = PlannerFeedbackLoop(event_bus=EventBus())
    feedback = loop.generate_feedback(
        state=state,
        failure_report=failure_report,
        healing_result=healing_result,
    )

    assert feedback.workflow_id == workflow_id
    assert feedback.failure_summary is not None
    assert feedback.failure_summary.task_name == "generate-ppt-slides"
    assert feedback.failure_summary.tool_used == "ppt_tool"
    assert feedback.healing_summary is not None
    assert feedback.healing_summary.outcome == "SUCCESS"
    assert feedback.healing_summary.successful_strategy == "Retry slide creation"
    # No replanning context should be created since it was successfully recovered
    assert feedback.replanning_context is None


def test_failed_recovery_feedback_and_replanning_required():
    workflow_id = uuid4()
    task_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Create PDF from PPT",
        )
    )
    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="convert-to-pdf",
        description="Task to convert presentation to PDF",
        required_tool="pdf_generator",
        category=TaskCategory.PDF_GENERATION,
        expected_output="pdf export",
    )
    state.tasks[task_id] = task

    failure_report = TaskFailureReport(
        task_id=task_id,
        workflow_id=workflow_id,
        failure_type=FailureType.TIMEOUT,
        message="PDF converter timed out",
        retryability=False,
    )

    healing_result = HealingResult(
        task_id=task_id,
        workflow_id=workflow_id,
        root_cause="PDF converter timed out",
        recovery_strategy="Retry with increased timeout",
        attempt_number=3,
        success=False,
    )

    loop = PlannerFeedbackLoop(event_bus=EventBus())
    feedback = loop.generate_feedback(
        state=state,
        failure_report=failure_report,
        healing_result=healing_result,
    )

    assert feedback.healing_summary is not None
    assert feedback.healing_summary.outcome == "UNRECOVERABLE"
    assert feedback.replanning_context is not None
    assert "Healing failed to recover task" in feedback.replanning_context.trigger_reason
    assert feedback.replanning_context.original_goal == "Create PDF from PPT"


def test_capability_failure_feedback():
    workflow_id = uuid4()
    task_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Search web secure",
        )
    )
    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="run-web-search",
        description="Task to perform web search",
        required_tool="web_search_tool",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="search result",
    )
    state.tasks[task_id] = task

    # Permission denied is a typical capability failure
    failure_report = TaskFailureReport(
        task_id=task_id,
        workflow_id=workflow_id,
        failure_type=FailureType.PERMISSION_DENIED,
        message="Access to web search tool is denied",
        retryability=False,
    )

    loop = PlannerFeedbackLoop(event_bus=EventBus())
    feedback = loop.generate_feedback(
        state=state,
        failure_report=failure_report,
    )

    assert feedback.capability_failure is not None
    assert feedback.capability_failure.tool_name == "web_search_tool"
    assert feedback.capability_failure.is_permanent is True
    assert feedback.replanning_context is not None
    assert "Permanent capability failure" in feedback.replanning_context.trigger_reason


@pytest.mark.asyncio
async def test_process_and_publish_events():
    workflow_id = uuid4()
    task_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Run python execution",
        )
    )
    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="python-script",
        description="Task to execute python script",
        required_tool="python",
        category=TaskCategory.PYTHON,
        expected_output="script stdout",
    )
    state.tasks[task_id] = task

    failure_report = TaskFailureReport(
        task_id=task_id,
        workflow_id=workflow_id,
        failure_type=FailureType.TOOL_UNAVAILABLE,
        message="Python executor tool not found",
        retryability=False,
    )

    event_bus = EventBus()
    events_received = []

    async def on_event(evt):
        events_received.append(evt)

    event_bus.subscribe_all(on_event)

    loop = PlannerFeedbackLoop(event_bus=event_bus)
    await loop.process_and_publish_feedback(
        state=state,
        failure_report=failure_report,
    )

    assert len(events_received) == 2
    types = [e.event_type for e in events_received]
    assert ModelEventType.FEEDBACK_GENERATED in types
    assert ModelEventType.REPLANNING_TRIGGERED in types


def test_planner_integration_filtering():
    agent = PlannerAgent()

    # Define a custom capability registry for testing
    from shared.contracts.capability import Capability
    from app.engine.registry import CapabilityRegistry
    cap_reg = CapabilityRegistry()
    cap_reg.register(
        Capability(
            name="tool_a",
            description="Tool A description",
            category=TaskCategory.OTHER,
            required_tools=["tool_a"],
        )
    )
    cap_reg.register(
        Capability(
            name="tool_b",
            description="Tool B description",
            category=TaskCategory.OTHER,
            required_tools=["tool_b"],
        )
    )
    agent.capability_engine.registry = cap_reg

    # 1. Normal plan request
    req1 = PlannerRequest(
        session_id="integration-session-1",
        message="Create a new user securely",
    )
    res1 = agent.process_request(req1)
    assert res1.status == "ready"
    plan_data1 = json.loads(res1.reply)
    # The capability registry defaults to first enabled cap (tool_a)
    assert plan_data1["tasks"][1]["required_tool"] == "tool_a"

    # 2. Plan request with feedback indicating tool_a is permanently failed
    feedback = PlannerFeedback(
        workflow_id=uuid4(),
        capability_failure={
            "tool_name": "tool_a",
            "category": "OTHER",
            "is_permanent": True,
            "details": "Tool A failed permanently due to network restriction",
        }
    )
    req2 = PlannerRequest(
        session_id="integration-session-2",
        message="Create a new user securely",
        feedback=feedback,
    )
    res2 = agent.process_request(req2)
    assert res2.status == "ready"
    plan_data2 = json.loads(res2.reply)
    # It should dynamically consider other capability (tool_b) since tool_a is unavailable
    assert plan_data2["tasks"][1]["required_tool"] == "tool_b"


def test_circular_feedback_loop_prevention():
    agent = PlannerAgent()

    session_id = "circular-test-session"
    feedback = PlannerFeedback(
        workflow_id=uuid4(),
        failure_summary={
            "task_id": uuid4(),
            "task_name": "task-failed",
            "tool_used": "some-tool",
            "failure_type": FailureType.TIMEOUT,
            "error_message": "Repeated timeout error",
        },
        healing_summary={
            "attempts": 3,
            "outcome": "UNRECOVERABLE",
        },
        replanning_context={
            "trigger_reason": "Healing failed to recover task",
            "original_goal": "Goal that causes timeout loops",
        }
    )

    req = PlannerRequest(
        session_id=session_id,
        message="Create a new user securely",
        feedback=feedback,
    )

    # 1st replan
    res = agent.process_request(req)
    assert res.status == "ready"

    # 2nd replan
    res = agent.process_request(req)
    assert res.status == "ready"

    # 3rd replan
    res = agent.process_request(req)
    assert res.status == "ready"

    # 4th replan -> Should detect circular loop and terminate
    res = agent.process_request(req)
    assert res.status == "error"
    assert "Circular planning loop detected" in res.reply
    assert res.action == "terminate"
