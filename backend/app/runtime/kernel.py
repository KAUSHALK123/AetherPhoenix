from typing import Dict, Optional

from shared.contracts.workflow import SharedWorkflowState

from app.core.logging import get_logger
from app.runtime.context import RuntimeContext
from app.runtime.interfaces import BaseAgent

logger = get_logger(__name__)


class RuntimeKernel:
    """
    The central execution engine responsible for orchestrating all AI agents.
    Manages agent lifecycle, execution context, and shared state.
    """

    def __init__(self):
        self.is_running: bool = False
        self.registered_agents: Dict[str, BaseAgent] = {}
        self.active_contexts: Dict[str, RuntimeContext] = {}

    async def initialize(self) -> None:
        """Starts the Runtime Kernel and initializes all registered agents."""
        logger.info("Initializing Runtime Kernel...")
        self.is_running = True
        for name, agent in self.registered_agents.items():
            logger.info(f"Initializing agent: {name}")
            await agent.initialize()
        logger.info("Runtime Kernel initialized.")

    async def shutdown(self) -> None:
        """Shuts down the Runtime Kernel and all registered agents."""
        logger.info("Shutting down Runtime Kernel...")
        self.is_running = False

        # Shutdown all agents
        for name, agent in self.registered_agents.items():
            logger.info(f"Shutting down agent: {name}")
            try:
                await agent.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down agent {name}: {e}")

        self.active_contexts.clear()
        logger.info("Runtime Kernel shut down.")

    def register_agent(self, agent: BaseAgent) -> None:
        """
        Registers an agent with the kernel.

        Args:
            agent (BaseAgent): The agent instance to register.

        Raises:
            ValueError: If an agent with the same name is already registered.
        """
        name = agent.registration.name
        if name in self.registered_agents:
            raise ValueError(f"Agent with name '{name}' is already registered.")

        self.registered_agents[name] = agent
        logger.info(f"Registered agent: {name} (v{agent.registration.version})")

    def create_context(
        self, session_id: str, shared_state: Optional[SharedWorkflowState] = None
    ) -> RuntimeContext:
        """
        Creates and stores a new RuntimeContext for a given session.

        Args:
            session_id: Identifier for the user session.
            shared_state: Optional shared state to inject.

        Returns:
            The newly created RuntimeContext.
        """
        context = RuntimeContext(session_id=session_id, shared_state=shared_state)
        self.active_contexts[context.context_id] = context
        logger.info(
            f"Created RuntimeContext {context.context_id} for session {session_id}"
        )
        return context

    def get_context(self, context_id: str) -> Optional[RuntimeContext]:
        """Retrieves an active context by ID."""
        return self.active_contexts.get(context_id)

    def remove_context(self, context_id: str) -> None:
        """Removes an active context and cleans it up."""
        if context_id in self.active_contexts:
            context = self.active_contexts.pop(context_id)
            context.mark_complete()
            logger.info(f"Removed RuntimeContext {context_id}")
