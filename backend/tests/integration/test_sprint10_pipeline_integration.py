import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import (
    ExecutionResult,
    TaskError,
)
from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.tool import Tool, ToolHealth, ToolState
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.self_healing_loop import SelfHealingLoop
from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus
from app.core.permissions import PermissionManager
from app.engine.orchestrator import PipelineOrchestrator
from app.planner.session import SessionManager
from app.services.artifact_storage import (
    ArtifactStorageService,
    LocalFileSystemArtifactStorageProvider,
)
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry


class ConfigurableIntegrationAdapter(BaseToolAdapter):
    """Integration Mock Tool Adapter simulating success and failure execution paths."""

    def __init__(self) -> None:
        self.call_count = 0
        self.side_effects = {}

    async def execute(self, task: Task) -> ExecutionResult:
        self.call_count += 1
        name = task.task_name

        if name in self.side_effects:
            effect = self.side_effects[name]
            if isinstance(effect, list) and effect:
                beh = effect.pop(0)
            else:
                beh = effect

            if isinstance(beh, Exception):
                raise beh
            elif isinstance(beh, ExecutionResult):
                beh.task_id = task.task_id
                beh.workflow_id = task.workflow_id
                return beh
            return beh

        # Default success with expected output key
        expected_key = task.expected_output or "result"
        return ExecutionResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            success=True,
            output={expected_key: f"Executed {name} successfully"},
        )


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def integration_env(temp_dir):
    event_bus = EventBus()
    tool_registry = ToolRegistry()
    permission_manager = PermissionManager(event_bus=event_bus)

    # Storage
    provider = LocalFileSystemArtifactStorageProvider(base_dir=temp_dir)
    storage_service = ArtifactStorageService(provider=provider)

    worker = WorkerAgent(
        tool_registry=tool_registry,
        permission_manager=permission_manager,
    )

    # Adapter Setup
    adapter = ConfigurableIntegrationAdapter()
    worker.register_adapter("configurable_adapter", adapter)

    # Healing and Supervision
    healing_loop = SelfHealingLoop(event_bus=event_bus, max_retries=2)
    supervisor = SupervisorAgent(
        event_bus=event_bus,
        healing_loop=healing_loop,
        max_retries=2,
    )

    orchestrator = PipelineOrchestrator(
        worker_agent=worker,
        supervisor_agent=supervisor,
        event_bus=event_bus,
        healing_agent=None,  # Not required for non-replanning tests
    )

    # Register mock tools
    tools = [
        Tool(
            name="test_tool",
            adapter="configurable_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
        ),
        Tool(
            name="ppt_tool",
            adapter="configurable_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
        ),
        Tool(
            name="secure_tool",
            adapter="configurable_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            required_permissions=["file_system"],
        ),
    ]
    for t in tools:
        tool_registry.register(t)

    return {
        "event_bus": event_bus,
        "tool_registry": tool_registry,
        "permission_manager": permission_manager,
        "storage_service": storage_service,
        "worker": worker,
        "supervisor": supervisor,
        "orchestrator": orchestrator,
        "adapter": adapter,
    }


@pytest.mark.asyncio
async def test_simple_successful_task(integration_env):
    """Verify simple successful task pipeline execution."""
    orchestrator = integration_env["orchestrator"]
    workflow_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Simple Goal",
            status=WorkflowStatus.CREATED,
        )
    )

    task = Task(
        workflow_id=workflow_id,
        task_name="Simple Task",
        description="Verify success",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        expected_output="result",
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    final_state = await orchestrator.run_workflow(state)
    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_pptx_generation_integration(integration_env):
    """Verify PowerPoint presentation generation tool adapter execution."""
    orchestrator = integration_env["orchestrator"]
    workflow_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Create Presentation Goal",
            status=WorkflowStatus.CREATED,
        )
    )

    task = Task(
        workflow_id=workflow_id,
        task_name="PPT Generator Task",
        description="Build ppt presentation",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="presentation",
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    final_state = await orchestrator.run_workflow(state)
    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED
    assert integration_env["adapter"].call_count > 0


@pytest.mark.asyncio
async def test_permission_required_and_approved(integration_env):
    """Verify workflow execution of a permission-required task when approved."""
    orchestrator = integration_env["orchestrator"]
    permission_manager = integration_env["permission_manager"]
    workflow_id = uuid4()

    # Pre-register required permission as GRANTED
    perm_req = PermissionRequest(
        workflow_id=workflow_id,
        permission_type=PermissionType.FILE_SYSTEM,
        status=PermissionStatus.GRANTED,
        reason="Security clearance for file system write",
        risk_level=RiskLevel.MEDIUM,
    )
    permission_manager.request_permission(perm_req)

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="File IO Goal",
            status=WorkflowStatus.CREATED,
        )
    )
    state.permissions.append(perm_req)

    task = Task(
        workflow_id=workflow_id,
        task_name="Write output",
        description="Persist files",
        required_tool="secure_tool",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="output",
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    final_state = await orchestrator.run_workflow(state)
    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_permission_required_and_rejected(integration_env):
    """Verify workflow execution of a permission-required task when rejected."""
    orchestrator = integration_env["orchestrator"]
    permission_manager = integration_env["permission_manager"]
    workflow_id = uuid4()

    # Pre-register required permission as REJECTED
    perm_req = PermissionRequest(
        workflow_id=workflow_id,
        permission_type=PermissionType.FILE_SYSTEM,
        status=PermissionStatus.REJECTED,
        reason="Security clearance for file system write",
        risk_level=RiskLevel.MEDIUM,
    )
    permission_manager.request_permission(perm_req)

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Secure File IO Goal",
            status=WorkflowStatus.CREATED,
        )
    )
    state.permissions.append(perm_req)

    task = Task(
        workflow_id=workflow_id,
        task_name="Write output",
        description="Persist files",
        required_tool="secure_tool",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="output",
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    final_state = await orchestrator.run_workflow(state)
    # The task should fail since permission is rejected
    assert final_state.metadata.status == WorkflowStatus.FAILED
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_unknown_tool_failure(integration_env):
    """Verify execution fails cleanly when requesting a tool missing from registry."""
    orchestrator = integration_env["orchestrator"]
    workflow_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Execute Unregistered Tool",
            status=WorkflowStatus.CREATED,
        )
    )

    task = Task(
        workflow_id=workflow_id,
        task_name="Execute Unknown Tool",
        description="Call non-existent capability",
        required_tool="mystery_tool_99",
        category=TaskCategory.OTHER,
        expected_output="result",
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    final_state = await orchestrator.run_workflow(state)
    assert final_state.metadata.status == WorkflowStatus.FAILED
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_worker_failure_and_healing_retry(integration_env):
    """Verify worker failure triggers supervisor analysis and succeeds on retry."""
    orchestrator = integration_env["orchestrator"]
    adapter = integration_env["adapter"]
    workflow_id = uuid4()

    # Simulate first execution failing, second succeeding
    task_name = "Healed Task"
    adapter.side_effects[task_name] = [
        ExecutionResult(
            task_id=uuid4(),
            workflow_id=workflow_id,
            success=False,
            error=TaskError(
                error_code="TIMEOUT",
                error_message="Worker timeout",
                is_recoverable=True,
            ),
        ),
        ExecutionResult(
            task_id=uuid4(),
            workflow_id=workflow_id,
            success=True,
            output={"result": "Recovered successfully!"},
        ),
    ]

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Healing Recovery Goal",
            status=WorkflowStatus.CREATED,
        )
    )

    task = Task(
        workflow_id=workflow_id,
        task_name=task_name,
        description="Expect self-healing to recover this",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        expected_output="result",
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    final_state = await orchestrator.run_workflow(state)
    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED
    assert task.retry_count == 1


@pytest.mark.asyncio
async def test_retry_exhaustion(integration_env):
    """Verify retry exhaustion triggers final failure after max limits reached."""
    orchestrator = integration_env["orchestrator"]
    adapter = integration_env["adapter"]
    workflow_id = uuid4()

    # Simulate persistent failures
    task_name = "Persistent Failing Task"
    persistent_fail = ExecutionResult(
        task_id=uuid4(),
        workflow_id=workflow_id,
        success=False,
        error=TaskError(
            error_code="TIMEOUT",
            error_message="Worker timeout",
            is_recoverable=True,
        ),
    )
    adapter.side_effects[task_name] = [
        persistent_fail,
        persistent_fail,
        persistent_fail,
        persistent_fail,
    ]

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Exhausted Recovery Goal",
            status=WorkflowStatus.CREATED,
        )
    )

    task = Task(
        workflow_id=workflow_id,
        task_name=task_name,
        description="Fails repeatedly until limit reached",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        expected_output="result",
    )
    state.tasks[task.task_id] = task
    state.execution_queue.append(task.task_id)

    final_state = await orchestrator.run_workflow(state, max_retries=2)
    assert final_state.metadata.status == WorkflowStatus.FAILED
    assert task.status == TaskStatus.FAILED
    assert task.retry_count >= 2


@pytest.mark.asyncio
async def test_dependency_and_parallel_execution(integration_env):
    """Verify dependency ordering and parallel execution of tasks."""
    orchestrator = integration_env["orchestrator"]
    workflow_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Dependency Chain Goal",
            status=WorkflowStatus.CREATED,
        )
    )

    # Task A: Root
    task_a = Task(
        workflow_id=workflow_id,
        task_name="Task A",
        description="Root task",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        expected_output="out_a",
    )
    # Task B: Depends on A
    task_b = Task(
        workflow_id=workflow_id,
        task_name="Task B",
        description="Dependent task",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        expected_output="out_b",
        dependencies=[task_a.task_id],
    )
    # Task C: Depends on A (Parallel with B)
    task_c = Task(
        workflow_id=workflow_id,
        task_name="Task C",
        description="Concurrent task",
        required_tool="test_tool",
        category=TaskCategory.OTHER,
        expected_output="out_c",
        dependencies=[task_a.task_id],
    )

    for t in (task_a, task_b, task_c):
        state.tasks[t.task_id] = t
        state.execution_queue.append(t.task_id)

    final_state = await orchestrator.run_workflow(state)
    assert final_state.metadata.status == WorkflowStatus.COMPLETED
    assert task_a.status == TaskStatus.COMPLETED
    assert task_b.status == TaskStatus.COMPLETED
    assert task_c.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_artifact_persistence(integration_env):
    """Verify registration, local persistence, and retrieval of workflow artifacts."""
    storage_service = integration_env["storage_service"]
    workflow_id = uuid4()
    task_id = uuid4()

    art = Artifact(
        workflow_id=workflow_id,
        task_id=task_id,
        name="summary.json",
        filepath="dummy/path",
        artifact_type=ArtifactType.REPORTS,
    )
    content = b'{"results": "success"}'

    saved = await storage_service.register_artifact(artifact=art, content=content)
    assert saved.size_bytes == len(content)
    assert saved.checksum == Artifact.compute_checksum(content)

    meta = await storage_service.get_artifact(art.artifact_id)
    assert meta is not None
    assert meta.name == "summary.json"

    retrieved = await storage_service.get_artifact_content(art.artifact_id)
    assert retrieved == content


def test_multi_turn_planner_session():
    """Verify multi-turn session tracking and context preservation in SessionManager."""
    manager = SessionManager()
    session = manager.create_session()

    session.add_turn("Turn 1 Goal", {"plan_id": "1"})
    session.add_turn("Turn 2 Clarification", {"plan_id": "2"})

    history = session.get_history_dicts()
    assert len(history) == 2
    assert history[0]["message"] == "Turn 1 Goal"
    assert history[1]["message"] == "Turn 2 Clarification"
    assert session.get_context_summary() == "Previous goal: Turn 2 Clarification"
