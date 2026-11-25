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
        # Using standard Mozilla/5.0 ensures DuckDuckGo returns clean HTML without anti-bot redirection
        self.user_agent = "Mozilla/5.0"
        self.fallback_user_agent = (
            "AetherPhoenixResearch/1.0 (https://github.com/aetherphoenix; contact@example.com)"
        )

    async def search(self, query: str, max_results: int = 5) -> List[SourceMetadata]:
        """Performs search and parses source metadata, with automated fallback if blocked."""
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
                if response.status_code == 200:
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

            if sources:
                logger.info("DuckDuckGo search completed", query=query, count=len(sources))
                return sources[:max_results]

        except Exception as exc:
            logger.warning(
                "Primary DuckDuckGo web search encountered issue; trying Wikipedia fallback",
                query=query,
                error=str(exc),
            )

        # Fallback search engine: Wikipedia srsearch API
        try:
            wiki_sources = await self._search_wikipedia(query, max_results=max_results)
            if wiki_sources:
                logger.info(
                    "Wikipedia fallback search completed", query=query, count=len(wiki_sources)
                )
                return wiki_sources
        except Exception as wiki_exc:
            logger.warning(
                "Wikipedia fallback search failed", query=query, error=str(wiki_exc)
            )

        return sources[:max_results]

    async def _search_wikipedia(
        self, query: str, max_results: int = 5
    ) -> List[SourceMetadata]:
        """Fallback search using Wikipedia's search API."""
        api_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": max_results,
        }
        headers = {"User-Agent": self.fallback_user_agent}

        sources: List[SourceMetadata] = []
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, follow_redirects=True
        ) as client:
            resp = await client.get(api_url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            search_items = data.get("query", {}).get("search", [])

            for item in search_items[:max_results]:
                title = item.get("title", "")
                snippet_html = item.get("snippet", "")
                snippet = BeautifulSoup(snippet_html, "html.parser").get_text(strip=True)
                page_slug = urllib.parse.quote(title.replace(" ", "_"))
                target_url = f"https://en.wikipedia.org/wiki/{page_slug}"

                sources.append(
                    SourceMetadata(
                        url=target_url,
                        title=title,
                        snippet=snippet,
                        domain="wikipedia.org",
                        status=SourceStatus.SUCCESS,
                    )
                )

        return sources


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
