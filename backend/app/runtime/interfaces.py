from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentRegistration(BaseModel):
    """Metadata required to register an agent with the Runtime Kernel."""

    name: str = Field(..., description="Unique name of the agent")
    version: str = Field(..., description="Version of the agent")
    description: str = Field(
        default="", description="Description of the agent's capabilities"
    )


class BaseAgent(ABC):
    """Core interface that all agents must implement."""

    @property
    @abstractmethod
    def registration(self) -> AgentRegistration:
        """Returns the registration metadata for this agent."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Lifecycle hook: Called when the agent is registered
        and initialized by the kernel."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Lifecycle hook: Called when the kernel shuts down
        or the agent is unregistered."""
        pass

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Main execution loop for the agent."""
        pass
