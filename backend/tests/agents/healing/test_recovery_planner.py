from uuid import uuid4

import pytest
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.agents.healing.recovery_planner import (
    RecoveryPlan,
    RecoveryPlanner,
    RecoveryStrategy,
)
from app.agents.healing.root_cause_analyzer import RootCauseAnalysis, RootCauseCategory


@pytest.fixture
def dummy_state():
    return SharedWorkflowState(metadata=WorkflowMetadata(goal="Test Recovery Planner"))


def create_task(workflow_id) -> Task:
    return Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Scrape Website",
        description="Scrape target website data",
        required_tool="browser_tool",
        category=TaskCategory.WEB_SCRAPING,
        expected_output="scraped_data",
        status=TaskStatus.FAILED,
    )


def test_recovery_planner_retry_strategy(dummy_state):
    planner = RecoveryPlanner()
    task = create_task(dummy_state.metadata.workflow_id)
    rc = RootCauseAnalysis(
        category=RootCauseCategory.NETWORK,
        summary="Transient network timeout",
        explanation="Network error",
        is_recoverable=True,
        recommended_strategy="RETRY",
    )

    plan: RecoveryPlan = planner.plan(rc, task, dummy_state)
    assert plan.strategy == RecoveryStrategy.RETRY
    assert plan.is_executable is True
    assert plan.delay_seconds >= 5.0
    assert len(plan.replacement_tasks) == 0


def test_recovery_planner_alternative_tool(dummy_state):
    planner = RecoveryPlanner()
    task = create_task(dummy_state.metadata.workflow_id)
    rc = RootCauseAnalysis(
        category=RootCauseCategory.TOOL,
        summary="Browser tool crashed",
        explanation="Tool failure",
        is_recoverable=True,
        recommended_strategy="ALTERNATIVE_TOOL",
    )

    plan: RecoveryPlan = planner.plan(rc, task, dummy_state)
    assert plan.strategy == RecoveryStrategy.ALTERNATIVE_TOOL
    assert plan.is_executable is True
    assert len(plan.replacement_tasks) == 1
    assert plan.replacement_tasks[0].required_tool == "web_research_tool"


def test_recovery_planner_non_recoverable_escalate(dummy_state):
    planner = RecoveryPlanner()
    task = create_task(dummy_state.metadata.workflow_id)
    rc = RootCauseAnalysis(
        category=RootCauseCategory.PERMISSION,
        summary="Permission denied by user",
        explanation="Permission error",
        is_recoverable=False,
        recommended_strategy="REQUEST_PERMISSION_AGAIN",
    )

    plan: RecoveryPlan = planner.plan(rc, task, dummy_state)
    assert plan.strategy == RecoveryStrategy.REQUEST_PERMISSION_AGAIN
    assert plan.is_executable is False
    assert plan.requires_permission is True
