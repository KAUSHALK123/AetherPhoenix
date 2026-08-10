import logging
from typing import List, Tuple

from shared.contracts.task import Task

from app.engine.registry import CapabilityRegistry

logger = logging.getLogger(__name__)


class CapabilityDiscoveryEngine:
    """
    Engine responsible for discovering required capabilities and assigning
    the correct Tool to each Task based on the Capability Registry.
    """

    def __init__(self, registry: CapabilityRegistry = None):
        self.registry = registry or CapabilityRegistry()

    def discover_capabilities(self, tasks: List[Task]) -> Tuple[List[Task], List[str]]:
        """
        Iterates over tasks, finds a matching capability by category, 
        and assigns the required tool.
        Returns the modified tasks and a list of unsupported capability categories.
        """
        unsupported = []

        for task in tasks:
            # Skip if tool is already assigned explicitly and not empty
            if task.required_tool and task.required_tool.strip() != "":
                continue

            if task.assigned_agent == "System":
                continue

            # Find matching capabilities
            caps = self.registry.list_by_category(task.category)

            if not caps:
                unsupported.append(task.category.value)
                continue

            enabled_caps = [c for c in caps if c.enabled]
            if not enabled_caps:
                unsupported.append(task.category.value)
                continue

            selected_cap = enabled_caps[0]
            if selected_cap.required_tools:
                task.required_tool = selected_cap.required_tools[0]
            else:
                task.required_tool = selected_cap.name

        return tasks, list(set(unsupported))
