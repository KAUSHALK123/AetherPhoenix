import logging
from typing import Any, Optional

from shared.contracts.capability import Capability
from shared.contracts.permission import PermissionType
from shared.contracts.task import TaskCategory
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.engine.registry import CapabilityRegistry
from app.tools.browser_extension.adapter import BrowserExtensionAdapter
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_browser_extension_capability(
    tool_registry: ToolRegistry,
    cap_registry: Optional[CapabilityRegistry] = None,
    worker_agent: Optional[Any] = None,
    permission_manager: Optional[Any] = None,
):
    """Registers the browser_extension tool and capability into the system registries."""
    browser_ext_tool = Tool(
        name="browser_extension",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="browser_extension_adapter",
        dependencies=[],
        required_permissions=[
            PermissionType.BROWSER_ACCESS.value,
            PermissionType.INTERNET.value,
        ],
    )
    tool_registry.register(browser_ext_tool)

    if cap_registry is not None:
        browser_ext_cap = Capability(
            name="web_extension_automation",
            description="Controls user's visible browser via Chrome extension",
            category=TaskCategory.BROWSER,
            required_tools=["browser_extension"],
        )
        cap_registry.register(browser_ext_cap)

    if worker_agent is not None:
        adapter = BrowserExtensionAdapter(permission_manager=permission_manager)
        worker_agent.register_adapter("browser_extension_adapter", adapter)
        worker_agent.register_adapter(
            "app.tools.browser_extension.adapter.BrowserExtensionAdapter", adapter
        )
