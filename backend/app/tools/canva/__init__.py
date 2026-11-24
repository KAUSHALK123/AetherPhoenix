"""
Canva Automation Tool Package
Provides live Canva automation via Member 2's browser runtime and CanvaSkills layer.
"""

from typing import Any, List, Optional

from shared.contracts.capability import Capability
from shared.contracts.permission import PermissionType
from shared.contracts.task import TaskCategory
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.engine.registry import CapabilityRegistry
from app.tools.canva.adapter import CanvaToolAdapter
from app.tools.canva.controller import CanvaBrowserController
from app.tools.canva.skill_adapter import CanvaSkillAdapter
from app.tools.canva.skills import CRITICAL_SKILLS, CanvaSkills
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

# Contract Metadata for Canva Skills
CANVA_SKILL_NAMES = [
    "canva_skill_adapter",
    "canva_skill_open",
    "canva_skill_create_design",
    "canva_skill_pick_template",
    "canva_skill_edit_text",
    "canva_skill_add_slide",
    "canva_skill_upload_image",
    "canva_skill_apply_brand_colors",
    "canva_skill_export",
    "canva_skill_publish",
    "canva_skill_share",
    "canva_skill_purchase",
]


def register_canva_tool(
    registry: ToolRegistry,
    cap_registry: Optional[CapabilityRegistry] = None,
    worker_agent: Optional[Any] = None,
    permission_manager: Optional[Any] = None,
) -> Tool:
    """Registers Canva tool and capability into the system registries."""
    if not registry.get("canva_tool"):
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
        try:
            cap_registry.register(canva_cap)
        except Exception:
            pass

    if worker_agent is not None:
        adapter = CanvaToolAdapter(permission_manager=permission_manager)
        worker_agent.register_adapter("canva_tool", adapter)
        worker_agent.register_adapter(
            "app.tools.canva.adapter.CanvaToolAdapter", adapter
        )

    return canva_tool_metadata


def register_canva_skills(
    registry: ToolRegistry,
    cap_registry: Optional[CapabilityRegistry] = None,
    worker_agent: Optional[Any] = None,
    permission_manager: Optional[Any] = None,
) -> List[Tool]:
    """
    Registers the Canva skills layer tools into the system ToolRegistry.
    Allows planner and decomposer to route directly to verified Canva skills.
    """
    registered_tools = []
    skill_adapter = None
    if worker_agent is not None:
        skill_adapter = CanvaSkillAdapter(permission_manager=permission_manager)

    for skill_name in CANVA_SKILL_NAMES:
        tool_meta = Tool(
            name=skill_name,
            version="1.0.0",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="app.tools.canva.skill_adapter.CanvaSkillAdapter",
            dependencies=["playwright"],
            required_permissions=[
                PermissionType.BROWSER_ACCESS.value,
                PermissionType.INTERNET.value,
            ],
        )
        if not registry.get(skill_name):
            registry.register(tool_meta)
            registered_tools.append(tool_meta)

        if worker_agent is not None and skill_adapter is not None:
            worker_agent.register_adapter(skill_name, skill_adapter)

    if worker_agent is not None and skill_adapter is not None:
        worker_agent.register_adapter(
            "app.tools.canva.skill_adapter.CanvaSkillAdapter", skill_adapter
        )

    if cap_registry is not None:
        skills_cap = Capability(
            name="canva_skills",
            description="High-level verified Canva skills for creating presentations, applying templates, and exporting designs",
            category=TaskCategory.BROWSER,
            required_tools=["canva_skill_adapter"],
            required_permissions=[
                PermissionType.BROWSER_ACCESS.value,
                PermissionType.INTERNET.value,
            ],
        )
        try:
            cap_registry.register(skills_cap)
        except Exception:
            pass

    return registered_tools


__all__ = [
    "CanvaBrowserController",
    "CanvaToolAdapter",
    "CanvaSkills",
    "CanvaSkillAdapter",
    "CRITICAL_SKILLS",
    "CANVA_SKILL_NAMES",
    "canva_tool_metadata",
    "register_canva_tool",
    "register_canva_skills",
]
