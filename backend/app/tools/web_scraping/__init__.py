from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.tools.web_scraping.adapter import WebScrapingAdapter
from app.tools.web_scraping.contracts import (
    ExtractionRule,
    ScrapeRequest,
    ScrapeResult,
    SourceMetadata,
)
from app.tools.web_scraping.scraper import WebScraper


def register_web_scraping_tool(registry, worker_agent=None) -> Tool:
    """
    Registers the Web Scraping tool with the ToolRegistry and registers its adapter
    with the WorkerAgent.

    Args:
        registry: The ToolRegistry instance.
        worker_agent: Optional WorkerAgent instance.

    Returns:
        Tool: The registered Tool contract instance.
    """
    tool = Tool(
        name="web_scraping",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="web_scraping_adapter",
        dependencies=["httpx", "beautifulsoup4"],
        required_permissions=["network_access"],
    )
    registry.register(tool)

    if worker_agent is not None:
        adapter = WebScrapingAdapter()
        worker_agent.register_adapter("web_scraping_adapter", adapter)

    return tool


__all__ = [
    "WebScraper",
    "WebScrapingAdapter",
    "ExtractionRule",
    "ScrapeRequest",
    "SourceMetadata",
    "ScrapeResult",
    "register_web_scraping_tool",
]
