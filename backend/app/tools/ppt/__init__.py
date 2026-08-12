from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.tools.ppt.generator import PPTGenerator

# Tool Contract Metadata for Registration
ppt_tool_metadata = Tool(
    name="ppt_tool",
    version="1.0.0",
    status=ToolState.READY,
    health=ToolHealth.HEALTHY,
    adapter="app.tools.ppt.generator.PPTGenerator",
    dependencies=["python-pptx"],
    required_permissions=["FILE_SYSTEM"],
)

__all__ = [
    "PPTGenerator",
    "ppt_tool_metadata",
]
