import urllib.parse
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.tools.web_research.interface import SearchEngineInterface
from app.tools.web_research.schemas import SourceMetadata, SourceStatus

logger = get_logger(__name__)


def extract_domain(url: str) -> str:
    """Safely extracts domain name from a URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc or parsed.path.split("/")[0]
    except Exception:
        return ""


def clean_ddg_url(raw_url: str) -> str:
    """Parses DDG redirection links if present."""
    if "duckduckgo.com/l/?" in raw_url or "duckduckgo.com/r/?" in raw_url:
        parsed = urllib.parse.urlparse(raw_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        if "uddg" in query_params:
            return query_params["uddg"][0]
        if "u" in query_params:
            return query_params["u"][0]
    return raw_url


class DuckDuckGoSearchEngine(SearchEngineInterface):
    """
    Search engine implementation using DuckDuckGo HTML endpoint.
    Retrieves web sources without requiring API keys.
    """

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def search(self, query: str, max_results: int = 5) -> List[SourceMetadata]:
        """Performs search and parses source metadata."""
        if not query or not query.strip():
            logger.warning("Empty search query provided to DuckDuckGoSearchEngine")
            return []

        logger.info("Executing web search query", query=query, max_results=max_results)

        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": self.user_agent}
        data = {"q": query}

        sources: List[SourceMetadata] = []

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, follow_redirects=True
            ) as client:
                response = await client.post(url, data=data, headers=headers)
                response.raise_for_status()
                html = response.text

            soup = BeautifulSoup(html, "html.parser")
            results = soup.select(".result")

            for result in results[:max_results]:
                title_tag = result.select_one(".result__title a")
                snippet_tag = result.select_one(".result__snippet")

                if not title_tag:
                    continue

                raw_href = title_tag.get("href", "")
                target_url = clean_ddg_url(raw_href)
                title_text = title_tag.get_text(strip=True)
                snippet_text = snippet_tag.get_text(strip=True) if snippet_tag else ""
                domain_name = extract_domain(target_url)

                if target_url and target_url.startswith("http"):
                    sources.append(
                        SourceMetadata(
                            url=target_url,
                            title=title_text,
                            snippet=snippet_text,
                            domain=domain_name,
                            status=SourceStatus.SUCCESS,
                        )
                    )

            logger.info("Search query completed", query=query, count=len(sources))
            return sources

        except Exception as exc:
            logger.error(
                "DuckDuckGo web search failed",
                query=query,
                error=str(exc),
                exc_info=True,
            )
            raise RuntimeError(f"Web search engine failure: {str(exc)}") from exc


class MockSearchEngine(SearchEngineInterface):
    """Mock search engine implementation for testing and offline environments."""

    def __init__(
        self,
        mock_results: Optional[List[SourceMetadata]] = None,
        should_fail: bool = False,
        error_message: str = "Mock search engine failure",
    ):
        self.mock_results = mock_results or []
        self.should_fail = should_fail
        self.error_message = error_message

    async def search(self, query: str, max_results: int = 5) -> List[SourceMetadata]:
        if self.should_fail:
            logger.error("Mock search engine configured to fail", query=query)
            raise RuntimeError(self.error_message)

        logger.info(
            "Executing mock search", query=query, available=len(self.mock_results)
        )
        if not self.mock_results:
            return []

        filtered = [
            s
            for s in self.mock_results
            if query.lower() in s.title.lower()
            or query.lower() in s.snippet.lower()
            or query.lower() in s.url.lower()
        ]
        results = filtered if filtered else self.mock_results
        return results[:max_results]
