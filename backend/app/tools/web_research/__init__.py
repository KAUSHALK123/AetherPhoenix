"""Web Research capability module for Worker Agent."""

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

__all__ = [
    "WebResearchTool",
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
