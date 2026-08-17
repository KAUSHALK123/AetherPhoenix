from uuid import uuid4

import pytest
from shared.contracts.event import EventType
from shared.contracts.execution import (
    ExecutionMetrics,
    ExecutionResult,
    TaskError,
    WorkerReexecutionRequest,
    WorkerReexecutionResult,
)
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.tool import Tool, ToolState
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.worker.agent import WorkerAgent
from app.agents.worker.reexecution import WorkerReexecutionManager
from app.core.events.bus import EventBus
from app.core.permissions.manager import PermissionManager
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry


class DummyRecoveryPlan:
    def __init__(self, plan_id=None, strategy="RETRY", replacement_tasks=None):
        self.plan_id = plan_id or uuid4()
        self.strategy = strategy
        self.replacement_tasks = replacement_tasks or []


class DummyToolAdapter(BaseToolAdapter):
    """Mock Tool Adapter for testing Worker Re-execution."""

    def __init__(self, name: str = "dummy_adapter", should_succeed: bool = True):
        self.name = name
        self.should_succeed = should_succeed

    async def execute(self, task: Task, *args, **kwargs) -> ExecutionResult:
        if self.should_succeed:
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output={"result": "Re-execution successful ppt generation"},
                logs=[f"Adapter executed task {task.task_id}"],
                metrics=ExecutionMetrics(execution_time_ms=120.0),
            )
        else:
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=[f"Adapter failed task {task.task_id}"],
                error=TaskError(
                    error_code="ADAPTER_FAILURE",
                    error_message="Tool adapter execution failed",
                ),
                metrics=ExecutionMetrics(execution_time_ms=50.0),
            )


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def tool_registry():
    registry = ToolRegistry()
    tool = Tool(
        name="ppt_generator",
        version="1.0.0",
        description="Generates PowerPoint presentations",
        adapter="dummy_adapter",
        category="PPT_GENERATION",
        status=ToolState.READY,
    )
    registry.register(tool)
    return registry


@pytest.fixture
def permission_manager():
    return PermissionManager(mode="ASSISTED")


@pytest.fixture
def worker_agent(tool_registry, permission_manager):
    agent = WorkerAgent(
        tool_registry=tool_registry, permission_manager=permission_manager
    )
    adapter = DummyToolAdapter("dummy_adapter", should_succeed=True)
    agent.register_adapter("dummy_adapter", adapter)
    return agent


@pytest.fixture
def workflow_state():
    metadata = WorkflowMetadata(goal="Generate PPT", status=WorkflowStatus.RUNNING)
    return SharedWorkflowState(metadata=metadata)


def create_task(workflow_id) -> Task:
    return Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Generate PPT",
        description="Generate presentation deck",
        required_tool="ppt_generator",
        category=TaskCategory.PPT_GENERATION,
        expected_output="deck.pptx",
        status=TaskStatus.FAILED,
        retry_count=0,
    )


@pytest.mark.anyio
async def test_successful_worker_reexecution_flow(
    worker_agent, workflow_state, event_bus
):
    reexec_mgr = WorkerReexecutionManager()
    task = create_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    published_events = []

    async def capture(evt):
        published_events.append(evt)

    event_bus.subscribe_all(capture)

    # 1. Create re-execution request
    req: WorkerReexecutionRequest = reexec_mgr.create_reexecution_request(
        task=task, state=workflow_state
    )

    assert req.task_id == task.task_id
    assert req.attempt_number == 1
    assert len(task.attempt_history) == 1
    assert task.current_attempt_id == req.attempt_id

    # 2. Process re-execution through WorkerAgent
    res: WorkerReexecutionResult = await reexec_mgr.process_reexecution(
        request=req,
        worker_agent=worker_agent,
        state=workflow_state,
        event_bus=event_bus,
    )

    assert res.execution_result.success is True
    assert res.task_id == task.task_id
    assert res.attempt_id == req.attempt_id
    assert res.attempt_number == 1

    # Verify event publication
    event_types = [e.event_type for e in published_events]
    assert EventType.WORKER_REEXECUTION_STARTED in event_types
    assert EventType.WORKER_REEXECUTION_COMPLETED in event_types


@pytest.mark.anyio
async def test_failed_worker_reexecution_flow(
    tool_registry, permission_manager, workflow_state, event_bus
):
    # Setup failing adapter
    failing_agent = WorkerAgent(
        tool_registry=tool_registry, permission_manager=permission_manager
    )
    failing_adapter = DummyToolAdapter("dummy_adapter", should_succeed=False)
    failing_agent.register_adapter("dummy_adapter", failing_adapter)

    reexec_mgr = WorkerReexecutionManager()
    task = create_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    published_events = []

    async def capture(evt):
        published_events.append(evt)

    event_bus.subscribe_all(capture)

    req = reexec_mgr.create_reexecution_request(task=task, state=workflow_state)
    res = await reexec_mgr.process_reexecution(
        request=req,
        worker_agent=failing_agent,
        state=workflow_state,
        event_bus=event_bus,
    )

    assert res.execution_result.success is False
    assert res.execution_result.error.error_code == "ADAPTER_FAILURE"

    event_types = [e.event_type for e in published_events]
    assert EventType.WORKER_REEXECUTION_STARTED in event_types
    assert EventType.WORKER_REEXECUTION_FAILED in event_types


@pytest.mark.anyio
async def test_multiple_attempts_and_preserved_history(worker_agent, workflow_state):
    reexec_mgr = WorkerReexecutionManager()
    task = create_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    # Attempt 1
    req1 = reexec_mgr.create_reexecution_request(task, state=workflow_state)
    res1 = await reexec_mgr.process_reexecution(req1, worker_agent, workflow_state)
    assert res1.attempt_number == 1

    # Attempt 2
    req2 = reexec_mgr.create_reexecution_request(task, state=workflow_state)
    res2 = await reexec_mgr.process_reexecution(req2, worker_agent, workflow_state)
    assert res2.attempt_number == 2

    # Attempt 3
    req3 = reexec_mgr.create_reexecution_request(task, state=workflow_state)
    res3 = await reexec_mgr.process_reexecution(req3, worker_agent, workflow_state)
    assert res3.attempt_number == 3

    # Verify task ID is strictly preserved across all attempts
    assert task.task_id == req1.task_id == req2.task_id == req3.task_id
    # Verify previous attempt history is preserved and not deleted
    assert len(task.attempt_history) == 3
    assert req1.attempt_id in res3.previous_attempt_ids
    assert req2.attempt_id in res3.previous_attempt_ids


@pytest.mark.anyio
async def test_permission_denied_during_reexecution(tool_registry, workflow_state):
    # Require permission on tool
    tool_registry.get("ppt_generator").required_permissions = ["FILE_WRITE"]
    strict_perm_mgr = PermissionManager(mode="SAFE")

    agent = WorkerAgent(tool_registry=tool_registry, permission_manager=strict_perm_mgr)
    agent.register_adapter("dummy_adapter", DummyToolAdapter("dummy_adapter"))

    reexec_mgr = WorkerReexecutionManager()
    task = create_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    req = reexec_mgr.create_reexecution_request(task, state=workflow_state)
    res = await reexec_mgr.process_reexecution(req, agent, workflow_state)

    assert res.execution_result.success is False
    assert res.execution_result.error.error_code == "PERMISSION_DENIED"


@pytest.mark.anyio
async def test_invalid_recovery_request_handling(worker_agent, workflow_state):
    reexec_mgr = WorkerReexecutionManager()
    invalid_req = WorkerReexecutionRequest(
        task_id=uuid4(),  # Missing from workflow_state
        workflow_id=workflow_state.metadata.workflow_id,
        attempt_number=1,
    )

    res = await reexec_mgr.process_reexecution(
        invalid_req, worker_agent, workflow_state
    )
    assert res.execution_result.success is False
    assert res.execution_result.error.error_code == "INVALID_REEXECUTION_REQUEST"


@pytest.mark.anyio
async def test_worker_reexecution_via_agent_method(worker_agent, workflow_state):
    reexec_mgr = WorkerReexecutionManager()
    task = create_task(workflow_state.metadata.workflow_id)
    workflow_state.tasks[task.task_id] = task

    req = reexec_mgr.create_reexecution_request(task, state=workflow_state)
    exec_res = await worker_agent.reexecute(req, workflow_state)

    assert exec_res.success is True
    assert task.current_attempt_id == req.attempt_id
