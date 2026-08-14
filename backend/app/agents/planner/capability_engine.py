import logging
from typing import List, Optional, Tuple

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

    def discover_capabilities(
        self, tasks: List[Task], unavailable_tools: Optional[List[str]] = None
    ) -> Tuple[List[Task], List[str]]:
        """
        Iterates over tasks, finds a matching capability by category,
        and assigns the correct Tool to each Task based on the Capability Registry.
        Returns the modified tasks and a list of unsupported capability categories.
        """
        unsupported = []

        for task in tasks:
            # Skip if tool is already assigned explicitly and not empty, unless it is unavailable
            if task.required_tool and task.required_tool.strip() != "":
                if unavailable_tools and task.required_tool in unavailable_tools:
                    task.required_tool = ""
                else:
                    continue

            if task.assigned_agent == "System":
                continue

            # Find matching capabilities
            caps = self.registry.list_by_category(task.category)

            if not caps:
                unsupported.append(task.category.value)
                continue

            enabled_caps = [c for c in caps if c.enabled]
            if unavailable_tools:
                enabled_caps = [
                    c
                    for c in enabled_caps
                    if not any(t in unavailable_tools for t in (c.required_tools or [c.name]))
                ]

            if not enabled_caps:
                unsupported.append(task.category.value)
                continue

            selected_cap = enabled_caps[0]
            if selected_cap.required_tools:
                task.required_tool = selected_cap.required_tools[0]
            else:
                task.required_tool = selected_cap.name

        return tasks, list(set(unsupported))
