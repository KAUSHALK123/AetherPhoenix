from typing import Dict, List, Optional

from shared.contracts.capability import Capability
from shared.contracts.task import TaskCategory


class CapabilityRegistry:
    """
    Manages the lifecycle and lookup of available capabilities.
    Provides validation to ensure the Planner only assigns supported tasks.
    """

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        """Registers a new capability. Raises ValueError if name already exists."""
        if capability.name in self._capabilities:
            raise ValueError(
                f"Capability with name '{capability.name}' is already registered."
            )

        self._capabilities[capability.name] = capability

    def unregister(self, capability_name: str) -> None:
        """Removes a capability from the registry."""
        if capability_name in self._capabilities:
            del self._capabilities[capability_name]

    def get(self, capability_name: str) -> Optional[Capability]:
        """Retrieves a capability by its unique name."""
        return self._capabilities.get(capability_name)

    def list_all(self) -> List[Capability]:
        """Returns all registered capabilities."""
        return list(self._capabilities.values())

    def list_by_category(self, category: TaskCategory) -> List[Capability]:
        """Returns all registered capabilities matching a specific category."""
        return [cap for cap in self._capabilities.values() if cap.category == category]

    def validate_capabilities(self, requested_capabilities: List[str]) -> bool:
        """
        Validates if a set of capability names are registered and enabled.
        Returns True if ALL capabilities are supported, False otherwise.
        """
        for req in requested_capabilities:
            cap = self.get(req)
            if not cap or not cap.enabled:
                return False
        return True
