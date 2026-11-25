"""Web Research capability module for Worker Agent."""

from shared.contracts.permission import PermissionType
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.tools.registry import ToolRegistry
from app.tools.web_research.adapter import WebResearchToolAdapter
from app.tools.web_research.extractor import ContentExtractor
from app.tools.web_research.interface import BaseResearchTool, SearchEngineInterface
from app.tools.web_research.schemas import (
    ExtractedPageContent,
    SourceMetadata,
    SourceStatus,
    StructuredResearchResult,
    WebResearchRequest,
)
from app.tools.web_research.search import DuckDuckGoSearchEngine, MockSearchEngine
from app.tools.web_research.tool import WebResearchTool


def register_web_research_tool(registry: ToolRegistry) -> Tool:
    """
    Registers the Web Research tool contracts with the ToolRegistry.
    Registers both 'web_research' and 'web_research_tool' aliases.
    """
    web_res_tool = Tool(
        name="web_research",
        description="Gathers, extracts, and packages structured research from web sources.",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.web_research.adapter.WebResearchToolAdapter",
        dependencies=["httpx", "beautifulsoup4"],
        required_permissions=[PermissionType.INTERNET.value],
    )
    registry.register(web_res_tool)

    web_res_tool_alias = Tool(
        name="web_research_tool",
        description="Gathers, extracts, and packages structured research from web sources.",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.web_research.adapter.WebResearchToolAdapter",
        dependencies=["httpx", "beautifulsoup4"],
        required_permissions=[PermissionType.INTERNET.value],
    )
    registry.register(web_res_tool_alias)

    return web_res_tool


__all__ = [
    "WebResearchTool",
    "WebResearchToolAdapter",
    "register_web_research_tool",
    "BaseResearchTool",
    "SearchEngineInterface",
    "DuckDuckGoSearchEngine",
    "MockSearchEngine",
    "ContentExtractor",
    "SourceStatus",
    "SourceMetadata",
    "ExtractedPageContent",
    "WebResearchRequest",
    "StructuredResearchResult",
]
