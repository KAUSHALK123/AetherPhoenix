from uuid import uuid4

import pytest
from shared.contracts.execution import HealingResult
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.agents.healing.recovery_planner import RecoveryPlan, RecoveryStrategy
from app.agents.healing.retry_engine import RetryEngine
from app.agents.healing.root_cause_analyzer import RootCauseAnalysis, RootCauseCategory


@pytest.fixture
def dummy_state():
    return SharedWorkflowState(metadata=WorkflowMetadata(goal="Test Retry Engine"))


def create_task(workflow_id) -> Task:
    return Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Search Web",
        description="Search web results",
        required_tool="browser_tool",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="results",
        status=TaskStatus.FAILED,
        retry_count=0,
    )


def test_retry_engine_can_retry_success(dummy_state):
    engine = RetryEngine(default_max_retries=3, default_max_healing_attempts=5)
    task = create_task(dummy_state.metadata.workflow_id)
    rc = RootCauseAnalysis(
        category=RootCauseCategory.NETWORK,
        summary="Timeout",
        explanation="Network error",
        is_recoverable=True,
    )

    can, reason = engine.can_retry(task, dummy_state, rc)
    assert can is True
    assert reason == "Retry permitted."


def test_retry_engine_max_retries_limit(dummy_state):
    engine = RetryEngine(default_max_retries=3, default_max_healing_attempts=5)
    task = create_task(dummy_state.metadata.workflow_id)
    task.retry_count = 3
    rc = RootCauseAnalysis(
        category=RootCauseCategory.NETWORK,
        summary="Timeout",
        explanation="Network error",
        is_recoverable=True,
    )

    can, reason = engine.can_retry(task, dummy_state, rc)
    assert can is False
    assert "max retry limit" in reason.lower()


def test_retry_engine_max_healing_attempts_limit(dummy_state):
    engine = RetryEngine(default_max_retries=5, default_max_healing_attempts=2)
    task = create_task(dummy_state.metadata.workflow_id)
    dummy_state.healing_history = [
        HealingResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            root_cause="NETWORK",
            recovery_strategy="RETRY",
            attempt_number=1,
            success=True,
        ),
        HealingResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            root_cause="NETWORK",
            recovery_strategy="RETRY",
            attempt_number=2,
            success=True,
        ),
    ]
    rc = RootCauseAnalysis(
        category=RootCauseCategory.NETWORK,
        summary="Timeout",
        explanation="Network error",
        is_recoverable=True,
    )

    can, reason = engine.can_retry(task, dummy_state, rc)
    assert can is False
    assert "max healing attempts limit" in reason.lower()


def test_retry_engine_infinite_loop_protection(dummy_state):
    engine = RetryEngine()
    task = create_task(dummy_state.metadata.workflow_id)
    rc = RootCauseAnalysis(
        category=RootCauseCategory.RUNTIME,
        summary="Identical Crash",
        explanation="Crash",
        is_recoverable=True,
    )

    sig = (str(task.task_id), rc.category.value, rc.summary[:30])
    engine._failure_signature_counts[sig] = 3

    can, reason = engine.can_retry(task, dummy_state, rc)
    assert can is False
    assert "infinite loop detected" in reason.lower()


def test_retry_engine_execute_recovery_re_enqueue(dummy_state):
    engine = RetryEngine()
    task = create_task(dummy_state.metadata.workflow_id)
    dummy_state.tasks[task.task_id] = task
    dummy_state.failed_tasks.append(task.task_id)

    rc = RootCauseAnalysis(
        category=RootCauseCategory.NETWORK,
        summary="Timeout",
        explanation="Network error",
        is_recoverable=True,
    )
    plan = RecoveryPlan(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        strategy=RecoveryStrategy.RETRY,
        description="Retry task",
        is_executable=True,
    )

    res: HealingResult = engine.execute_recovery(
        plan, task, dummy_state, rc, attempt_number=1
    )
    assert res.success is True
    assert task.retry_count == 1
    assert task.status == TaskStatus.WAITING
    assert task.task_id in dummy_state.execution_queue
    assert task.task_id not in dummy_state.failed_tasks
