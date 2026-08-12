import time
import urllib.parse
from typing import Tuple

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.tools.web_research.schemas import ExtractedPageContent, SourceStatus

logger = get_logger(__name__)


class ContentExtractor:
    """
    Asynchronous web content extractor.
    Safely fetches and parses accessible HTML web pages.
    """

    def __init__(self, max_content_length: int = 10000):
        self.max_content_length = max_content_length
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    def is_valid_url(self, url: str) -> bool:
        """Validates basic URL structure."""
        if not url or not isinstance(url, str):
            return False
        try:
            parsed = urllib.parse.urlparse(url.strip())
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False

    def sanitize_html(self, html_text: str) -> Tuple[str, str]:
        """
        Parses HTML, removes scripts/styles/navigation tags,
        and extracts page title and readable body text.
        """
        soup = BeautifulSoup(html_text, "html.parser")

        # Remove irrelevant tags
        for element in soup(
            ["script", "style", "nav", "footer", "header", "iframe", "noscript"]
        ):
            element.decompose()

        # Title extraction
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Body text extraction
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = "\n".join(chunk for chunk in chunks if chunk)

        if len(clean_text) > self.max_content_length:
            clean_text = (
                clean_text[: self.max_content_length] + "\n...[Content Truncated]"
            )

        return title, clean_text

    async def extract_content(
        self, url: str, timeout_seconds: float = 10.0
    ) -> Tuple[ExtractedPageContent, float]:
        """
        Fetches web page from URL and extracts structured page content.
        Returns ExtractedPageContent and elapsed time in seconds.
        """
        start_time = time.perf_counter()

        if not self.is_valid_url(url):
            elapsed = time.perf_counter() - start_time
            logger.warning("Malformed URL provided for content extraction", url=url)
            return (
                ExtractedPageContent(
                    url=url,
                    title="",
                    content="",
                    status=SourceStatus.MALFORMED_URL,
                    error_message="Invalid URL structure or missing http/https scheme",
                ),
                elapsed,
            )

        headers = {"User-Agent": self.user_agent}

        try:
            async with httpx.AsyncClient(
                timeout=timeout_seconds, follow_redirects=True
            ) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in (404, 410, 403, 500, 502, 503):
                    elapsed = time.perf_counter() - start_time
                    logger.warning(
                        "Web source unavailable",
                        url=url,
                        status_code=response.status_code,
                    )
                    return (
                        ExtractedPageContent(
                            url=url,
                            title="",
                            content="",
                            status=SourceStatus.UNAVAILABLE,
                            error_message=f"HTTP status code {response.status_code}",
                        ),
                        elapsed,
                    )

                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()

                if (
                    "text/html" not in content_type
                    and "application/xhtml" not in content_type
                ):
                    elapsed = time.perf_counter() - start_time
                    logger.info(
                        "Non-HTML content type skipped",
                        url=url,
                        content_type=content_type,
                    )
                    return (
                        ExtractedPageContent(
                            url=url,
                            title="",
                            content=response.text[: self.max_content_length],
                            status=SourceStatus.SUCCESS,
                        ),
                        elapsed,
                    )

                title, clean_text = self.sanitize_html(response.text)
                elapsed = time.perf_counter() - start_time

                logger.info(
                    "Page content successfully extracted",
                    url=url,
                    content_length=len(clean_text),
                    elapsed=round(elapsed, 3),
                )

                return (
                    ExtractedPageContent(
                        url=url,
                        title=title,
                        content=clean_text,
                        status=SourceStatus.SUCCESS,
                    ),
                    elapsed,
                )

        except httpx.TimeoutException:
            elapsed = time.perf_counter() - start_time
            logger.warning(
                "Content extraction timed out", url=url, timeout=timeout_seconds
            )
            return (
                ExtractedPageContent(
                    url=url,
                    title="",
                    content="",
                    status=SourceStatus.UNAVAILABLE,
                    error_message=f"Request timed out after {timeout_seconds}s",
                ),
                elapsed,
            )

        except httpx.HTTPError as exc:
            elapsed = time.perf_counter() - start_time
            logger.warning(
                "HTTP error during content extraction", url=url, error=str(exc)
            )
            return (
                ExtractedPageContent(
                    url=url,
                    title="",
                    content="",
                    status=SourceStatus.FETCH_ERROR,
                    error_message=str(exc),
                ),
                elapsed,
            )

        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            logger.error(
                "Unexpected error during content extraction",
                url=url,
                error=str(exc),
                exc_info=True,
            )
            return (
                ExtractedPageContent(
                    url=url,
                    title="",
                    content="",
                    status=SourceStatus.FAILED,
                    error_message=str(exc),
                ),
                elapsed,
            )
