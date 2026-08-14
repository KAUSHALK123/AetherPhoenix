from uuid import uuid4

import pytest
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.agents.healing.error_parser import ErrorCategory, ParsedError
from app.agents.healing.root_cause_analyzer import (
    RootCauseAnalysis,
    RootCauseAnalyzer,
    RootCauseCategory,
)


@pytest.fixture
def dummy_state():
    return SharedWorkflowState(metadata=WorkflowMetadata(goal="Test Root Cause"))


def create_task(workflow_id) -> Task:
    return Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Dummy Task",
        description="Testing task",
        required_tool="browser_tool",
        category=TaskCategory.OTHER,
        expected_output="dummy output",
        status=TaskStatus.FAILED,
    )


def test_root_cause_permission_denied(dummy_state):
    analyzer = RootCauseAnalyzer()
    task = create_task(dummy_state.metadata.workflow_id)
    parsed = ParsedError(
        category=ErrorCategory.PERMISSIONS,
        normalized_code="PERMISSION_DENIED",
        raw_message="Access denied",
        is_transient=False,
    )

    rc: RootCauseAnalysis = analyzer.analyze(parsed, task, dummy_state)
    assert rc.category == RootCauseCategory.PERMISSION
    assert rc.is_recoverable is False
    assert rc.recommended_strategy == "REQUEST_PERMISSION_AGAIN"


def test_root_cause_tool_unavailable(dummy_state):
    analyzer = RootCauseAnalyzer()
    task = create_task(dummy_state.metadata.workflow_id)
    parsed = ParsedError(
        category=ErrorCategory.TOOL,
        normalized_code="TOOL_UNAVAILABLE",
        raw_message="Tool missing",
        is_transient=False,
    )

    rc: RootCauseAnalysis = analyzer.analyze(parsed, task, dummy_state)
    assert rc.category == RootCauseCategory.TOOL
    assert rc.is_recoverable is True
    assert rc.recommended_strategy == "ALTERNATIVE_TOOL"


def test_root_cause_network_timeout(dummy_state):
    analyzer = RootCauseAnalyzer()
    task = create_task(dummy_state.metadata.workflow_id)
    parsed = ParsedError(
        category=ErrorCategory.NETWORK,
        normalized_code="NETWORK_TIMEOUT",
        raw_message="Connection timed out",
        is_transient=True,
    )

    rc: RootCauseAnalysis = analyzer.analyze(parsed, task, dummy_state)
    assert rc.category == RootCauseCategory.NETWORK
    assert rc.is_recoverable is True
    assert rc.recommended_strategy == "RETRY"


def test_root_cause_destructive_safety_override(dummy_state):
    analyzer = RootCauseAnalyzer()
    task = create_task(dummy_state.metadata.workflow_id)
    task.risk_level = "HIGH"
    parsed = ParsedError(
        category=ErrorCategory.UNKNOWN,
        normalized_code="EXECUTION_ERROR",
        raw_message="Unknown destructive operation failure",
        is_transient=False,
    )

    rc: RootCauseAnalysis = analyzer.analyze(parsed, task, dummy_state)
    assert rc.is_recoverable is False
    assert rc.recommended_strategy == "ESCALATE_USER"
