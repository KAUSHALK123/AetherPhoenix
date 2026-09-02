from shared.contracts.tool import Tool, ToolHealth, ToolState

try:
    from app.tools.ppt.adapter import PPTToolAdapter
    from app.tools.ppt.generator import PPTGenerator
except ImportError:
    PPTGenerator = None
    PPTToolAdapter = None

from app.tools.registry import ToolRegistry

# Tool Contract Metadata for Registration
ppt_tool_metadata = Tool(
    name="ppt_tool",
    version="1.0.0",
    status=ToolState.READY,
    health=ToolHealth.HEALTHY,
    adapter="app.tools.ppt.adapter.PPTToolAdapter",
    dependencies=["python-pptx"],
    required_permissions=["FILE_SYSTEM"],
)


def register_ppt_tool(registry: ToolRegistry) -> Tool:
    """Registers the PPT tool contract into ToolRegistry."""
    registry.register(ppt_tool_metadata)
    return ppt_tool_metadata


__all__ = [
    "PPTGenerator",
    "PPTToolAdapter",
    "ppt_tool_metadata",
    "register_ppt_tool",
]
