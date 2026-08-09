import asyncio
import logging
from typing import Any
from uuid import uuid4

import pytest
from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
)
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.core.config import Settings
from app.core.exceptions import AetherPhoenixException
from app.engine.registry import CapabilityRegistry
from app.engine.workflow import WorkflowEngine
from app.runtime.interfaces import AgentRegistration, BaseAgent
from app.runtime.kernel import RuntimeKernel
from app.tools.registry import ToolRegistry

# --- Mocks ---


class MockPermissionManager:
    """Mock Permission Manager since full implementation is missing in develop."""

    def request_permission(self, request: PermissionRequest) -> PermissionRequest:
        request.status = PermissionStatus.GRANTED
        return request


class MockRuntimeAgent(BaseAgent):
    """A basic runtime agent to test registry and kernel integration."""

    def __init__(self, name: str = "TestAgent"):
        self._registration = AgentRegistration(name=name, version="1.0.0")
        self.initialized = False

    @property
    def registration(self) -> AgentRegistration:
        return self._registration

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.initialized = False

    async def execute(self, *args, **kwargs) -> Any:
        return "Success"


# --- Tests ---


@pytest.fixture
def kernel():
    return RuntimeKernel()


@pytest.fixture
def workflow_state():
    return SharedWorkflowState(metadata=WorkflowMetadata(goal="Test goal"))


@pytest.mark.anyio
async def test_runtime_initialization_and_config(kernel):
    """Test: Runtime Kernel + Configuration Manager"""
    settings = Settings()
    assert settings.ENVIRONMENT in ["development", "production", "testing"]

    agent = MockRuntimeAgent("InitAgent")
    kernel.register_agent(agent)

    await kernel.initialize()
    assert kernel.is_running is True
    assert agent.initialized is True

    await kernel.shutdown()
    assert kernel.is_running is False
    assert agent.initialized is False


def test_registry_interaction():
    """Test: Tool Registry + Capability Registry"""
    tool_reg = ToolRegistry()
    cap_reg = CapabilityRegistry()

    assert isinstance(tool_reg, ToolRegistry)
    assert isinstance(cap_reg, CapabilityRegistry)
    # The registries themselves are simple dictionaries or structures.
    # Ensuring they instantiate correctly as part of the ecosystem.


def test_event_propagation_and_logging(caplog):
    """Test: Event System + Logging Framework"""
    from shared.contracts.event import EventSource, EventType, RuntimeEvent

    from app.core.events.bus import EventBus

    bus = EventBus()
    event_received = False

    async def mock_handler(event: RuntimeEvent):
        nonlocal event_received
        event_received = True
        logging.getLogger("test_logger").info(f"Received event: {event.event_type}")

    bus.subscribe(EventType.WORKFLOW_CREATED, mock_handler)

    event = RuntimeEvent(
        workflow_id=uuid4(),
        event_type=EventType.WORKFLOW_CREATED,
        source_component=EventSource.RUNTIME_KERNEL,
        payload={"status": "testing"}
    )
    
    caplog.set_level(logging.INFO)
    
    # We must run the async publish
    asyncio.run(bus.publish(event))

    assert event_received is True
    assert "Received event: EventType.WORKFLOW_CREATED" in caplog.text


def test_shared_exceptions():
    """Test: Shared Exceptions Framework"""

    class TestException(AetherPhoenixException):
        pass

    try:
        raise TestException("Test error occurred", details={"code": 500})
    except TestException as e:
        assert str(e) == "Test error occurred"
        assert e.details["code"] == 500


def test_workflow_engine_and_permissions(workflow_state):
    """Test: Workflow Engine + Permission Manager"""
    engine = WorkflowEngine(workflow_state)

    # Test Workflow state transitions
    engine.start()
    assert workflow_state.metadata.status == "RUNNING"

    # Enqueue a task
    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_state.metadata.workflow_id,
        task_name="TestTask",
        description="A test task",
        required_tool="None",
        category=TaskCategory.OTHER,
        expected_output="Done",
        priority=TaskPriority.HIGH,
    )
    engine.enqueue(task)
    assert task.status == TaskStatus.WAITING
    assert task.task_id in workflow_state.execution_queue

    # Dequeue and start task
    popped_task = engine.dequeue()
    assert popped_task is not None
    assert popped_task.task_id == task.task_id

    engine.update_task_status(popped_task.task_id, TaskStatus.RUNNING)
    assert popped_task.task_id in workflow_state.running_tasks

    # Test Mock Permission Manager integration
    permission_manager = MockPermissionManager()
    from shared.contracts.permission import RiskLevel

    perm_req = PermissionRequest(
        workflow_id=workflow_state.metadata.workflow_id,
        permission_type=PermissionType.FILE_SYSTEM,
        reason="Testing permission validation",
        risk_level=RiskLevel.LOW,
    )
    workflow_state.permissions.append(perm_req)

    approved_req = permission_manager.request_permission(perm_req)
    assert approved_req.status == PermissionStatus.GRANTED

    engine.complete()
    assert workflow_state.metadata.status == "COMPLETED"
