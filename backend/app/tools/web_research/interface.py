from abc import ABC, abstractmethod
from typing import List

from app.tools.web_research.schemas import (
    SourceMetadata,
    StructuredResearchResult,
    WebResearchRequest,
)


class SearchEngineInterface(ABC):
    """Abstract interface for web search engines."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SourceMetadata]:
        """Performs a web search and returns candidate source metadata."""
        pass


class BaseResearchTool(ABC):
    """Abstract base class for web research tools."""

    @abstractmethod
    async def research(self, request: WebResearchRequest) -> StructuredResearchResult:
        """Executes research and returns structured normalized results."""
        pass
