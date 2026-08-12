"""Integration test suite for Sprint 1 Runtime Infrastructure.

Validates end-to-end interoperability between Runtime Kernel, Workflow Engine,
Capability Registry, Tool Registry, Permission Manager, Event System,
Logging Framework, Configuration Manager, and Shared Exceptions.
"""

from typing import Any, List
from uuid import uuid4

import pytest
from shared.contracts.capability import Capability
from shared.contracts.permission import PermissionStatus, PermissionType, RiskLevel
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.tool import Tool, ToolHealth, ToolState
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.core.config import ConfigurationManager, get_config
from app.core.events.bus import EventBus
from app.core.events.models import Event, EventType
from app.core.exceptions import (
    AetherPhoenixException,
    PermissionDeniedException,
    ToolNotFoundException,
    WorkflowRuntimeException,
)
from app.core.logging import get_logger
from app.core.permissions import PermissionManager
from app.engine.registry import CapabilityRegistry
from app.engine.workflow import WorkflowEngine
from app.runtime.interfaces import AgentRegistration, BaseAgent
from app.runtime.kernel import RuntimeKernel
from app.tools.registry import ToolRegistry


class IntegrationTestAgent(BaseAgent):
    """Mock agent implementation for integration testing."""

    def __init__(self, name: str = "IntegrationAgent", version: str = "1.0.0"):
        self._registration = AgentRegistration(
            name=name, version=version, description="Test Agent"
        )
        self.initialized = False
        self.shut_down = False
        self.executed_tasks: List[str] = []

    @property
    def registration(self) -> AgentRegistration:
        return self._registration

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.shut_down = True

    async def execute(self, task_name: str, *args, **kwargs) -> Any:
        self.executed_tasks.append(task_name)
        return f"Executed: {task_name}"


@pytest.fixture
def runtime_env():
    """Fixture providing a complete initialized runtime environment stack."""
    config_mgr = ConfigurationManager()
    logger = get_logger("integration_test")
    event_bus = EventBus()
    capability_registry = CapabilityRegistry()
    tool_registry = ToolRegistry()
    permission_manager = PermissionManager(event_bus=event_bus)
    kernel = RuntimeKernel()

    return {
        "config_mgr": config_mgr,
        "config": config_mgr.get_config(),
        "logger": logger,
        "event_bus": event_bus,
        "capability_registry": capability_registry,
        "tool_registry": tool_registry,
        "permission_manager": permission_manager,
        "kernel": kernel,
    }


@pytest.mark.asyncio
async def test_end_to_end_runtime_initialization_and_shutdown(runtime_env):
    """Verify runtime kernel lifecycle and multi-component initialization."""
    kernel: RuntimeKernel = runtime_env["kernel"]
    event_bus: EventBus = runtime_env["event_bus"]
    received_events: List[Event] = []

    async def capture_event(evt: Event):
        received_events.append(evt)

    event_bus.subscribe_all(capture_event)

    agent = IntegrationTestAgent()
    kernel.register_agent(agent)
    assert "IntegrationAgent" in kernel.registered_agents

    await kernel.initialize()
    assert kernel.is_running is True
    assert agent.initialized is True

    context = kernel.create_context(session_id="session-integration-001")
    assert context.is_active is True
    assert kernel.get_context(context.context_id) is context

    kernel.remove_context(context.context_id)
    assert context.is_active is False
    assert kernel.get_context(context.context_id) is None

    await kernel.shutdown()
    assert kernel.is_running is False
    assert agent.shut_down is True


@pytest.mark.asyncio
async def test_workflow_engine_lifecycle_and_task_execution(runtime_env):
    """Verify workflow engine state machine and task queue operations."""
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(goal="Integration Workflow Execution")
    )
    engine = WorkflowEngine(state)
    logger = runtime_env["logger"]

    logger.info("Testing workflow lifecycle transitions...")
    assert state.metadata.status == WorkflowStatus.CREATED

    engine.start()
    assert state.metadata.status == WorkflowStatus.RUNNING

    engine.pause()
    assert state.metadata.status == WorkflowStatus.PAUSED

    engine.start()
    assert state.metadata.status == WorkflowStatus.RUNNING

    # Create and enqueue task
    task = Task(
        workflow_id=state.metadata.workflow_id,
        task_name="Process Data",
        description="Data processing step",
        required_tool="data_processor",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="Processed data output",
    )
    engine.enqueue(task)
    assert task.status == TaskStatus.WAITING

    dequeued_task = engine.dequeue()
    assert dequeued_task is not None
    assert dequeued_task.task_id == task.task_id

    engine.update_task_status(task.task_id, TaskStatus.RUNNING)
    assert task.task_id in state.running_tasks

    engine.update_task_status(task.task_id, TaskStatus.COMPLETED)
    assert task.task_id in state.completed_tasks
    assert task.task_id not in state.running_tasks

    engine.complete()
    assert state.metadata.status == WorkflowStatus.COMPLETED


def test_registries_capability_and_tool_interoperability(runtime_env):
    """Verify capability and tool registry lookup, validation, and health updates."""
    cap_reg: CapabilityRegistry = runtime_env["capability_registry"]
    tool_reg: ToolRegistry = runtime_env["tool_registry"]

    capability = Capability(
        name="web_search",
        description="Search the web for information",
        category=TaskCategory.WEB_RESEARCH,
        required_tools=["google_search"],
        enabled=True,
    )
    cap_reg.register(capability)
    assert cap_reg.get("web_search") == capability
    assert cap_reg.validate_capabilities(["web_search"]) is True

    tool = Tool(
        name="google_search",
        description="Google Search Tool Adapter",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.google_search.GoogleSearchAdapter",
    )
    tool_reg.register(tool)
    assert tool_reg.get("google_search") == tool

    tool_reg.update_state("google_search", ToolState.UNAVAILABLE)
    tool_reg.update_health("google_search", ToolHealth.FAILED)
    updated_tool = tool_reg.get("google_search")
    assert updated_tool.status == ToolState.UNAVAILABLE
    assert updated_tool.health == ToolHealth.FAILED


@pytest.mark.asyncio
async def test_event_propagation_across_runtime_modules(runtime_env):
    """Verify asynchronous event publishing and subscription handling."""
    event_bus: EventBus = runtime_env["event_bus"]
    received_workflow_events: List[Event] = []
    received_global_events: List[Event] = []

    async def workflow_handler(evt: Event):
        received_workflow_events.append(evt)

    async def global_handler(evt: Event):
        received_global_events.append(evt)

    event_bus.subscribe(EventType.WORKFLOW_STARTED, workflow_handler)
    event_bus.subscribe_all(global_handler)

    evt1 = Event(
        event_type=EventType.WORKFLOW_STARTED,
        source_component="WorkflowEngine",
        payload={"workflow_id": "wf-100"},
    )
    evt2 = Event(
        event_type=EventType.TASK_COMPLETED,
        source_component="WorkerAgent",
        payload={"task_id": "task-200"},
    )

    await event_bus.publish(evt1)
    await event_bus.publish(evt2)

    assert len(received_workflow_events) == 1
    assert received_workflow_events[0].payload["workflow_id"] == "wf-100"
    assert len(received_global_events) == 2


@pytest.mark.asyncio
async def test_permission_validation_and_enforcement_flow(runtime_env):
    """Verify permission request, approval, event firing, and exception raising."""
    perm_mgr: PermissionManager = runtime_env["permission_manager"]
    event_bus: EventBus = runtime_env["event_bus"]
    captured_events: List[Event] = []

    async def on_event(evt: Event):
        captured_events.append(evt)

    event_bus.subscribe_all(on_event)

    workflow_id = uuid4()

    # 1. Low risk request auto-approved
    req_low = await perm_mgr.request_permission(
        workflow_id=workflow_id,
        permission_type=PermissionType.FILE_SYSTEM,
        reason="Read settings",
        risk_level=RiskLevel.LOW,
    )
    assert req_low.status == PermissionStatus.GRANTED
    assert perm_mgr.check_permission(PermissionType.FILE_SYSTEM, workflow_id) is True

    # 2. High risk request pending & enforced failure
    req_high = await perm_mgr.request_permission(
        workflow_id=workflow_id,
        permission_type=PermissionType.POWERSHELL,
        reason="Execute system script",
        risk_level=RiskLevel.HIGH,
    )
    assert req_high.status == PermissionStatus.PENDING

    with pytest.raises(PermissionDeniedException) as exc_info:
        perm_mgr.enforce_permission(PermissionType.POWERSHELL, workflow_id)

    assert "denied for workflow" in str(exc_info.value)
    assert exc_info.value.code == "PERMISSION_DENIED"

    # 3. Grant pending permission & enforce success
    await perm_mgr.grant_permission(req_high.permission_id)
    assert req_high.status == PermissionStatus.GRANTED
    perm_mgr.enforce_permission(
        PermissionType.POWERSHELL, workflow_id
    )  # Should not raise

    event_types = [e.event_type for e in captured_events]
    assert EventType.PERMISSION_REQUESTED in event_types
    assert EventType.PERMISSION_GRANTED in event_types


def test_shared_exceptions_hierarchy_handling(runtime_env):
    """Verify exceptions hierarchy, status code mappings, and details payload."""
    perm_err = PermissionDeniedException(
        message="Access denied", details={"tool": "powershell"}
    )
    assert isinstance(perm_err, AetherPhoenixException)
    assert perm_err.code == "PERMISSION_DENIED"
    assert perm_err.details["tool"] == "powershell"

    wf_err = WorkflowRuntimeException(message="Invalid state transition")
    assert isinstance(wf_err, AetherPhoenixException)
    assert wf_err.code == "WORKFLOW_RUNTIME_ERROR"

    tool_err = ToolNotFoundException(message="Tool not found")
    assert isinstance(tool_err, AetherPhoenixException)
    assert tool_err.code == "TOOL_NOT_FOUND"


@pytest.mark.asyncio
async def test_unified_runtime_execution_scenario(runtime_env):
    """
    End-to-End unified integration scenario orchestrating Configuration,
    Logger, Event Bus, Kernel, Registries, Permissions, and Workflow Engine.
    """
    config = get_config()
    assert config.PROJECT_NAME == "AetherPhoenix"

    logger = runtime_env["logger"]
    kernel: RuntimeKernel = runtime_env["kernel"]
    cap_reg: CapabilityRegistry = runtime_env["capability_registry"]
    tool_reg: ToolRegistry = runtime_env["tool_registry"]
    perm_mgr: PermissionManager = runtime_env["permission_manager"]

    # 1. Start Kernel
    agent = IntegrationTestAgent(name="UnifiedWorker", version="1.0.0")
    kernel.register_agent(agent)
    await kernel.initialize()

    # 2. Register capabilities and tools
    cap_reg.register(
        Capability(
            name="file_management",
            description="Manage local files",
            category=TaskCategory.FILE_SYSTEM,
            required_tools=["file_writer"],
            enabled=True,
        )
    )
    tool_reg.register(
        Tool(
            name="file_writer",
            description="Write text files",
            version="1.0.0",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="app.tools.file_writer.FileWriterAdapter",
        )
    )

    # 3. Create context & workflow
    ctx = kernel.create_context(session_id="unified-session")
    engine = WorkflowEngine(ctx.shared_state)
    engine.start()

    # 4. Request permission
    wf_id = ctx.shared_state.metadata.workflow_id
    p_req = await perm_mgr.request_permission(
        workflow_id=wf_id,
        permission_type=PermissionType.FILE_SYSTEM,
        reason="Write output artifact",
        risk_level=RiskLevel.LOW,
    )
    assert p_req.status == PermissionStatus.GRANTED
    perm_mgr.enforce_permission(PermissionType.FILE_SYSTEM, wf_id)

    # 5. Enqueue and execute task
    task = Task(
        workflow_id=wf_id,
        task_name="Write Report",
        description="Write final report",
        required_tool="file_writer",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="Final report written",
    )
    engine.enqueue(task)
    popped = engine.dequeue()
    engine.update_task_status(popped.task_id, TaskStatus.RUNNING)

    result = await agent.execute("Write Report")
    logger.info(f"Agent execution output: {result}")

    engine.update_task_status(popped.task_id, TaskStatus.COMPLETED)
    engine.complete()

    # 6. Clean up
    kernel.remove_context(ctx.context_id)
    await kernel.shutdown()

    assert engine.state.metadata.status == WorkflowStatus.COMPLETED
    assert popped.task_id in engine.state.completed_tasks
    assert len(agent.executed_tasks) == 1
