from typing import Dict, List, Optional

from shared.contracts.tool import Tool, ToolHealth, ToolState


class ToolRegistry:
    """
    Manages the lifecycle, health, and lookup of concrete tools.
    Provides the Worker Agent with discovering registered tools and adapters.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Registers a new tool. Raises ValueError if name already exists."""
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")

        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """Removes a tool from the registry."""
        if tool_name in self._tools:
            del self._tools[tool_name]

    def get(self, tool_name: str) -> Optional[Tool]:
        """Retrieves a tool by its unique name."""
        return self._tools.get(tool_name)

    def list_all(self) -> List[Tool]:
        """Returns all registered tools."""
        return list(self._tools.values())

    def list_by_state(self, state: ToolState) -> List[Tool]:
        """Returns all registered tools matching a specific lifecycle state."""
        return [tool for tool in self._tools.values() if tool.status == state]

    def update_state(self, tool_name: str, state: ToolState) -> None:
        """Updates the state of a specific tool."""
        tool = self.get(tool_name)
        if tool:
            tool.status = state

    def update_health(self, tool_name: str, health: ToolHealth) -> None:
        """Updates the health of a specific tool."""
        tool = self.get(tool_name)
        if tool:
            tool.health = health
