from typing import Any

import pytest
from shared.contracts.workflow import SharedWorkflowState

from app.runtime.interfaces import AgentRegistration, BaseAgent
from app.runtime.kernel import RuntimeKernel


class MockAgent(BaseAgent):
    def __init__(self, name: str, version: str):
        self._registration = AgentRegistration(name=name, version=version)
        self.initialized = False
        self.shut_down = False

    @property
    def registration(self) -> AgentRegistration:
        return self._registration

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.shut_down = True

    async def execute(self, *args, **kwargs) -> Any:
        return "Executed"


@pytest.fixture
def kernel():
    return RuntimeKernel()


@pytest.mark.anyio
async def test_kernel_initialization(kernel):
    agent1 = MockAgent("Agent1", "1.0")
    kernel.register_agent(agent1)

    await kernel.initialize()

    assert kernel.is_running is True
    assert agent1.initialized is True


@pytest.mark.anyio
async def test_kernel_shutdown(kernel):
    agent1 = MockAgent("Agent1", "1.0")
    kernel.register_agent(agent1)

    await kernel.initialize()
    await kernel.shutdown()

    assert kernel.is_running is False
    assert agent1.shut_down is True


def test_agent_registration(kernel):
    agent1 = MockAgent("Agent1", "1.0")
    kernel.register_agent(agent1)
    assert "Agent1" in kernel.registered_agents

    with pytest.raises(ValueError):
        kernel.register_agent(agent1)


def test_context_creation(kernel):
    context = kernel.create_context("session-123")
    assert context.session_id == "session-123"
    assert context.is_active is True
    assert isinstance(context.shared_state, SharedWorkflowState)

    retrieved = kernel.get_context(context.context_id)
    assert retrieved is context

    kernel.remove_context(context.context_id)
    assert context.is_active is False
    assert kernel.get_context(context.context_id) is None
