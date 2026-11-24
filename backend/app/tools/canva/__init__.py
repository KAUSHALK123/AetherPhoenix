"""
Canva Automation Tool Package
Provides live Canva automation via Member 2's browser runtime.
"""

from typing import Any, Optional

from shared.contracts.capability import Capability
from shared.contracts.permission import PermissionType
from shared.contracts.task import TaskCategory
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.engine.registry import CapabilityRegistry
from app.tools.canva.adapter import CanvaToolAdapter
from app.tools.canva.controller import CanvaBrowserController
from app.tools.registry import ToolRegistry

# Contract Metadata for Canva Tool
canva_tool_metadata = Tool(
    name="canva_tool",
    version="1.0.0",
    status=ToolState.READY,
    health=ToolHealth.HEALTHY,
    adapter="app.tools.canva.adapter.CanvaToolAdapter",
    dependencies=["playwright"],
    required_permissions=[
        PermissionType.BROWSER_ACCESS.value,
        PermissionType.INTERNET.value,
    ],
)


def register_canva_tool(
    registry: ToolRegistry,
    cap_registry: Optional[CapabilityRegistry] = None,
    worker_agent: Optional[Any] = None,
    permission_manager: Optional[Any] = None,
) -> Tool:
    """Registers Canva tool and capability into the system registries."""
    registry.register(canva_tool_metadata)

    if cap_registry is not None:
        canva_cap = Capability(
            name="canva_design",
            description="Automates natural-language Canva design creation, editing, templates, and export via live browser runtime",
            category=TaskCategory.BROWSER,
            required_tools=["canva_tool"],
            required_permissions=[
                PermissionType.BROWSER_ACCESS.value,
                PermissionType.INTERNET.value,
            ],
        )
        cap_registry.register(canva_cap)

    if worker_agent is not None:
        adapter = CanvaToolAdapter(permission_manager=permission_manager)
        worker_agent.register_adapter("canva_tool", adapter)
        worker_agent.register_adapter(
            "app.tools.canva.adapter.CanvaToolAdapter", adapter
        )

    return canva_tool_metadata


__all__ = [
    "CanvaBrowserController",
    "CanvaToolAdapter",
    "canva_tool_metadata",
    "register_canva_tool",
]
