from uuid import uuid4

import pytest
from shared.contracts.event import EventType
from shared.contracts.execution import HealingResult, TaskError
from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)
from shared.contracts.retry import RecoveryPlan, RetryStatus
from shared.contracts.task import (
    RollbackInfo,
    Task,
    TaskCategory,
    TaskPriority,
    TaskStatus,
)
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.recovery_planner import RecoveryStrategy
from app.agents.healing.retry_engine import RetryEngine
from app.agents.healing.root_cause_analyzer import RootCauseAnalysis, RootCauseCategory
from app.core.events.bus import EventBus


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


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def retry_engine(event_bus):
    return RetryEngine(
        event_bus=event_bus, default_max_retries=3, base_backoff_seconds=1.0
    )


@pytest.fixture
def sample_state():
    metadata = WorkflowMetadata(
        workflow_id=uuid4(),
        goal="Test Healing Workflow",
        status=WorkflowStatus.RUNNING,
    )
    return SharedWorkflowState(metadata=metadata)


@pytest.fixture
def sample_task(sample_state):
    task = Task(
        task_id=uuid4(),
        workflow_id=sample_state.metadata.workflow_id,
        task_name="Scrape Web Page",
        description="Scrape target website data",
        required_tool="web_scraper",
        category=TaskCategory.WEB_SCRAPING,
        priority=TaskPriority.MEDIUM,
        expected_output="Extracted text data",
        status=TaskStatus.FAILED,
        retry_count=0,
    )
    sample_state.tasks[task.task_id] = task
    sample_state.failed_tasks.append(task.task_id)
    return task


@pytest.mark.asyncio
async def test_successful_retry(retry_engine, sample_state, sample_task):
    result = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
        reason="Temporary network timeout",
    )

    assert result.success is True
    assert result.status == RetryStatus.TRIGGERED
    assert result.attempt_number == 1
    assert sample_task.retry_count == 1
    assert sample_task.status == TaskStatus.WAITING
    assert sample_task.task_id in sample_state.execution_queue
    assert sample_task.task_id not in sample_state.failed_tasks
    assert len(sample_state.healing_history) == 1
    assert sample_state.healing_history[0].task_id == sample_task.task_id
    assert sample_state.healing_history[0].attempt_number == 1


@pytest.mark.asyncio
async def test_maximum_retry_reached(retry_engine, sample_state, sample_task):
    sample_task.retry_count = 3

    result = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
        max_retries=3,
    )

    assert result.success is False
    assert result.status == RetryStatus.REJECTED_MAX_RETRIES
    assert "maximum retry limit" in result.message
    assert sample_task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_non_retryable_failure_error_code(
    retry_engine, sample_state, sample_task
):
    error = TaskError(
        error_code="PERMISSION_DENIED",
        error_message="User denied permission to run script",
        is_recoverable=True,
    )

    result = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
        error=error,
    )

    assert result.success is False
    assert result.status == RetryStatus.REJECTED_NON_RETRYABLE
    assert "non-retryable" in result.message.lower()


@pytest.mark.asyncio
async def test_non_retryable_flag(retry_engine, sample_state, sample_task):
    error = TaskError(
        error_code="CUSTOM_ERR",
        error_message="Fatal unrecoverable error",
        is_recoverable=False,
    )

    result = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
        error=error,
    )

    assert result.success is False
    assert result.status == RetryStatus.REJECTED_NON_RETRYABLE


@pytest.mark.asyncio
async def test_retryable_failure(retry_engine, sample_state, sample_task):
    error = TaskError(
        error_code="TIMEOUT",
        error_message="Page load timed out",
        is_recoverable=True,
    )

    result = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
        error=error,
    )

    assert result.success is True
    assert result.status == RetryStatus.TRIGGERED
    assert sample_task.retry_count == 1


@pytest.mark.asyncio
async def test_permission_denied_due_to_rejected_request(
    retry_engine, sample_state, sample_task
):
    sample_state.permissions.append(
        PermissionRequest(
            workflow_id=sample_state.metadata.workflow_id,
            task_id=sample_task.task_id,
            permission_type=PermissionType.FILE_SYSTEM_WRITE,
            reason="Write output file",
            risk_level=RiskLevel.MEDIUM,
            status=PermissionStatus.REJECTED,
        )
    )

    result = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
    )

    assert result.success is False
    assert result.status == RetryStatus.REJECTED_PERMISSION_DENIED


@pytest.mark.asyncio
async def test_invalid_task_request(retry_engine, sample_state):
    non_existent_id = uuid4()
    result = await retry_engine.request_retry(
        task_id=non_existent_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
    )

    assert result.success is False
    assert result.status == RetryStatus.ERROR
    assert "not found" in result.message


@pytest.mark.asyncio
async def test_invalid_workflow_state(retry_engine, sample_state, sample_task):
    sample_state.metadata.status = WorkflowStatus.PAUSED

    result = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
    )

    assert result.success is False
    assert result.status == RetryStatus.REJECTED_INVALID_STATE


@pytest.mark.asyncio
async def test_multiple_retry_attempts_and_backoff(
    retry_engine, sample_state, sample_task
):
    # Attempt 1
    res1 = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
    )
    assert res1.success is True
    assert res1.attempt_number == 1
    assert res1.delay_seconds == 1.0

    # Simulate worker failure again
    sample_task.status = TaskStatus.FAILED
    sample_state.failed_tasks.append(sample_task.task_id)

    # Attempt 2
    res2 = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
    )
    assert res2.success is True
    assert res2.attempt_number == 2
    assert res2.delay_seconds == 2.0

    # Attempt 3
    sample_task.status = TaskStatus.FAILED
    res3 = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
    )
    assert res3.success is True
    assert res3.attempt_number == 3
    assert res3.delay_seconds == 4.0

    # Attempt 4 (Exceeds max retries = 3)
    sample_task.status = TaskStatus.FAILED
    res4 = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
    )
    assert res4.success is False
    assert res4.status == RetryStatus.REJECTED_MAX_RETRIES


@pytest.mark.asyncio
async def test_destructive_operation_safety_policy(
    retry_engine, sample_state, sample_task
):
    sample_task.risk_level = "HIGH"
    sample_task.rollback_info = RollbackInfo(rollback_point="checkpoint_1")

    error = TaskError(
        error_code="UNKNOWN_ERROR",
        error_message="Non-transient file deletion error",
        is_recoverable=True,
    )

    # Without approval or transient status -> Rejected
    result_rejected = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
        error=error,
    )
    assert result_rejected.success is False
    assert result_rejected.status == RetryStatus.REJECTED_DESTRUCTIVE_UNAPPROVED

    # With RecoveryPlan approval -> Approved
    plan = RecoveryPlan(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        strategy="APPROVED_RETRY",
        reason="User approved recovery policy",
    )
    result_approved = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
        recovery_plan=plan,
    )
    assert result_approved.success is True
    assert result_approved.status == RetryStatus.TRIGGERED


@pytest.mark.asyncio
async def test_recovery_plan_integration(retry_engine, sample_state, sample_task):
    repl_task = Task(
        task_id=uuid4(),
        workflow_id=sample_state.metadata.workflow_id,
        task_name="Clear Cache Prerequisites",
        description="Clear tool cache before retrying",
        required_tool="cache_cleaner",
        category=TaskCategory.OTHER,
        expected_output="Cache cleared",
    )
    plan = RecoveryPlan(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        strategy="RESTART_TOOL",
        backoff_seconds=5.0,
        replacement_tasks=[repl_task],
        updated_task_params={
            "description": "Scrape target website data with clean session"
        },
        reason="Tool session frozen",
    )

    result = await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
        recovery_plan=plan,
    )

    assert result.success is True
    assert result.delay_seconds == 5.0
    assert sample_task.description == "Scrape target website data with clean session"
    assert repl_task.task_id in sample_state.tasks
    assert repl_task.task_id in sample_state.execution_queue
    assert sample_task.task_id in sample_state.execution_queue


@pytest.mark.asyncio
async def test_retry_events_emitted(event_bus, retry_engine, sample_state, sample_task):
    emitted_events = []

    async def listener(event):
        emitted_events.append(event)

    event_bus.subscribe(EventType.HEALING_STARTED, listener)
    event_bus.subscribe(EventType.TASK_RETRIED, listener)
    event_bus.subscribe(EventType.HEALING_COMPLETED, listener)

    plan = RecoveryPlan(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        strategy="RETRY",
        reason="Network reconnect",
    )

    await retry_engine.request_retry(
        task_id=sample_task.task_id,
        workflow_id=sample_state.metadata.workflow_id,
        state=sample_state,
        recovery_plan=plan,
        reason="Network reconnect",
    )

    event_types = [e.event_type for e in emitted_events]
    assert EventType.HEALING_STARTED in event_types
    assert EventType.TASK_RETRIED in event_types
    assert EventType.HEALING_COMPLETED in event_types
