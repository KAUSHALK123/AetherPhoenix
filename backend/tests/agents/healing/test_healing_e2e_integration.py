import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from shared.contracts.execution import ExecutionResult, TaskError, HealingResult
from shared.contracts.task import Task, TaskCategory, TaskStatus, TaskType
from shared.contracts.tool import Tool, ToolState
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.agents.healing.self_healing_loop import SelfHealingLoop, HealingState
from app.agents.healing.retry_engine import RetryEngine
from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.tools.registry import ToolRegistry
from app.tools.adapter import BaseToolAdapter


class FlakyToolAdapter(BaseToolAdapter):
    """Adapter that fails N times before succeeding, or fails permanently."""

    def __init__(self, fail_count: int = 1):
        self.fail_count = fail_count
        self.attempts = 0

    async def execute(self, task: Task, *args, **kwargs) -> ExecutionResult:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                output={},
                error=TaskError(
                    error_code="TIMEOUT",
                    error_message=f"Flaky failure attempt {self.attempts}",
                    is_recoverable=True,
                ),
            )
        return ExecutionResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            success=True,
            output={"result": "Success on retry"},
            error=None,
        )


@pytest.fixture
def healing_env():
    tool_registry = ToolRegistry()
    flaky_adapter = FlakyToolAdapter(fail_count=1)
    
    tool = Tool(
        name="flaky_tool",
        version="1.0.0",
        status=ToolState.READY,
        adapter="flaky_adapter",
    )
    tool_registry.register(tool)

    mock_history = MagicMock()
    mock_storage = MagicMock()

    worker = WorkerAgent(
        tool_registry=tool_registry,
        task_history_service=mock_history,
        artifact_storage_service=mock_storage,
    )
    worker.register_adapter("flaky_adapter", flaky_adapter)

    mock_bus = MagicMock()
    mock_bus.publish = AsyncMock()

    retry_engine = RetryEngine(event_bus=mock_bus, default_max_retries=3)
    healing_agent = SelfHealingLoop(
        event_bus=mock_bus,
        retry_engine=retry_engine,
        max_retries=3,
    )

    supervisor = SupervisorAgent(
        event_bus=mock_bus,
        healing_loop=healing_agent,
        retry_engine=retry_engine,
        max_retries=3,
    )

    return {
        "worker": worker,
        "supervisor": supervisor,
        "healing_agent": healing_agent,
        "flaky_adapter": flaky_adapter,
    }


@pytest.mark.asyncio
async def test_e2e_healing_worker_failure_supervisor_detection_healing_recovery(healing_env):
    """
    Verify complete self-healing integration loop:
    Worker Failure -> Supervisor Detection -> Healing Agent Recovery -> Worker Re-execution
    """
    worker = healing_env["worker"]
    supervisor = healing_env["supervisor"]
    healing_agent = healing_env["healing_agent"]
    flaky_adapter = healing_env["flaky_adapter"]

    workflow_id = uuid.uuid4()
    task = Task(
        task_id=uuid.uuid4(),
        workflow_id=workflow_id,
        task_name="Flaky Task",
        description="Flaky task description",
        expected_output="Success on retry",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="flaky_tool",
    )
    metadata = WorkflowMetadata(workflow_id=workflow_id, goal="Test Goal")
    state = SharedWorkflowState(metadata=metadata)
    state.tasks[task.task_id] = task

    # 1. First execution attempt (Worker fails)
    result_1 = await worker.execute(task)
    assert result_1.success is False

    # 2. Supervisor detects failure
    validation = await supervisor.execute(task, result_1, state)
    assert validation.is_valid is False

    # 3. Healing Agent processes failure and generates recovery plan
    healing_result = await healing_agent.process_failure(
        task=task,
        failure_input=result_1,
        state=state,
    )

    assert healing_result is not None
    assert healing_agent.current_state in (HealingState.COMPLETED, HealingState.RETRYING, HealingState.IDLE)

    # 4. Worker re-execution following recovery
    task.retry_count += 1
    result_2 = await worker.execute(task)

    # 5. Worker succeeds on retry
    assert result_2.success is True
    assert flaky_adapter.attempts == 2

    # 6. Supervisor validates re-execution output
    final_validation = await supervisor.execute(task, result_2, state)
    assert final_validation.is_valid is True
    assert state.tasks[task.task_id].status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_healing_retry_limits_and_permanent_failure(healing_env):
    """
    Verify retry limits are enforced and permanent failures do not cause infinite loops.
    """
    worker = healing_env["worker"]
    healing_agent = healing_env["healing_agent"]
    flaky_adapter = healing_env["flaky_adapter"]
    flaky_adapter.fail_count = 100  # Always fails

    workflow_id = uuid.uuid4()
    task = Task(
        task_id=uuid.uuid4(),
        workflow_id=workflow_id,
        task_name="Perpetually Failing Task",
        description="Failing task description",
        expected_output="Success result",
        category=TaskCategory.OTHER,
        task_type=TaskType.LEAF,
        required_tool="flaky_tool",
        retry_count=3,  # Already reached max retries
        max_retries=3,
    )
    metadata = WorkflowMetadata(workflow_id=workflow_id, goal="Test Goal")
    state = SharedWorkflowState(metadata=metadata)
    state.tasks[task.task_id] = task

    result = await worker.execute(task)
    assert result.success is False

    # Process failure when retry limit is exceeded
    healing_result = await healing_agent.process_failure(
        task=task,
        failure_input=result,
        state=state,
    )

    assert healing_result.success is False
    assert healing_agent.current_state in (HealingState.EXHAUSTED, HealingState.ESCALATED, HealingState.FAILED)
