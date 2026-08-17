from typing import Any, Dict, List
from uuid import uuid4

import pytest
from shared.contracts.event import EventType
from shared.contracts.execution import ExecutionResult, TaskError
from shared.contracts.planner import PlannerOutput
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.tool import Tool, ToolHealth, ToolState
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus
from app.core.permissions import PermissionManager
from app.engine.orchestrator import PipelineOrchestrator
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry


class ConfigurableMockAdapter(BaseToolAdapter):
    """Dynamically configurable mock tool adapter for integration tests."""

    def __init__(self) -> None:
        self.call_count = 0
        self.behavior: Dict[str, List[Any]] = {}

    async def execute(self, task: Task) -> ExecutionResult:
        self.call_count += 1
        name = task.task_name

        behaviors = self.behavior.get(name, [])
        if behaviors:
            beh = behaviors.pop(0)
            if isinstance(beh, Exception):
                raise beh
            elif isinstance(beh, ExecutionResult):
                beh.task_id = task.task_id
                beh.workflow_id = task.workflow_id
                return beh
            return beh

        # Default success execution result matching expected output key
        expected_key = task.expected_output or "result"
        return ExecutionResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            success=True,
            output={expected_key: f"Completed {name} successfully"},
        )


@pytest.fixture
def test_setup():
    """Provides a complete pipeline testing setup."""
    event_bus = EventBus()
    tool_registry = ToolRegistry()
    permission_manager = PermissionManager(event_bus=event_bus)
    worker = WorkerAgent(
        tool_registry=tool_registry, permission_manager=permission_manager
    )
    supervisor = SupervisorAgent(event_bus=event_bus)
    orchestrator = PipelineOrchestrator(
        worker_agent=worker, supervisor_agent=supervisor, event_bus=event_bus
    )

    # Instantiate mock adapter and register with WorkerAgent
    adapter = ConfigurableMockAdapter()
    worker.register_adapter("mock_adapter", adapter)

    # Register mock tools in ToolRegistry
    tools = [
        Tool(
            name="web_search_tool",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="mock_adapter",
        ),
        Tool(
            name="ppt_tool",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="mock_adapter",
        ),
        Tool(
            name="pdf_generator",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="mock_adapter",
        ),
    ]
    for t in tools:
        tool_registry.register(t)

    return {
        "event_bus": event_bus,
        "tool_registry": tool_registry,
        "permission_manager": permission_manager,
        "worker": worker,
        "supervisor": supervisor,
        "orchestrator": orchestrator,
        "adapter": adapter,
    }


@pytest.mark.asyncio
async def test_end_to_end_electric_car_scenario(test_setup):
    """
    Verifies the main success path (electric car PPT -> PDF scenario).
    Task dependencies: Research -> PPT -> PDF.
    All tasks succeed validation and workflow reaches COMPLETED status.
    """
    orchestrator: PipelineOrchestrator = test_setup["orchestrator"]
    event_bus: EventBus = test_setup["event_bus"]

    # Capture all published events
    received_events = []

    async def capture_event(evt):
        received_events.append(evt)

    event_bus.subscribe_all(capture_event)

    workflow_id = uuid4()
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Create a PPT about electric cars and export it as PDF",
        )
    )

    # 1. Define Tasks
    task_research = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="electric-car-research",
        description="Search for electric car statistics",
        required_tool="web_search_tool",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="research data",
        success_criteria=["contains battery facts"],
    )

    task_ppt = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="electric-car-ppt",
        description="Generate PPT based on research",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="pptx presentation",
        success_criteria=["file format is pptx"],
        dependencies=[task_research.task_id],
    )

    task_pdf = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="electric-car-pdf",
        description="Convert PPT presentation to PDF format",
        required_tool="pdf_generator",
        category=TaskCategory.PDF_GENERATION,
        expected_output="pdf export",
        success_criteria=["file format is pdf"],
        dependencies=[task_ppt.task_id],
    )

    # Add tasks to state
    state.tasks[task_research.task_id] = task_research
    state.tasks[task_ppt.task_id] = task_ppt
    state.tasks[task_pdf.task_id] = task_pdf

    # Define PlannerOutput with dependency graph
    state.planner_output = PlannerOutput(
        workflow_spec="E2E Spec",
        tasks=[task_research, task_ppt, task_pdf],
        dependency_graph={
            task_research.task_id: [],
            task_ppt.task_id: [task_research.task_id],
            task_pdf.task_id: [task_ppt.task_id],
        },
    )

    state.execution_queue.append(task_research.task_id)
    state.execution_queue.append(task_ppt.task_id)
    state.execution_queue.append(task_pdf.task_id)

    # Run workflow orchestrator
    final_state = await orchestrator.run_workflow(state)

    # Assert workflow status is COMPLETED
    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task_research.status == TaskStatus.COMPLETED
    assert task_ppt.status == TaskStatus.COMPLETED
    assert task_pdf.status == TaskStatus.COMPLETED

    # Assert progress is correctly synchronized
    assert final_state.progress.completed_tasks == 3
    assert final_state.progress.total_tasks == 3
    assert final_state.progress.overall_percentage == 100.0

    # Assert events were fired in the expected order
    event_types = [evt.event_type for evt in received_events]
    assert EventType.WORKFLOW_STARTED in event_types
    assert EventType.TASK_STARTED in event_types
    assert EventType.TASK_COMPLETED in event_types
    assert EventType.WORKFLOW_COMPLETED in event_types


@pytest.mark.asyncio
async def test_workflow_failure_and_downstream_blocking(test_setup):
    """
    Verifies that when a parent task fails non-recoverably:
    1. Parent task status goes to FAILED.
    2. Downstream task dependencies are marked as BLOCKED.
    3. Workflow status reaches FAILED.
    """
    orchestrator: PipelineOrchestrator = test_setup["orchestrator"]
    adapter: ConfigurableMockAdapter = test_setup["adapter"]

    workflow_id = uuid4()
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Test workflow failure propagation",
        )
    )

    task_parent = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="failing-parent",
        description="Fails non-recoverably",
        required_tool="web_search_tool",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="output data",
        success_criteria=["criteria"],
    )

    task_child = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="blocked-child",
        description="Blocked by failing parent",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="slides file",
        success_criteria=["criteria"],
        dependencies=[task_parent.task_id],
    )

    state.tasks[task_parent.task_id] = task_parent
    state.tasks[task_child.task_id] = task_child

    state.planner_output = PlannerOutput(
        workflow_spec="Failure Spec",
        tasks=[task_parent, task_child],
        dependency_graph={
            task_parent.task_id: [],
            task_child.task_id: [task_parent.task_id],
        },
    )

    state.execution_queue.append(task_parent.task_id)
    state.execution_queue.append(task_child.task_id)

    # Configure parent task to fail with a non-recoverable error
    adapter.behavior["failing-parent"] = [
        ExecutionResult(
            task_id=task_parent.task_id,
            workflow_id=workflow_id,
            success=False,
            error=TaskError(
                error_code="CRITICAL_FAILURE",
                error_message="Non-recoverable database failure.",
                is_recoverable=False,  # Should block retries
            ),
        )
    ]

    final_state = await orchestrator.run_workflow(state)

    # Verify task and workflow statuses
    assert final_state.metadata.status == WorkflowStatus.FAILED
    assert task_parent.status == TaskStatus.FAILED
    assert task_child.status == TaskStatus.BLOCKED

    # Verify progress state propagates failure/blocking count
    assert final_state.progress.failed_tasks == 1
    assert final_state.progress.blocked_tasks == 1
    assert final_state.progress.completed_tasks == 0


@pytest.mark.asyncio
async def test_transient_failure_and_controlled_retry(test_setup):
    """
    Verifies that when a transient failure occurs:
    1. Supervisor detects validation failure and triggers controlled retry.
    2. Event for TASK_RETRIED is published.
    3. Workflow retries, succeeds on next attempt, and reaches COMPLETED status.
    """
    orchestrator: PipelineOrchestrator = test_setup["orchestrator"]
    adapter: ConfigurableMockAdapter = test_setup["adapter"]
    event_bus: EventBus = test_setup["event_bus"]

    received_events = []

    async def capture_event(evt):
        received_events.append(evt)

    event_bus.subscribe_all(capture_event)

    workflow_id = uuid4()
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Test transient failure retry",
        )
    )

    task_retry = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="retry-task",
        description="Fails once then succeeds",
        required_tool="web_search_tool",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="output data",
        success_criteria=["criteria"],
    )

    state.tasks[task_retry.task_id] = task_retry

    state.planner_output = PlannerOutput(
        workflow_spec="Retry Spec",
        tasks=[task_retry],
        dependency_graph={
            task_retry.task_id: [],
        },
    )

    state.execution_queue.append(task_retry.task_id)

    # Configure: first run returns transient recoverable error,
    # second run returns success
    adapter.behavior["retry-task"] = [
        ExecutionResult(
            task_id=task_retry.task_id,
            workflow_id=workflow_id,
            success=False,
            error=TaskError(
                error_code="TRANSIENT_TIMEOUT",
                error_message="Network connection timed out.",
                is_recoverable=True,
            ),
        ),
        ExecutionResult(
            task_id=task_retry.task_id,
            workflow_id=workflow_id,
            success=True,
            output={"output data": "Successful transient recovery"},
        ),
    ]

    final_state = await orchestrator.run_workflow(state)

    # Verify task and workflow statuses
    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task_retry.status == TaskStatus.COMPLETED
    assert task_retry.retry_count == 1

    # Verify that the TASK_RETRIED event was fired
    event_types = [evt.event_type for evt in received_events]
    assert EventType.TASK_RETRIED in event_types


@pytest.mark.asyncio
async def test_parallel_task_execution(test_setup):
    """
    Verifies parallel task processing:
    1. Independent tasks execute concurrently.
    2. A dependent downstream task is kept pending until both
       independent branches finish.
    """
    orchestrator: PipelineOrchestrator = test_setup["orchestrator"]
    adapter: ConfigurableMockAdapter = test_setup["adapter"]

    workflow_id = uuid4()
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Test parallel branch execution",
        )
    )

    task_a = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="task-a",
        description="Independent task A",
        required_tool="web_search_tool",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="a data",
        success_criteria=["criteria"],
    )

    task_b = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="task-b",
        description="Independent task B",
        required_tool="web_search_tool",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="b data",
        success_criteria=["criteria"],
    )

    task_c = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="task-c",
        description="Dependent task C",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="combined presentation",
        success_criteria=["criteria"],
        dependencies=[task_a.task_id, task_b.task_id],
    )

    state.tasks[task_a.task_id] = task_a
    state.tasks[task_b.task_id] = task_b
    state.tasks[task_c.task_id] = task_c

    state.planner_output = PlannerOutput(
        workflow_spec="Parallel Spec",
        tasks=[task_a, task_b, task_c],
        dependency_graph={
            task_a.task_id: [],
            task_b.task_id: [],
            task_c.task_id: [task_a.task_id, task_b.task_id],
        },
    )

    state.execution_queue.append(task_a.task_id)
    state.execution_queue.append(task_b.task_id)
    state.execution_queue.append(task_c.task_id)

    # Monitor execution order during the run
    started_tasks = []

    # Wrap adapter execute to track call order
    orig_execute = adapter.execute

    async def track_execute(t: Task):
        started_tasks.append(t.task_name)
        return await orig_execute(t)

    adapter.execute = track_execute

    final_state = await orchestrator.run_workflow(state)

    # Verify everything completed
    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task_a.status == TaskStatus.COMPLETED
    assert task_b.status == TaskStatus.COMPLETED
    assert task_c.status == TaskStatus.COMPLETED

    # Assert independent task-a and task-b started before task-c
    assert "task-a" in started_tasks
    assert "task-b" in started_tasks
    assert "task-c" in started_tasks
    assert started_tasks.index("task-c") > started_tasks.index("task-a")
    assert started_tasks.index("task-c") > started_tasks.index("task-b")
