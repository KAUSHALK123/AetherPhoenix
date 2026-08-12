import ipaddress
import time
from typing import Any, Optional
from urllib.parse import urlparse

import bs4
import httpx

from app.core.logging import get_logger
from app.tools.web_scraping.contracts import (
    ExtractionRule,
    ScrapeRequest,
    ScrapeResult,
    SourceMetadata,
)

logger = get_logger(__name__)

# Private/restricted IP ranges and local hostnames to prevent SSRF / private scraping
RESTRICTED_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "local"}


class WebScraper:
    """
    Controlled Web Scraper engine for extracting structured data from
    publicly accessible web pages.
    """

    def validate_url(self, url: str) -> str:
        """
        Validates target URL format, scheme, and ensures it does not point to
        a private or restricted local network address.
        """
        if not url or not isinstance(url, str):
            raise ValueError("Target URL must be a non-empty string.")

        parsed = urlparse(url.strip())
        if not parsed.scheme or parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme '{parsed.scheme}'. "
                "Only 'http' and 'https' are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: missing hostname.")

        hostname_lower = hostname.lower()
        if hostname_lower in RESTRICTED_HOSTNAMES or hostname_lower.endswith(".local"):
            raise ValueError(
                f"Access restricted: Scraping private or local hostname '{hostname}' "
                "is not permitted."
            )

        try:
            ip_obj = ipaddress.ip_address(hostname_lower)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_reserved
                or ip_obj.is_link_local
            ):
                raise ValueError(
                    f"Access restricted: Scraping private IP address '{hostname}' "
                    "is not permitted."
                )
        except ValueError as err:
            if "Scraping private" in str(err):
                raise err

        return url.strip()

    async def scrape(self, request: ScrapeRequest) -> ScrapeResult:
        """
        Executes a full web scraping operation: validating URL, retrieving page content,
        parsing HTML, and extracting requested structured fields.
        """
        start_time = time.time()
        logger.info(f"Starting web scrape for URL: {request.url}")

        # 1. URL Validation
        try:
            valid_url = self.validate_url(request.url)
        except ValueError as e:
            logger.warning(f"URL validation failed for '{request.url}': {str(e)}")
            return ScrapeResult(
                url=request.url,
                success=False,
                error_message=f"URL Validation Error: {str(e)}",
                source_metadata=SourceMetadata(url=request.url),
            )

        # 2. Page Retrieval
        headers = {"User-Agent": request.user_agent}
        status_code = None
        content_type = None

        try:
            async with httpx.AsyncClient(
                timeout=request.timeout_seconds, follow_redirects=True
            ) as client:
                response = await client.get(valid_url, headers=headers)
                status_code = response.status_code
                content_type = response.headers.get("Content-Type", "")
                response_time_ms = (time.time() - start_time) * 1000

                logger.info(
                    f"Fetched '{valid_url}' - Status: {status_code}, "
                    f"Time: {response_time_ms:.1f}ms"
                )

                if response.is_error:
                    logger.error(
                        f"HTTP status code {status_code} fetching '{valid_url}'"
                    )
                    return ScrapeResult(
                        url=valid_url,
                        success=False,
                        error_message=(
                            f"HTTP Request Failed with status code {status_code}"
                        ),
                        source_metadata=SourceMetadata(
                            url=valid_url,
                            status_code=status_code,
                            content_type=content_type,
                            response_time_ms=response_time_ms,
                        ),
                    )

                html_content = response.text

        except httpx.TimeoutException:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Network timeout fetching '{valid_url}'")
            return ScrapeResult(
                url=valid_url,
                success=False,
                error_message=(
                    f"Network Timeout after {request.timeout_seconds} seconds"
                ),
                source_metadata=SourceMetadata(
                    url=valid_url,
                    response_time_ms=response_time_ms,
                ),
            )
        except httpx.RequestError as exc:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Network failure fetching '{valid_url}': {str(exc)}")
            return ScrapeResult(
                url=valid_url,
                success=False,
                error_message=f"Network Connection Failure: {str(exc)}",
                source_metadata=SourceMetadata(
                    url=valid_url,
                    response_time_ms=response_time_ms,
                ),
            )
        except Exception as exc:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Unexpected error fetching '{valid_url}': {str(exc)}")
            return ScrapeResult(
                url=valid_url,
                success=False,
                error_message=f"Page Retrieval Error: {str(exc)}",
                source_metadata=SourceMetadata(
                    url=valid_url,
                    response_time_ms=response_time_ms,
                ),
            )

        # 3. HTML Parsing & Extraction
        try:
            soup = bs4.BeautifulSoup(html_content, "html.parser")
            page_title = (
                soup.title.string.strip()
                if soup.title and soup.title.string
                else None
            )

            extracted_data: dict[str, Any] = {}

            if request.parse_metadata:
                metadata = {
                    "title": page_title,
                    "description": self._extract_meta_content(soup, "description"),
                    "keywords": self._extract_meta_content(soup, "keywords"),
                    "og_title": self._extract_meta_property(soup, "og:title"),
                    "canonical": self._extract_canonical(soup),
                }
                extracted_data["metadata"] = {
                    k: v for k, v in metadata.items() if v is not None
                }

            if request.extraction_rules:
                for rule in request.extraction_rules:
                    extracted_val = self._apply_extraction_rule(soup, rule)
                    extracted_data[rule.field_name] = extracted_val

            source_meta = SourceMetadata(
                url=valid_url,
                status_code=status_code,
                content_type=content_type,
                response_time_ms=response_time_ms,
                page_title=page_title,
            )

            logger.info(
                f"Successfully scraped '{valid_url}' - "
                f"Extracted {len(extracted_data)} fields/sections"
            )
            return ScrapeResult(
                url=valid_url,
                success=True,
                extracted_data=extracted_data,
                source_metadata=source_meta,
            )

        except Exception as exc:
            logger.error(f"Failed to parse HTML from '{valid_url}': {str(exc)}")
            return ScrapeResult(
                url=valid_url,
                success=False,
                error_message=f"HTML Parsing Error: {str(exc)}",
                source_metadata=SourceMetadata(
                    url=valid_url,
                    status_code=status_code,
                    content_type=content_type,
                    response_time_ms=response_time_ms,
                ),
            )

    def _apply_extraction_rule(self, soup: bs4.BeautifulSoup, rule: ExtractionRule):
        """Applies a single CSS extraction rule to the parsed HTML soup."""
        try:
            if rule.is_list:
                elements = soup.select(rule.selector)
                if not elements:
                    return rule.default_value if rule.default_value is not None else []
                results = []
                for el in elements:
                    val = self._extract_element_value(el, rule.attribute)
                    if val is not None:
                        results.append(val)
                return results
            else:
                element = soup.select_one(rule.selector)
                if not element:
                    return rule.default_value
                return self._extract_element_value(element, rule.attribute)
        except Exception as e:
            logger.warning(
                f"Error applying rule '{rule.field_name}' "
                f"with selector '{rule.selector}': {str(e)}"
            )
            return rule.default_value

    def _extract_element_value(
        self, element: bs4.Tag, attribute: Optional[str]
    ) -> Optional[str]:
        """Extracts text or an attribute value from a BeautifulSoup tag element."""
        if attribute and attribute.strip():
            attr_name = attribute.strip().lower()
            if attr_name == "text":
                return element.get_text(strip=True)
            val = element.get(attr_name)
            if isinstance(val, list):
                return " ".join(val)
            return val.strip() if val else None
        else:
            return element.get_text(strip=True)

    def _extract_meta_content(
        self, soup: bs4.BeautifulSoup, meta_name: str
    ) -> Optional[str]:
        tag = soup.find("meta", attrs={"name": meta_name}) or soup.find(
            "meta", attrs={"property": meta_name}
        )
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
        return None

    def _extract_meta_property(
        self, soup: bs4.BeautifulSoup, prop: str
    ) -> Optional[str]:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
        return None

    def _extract_canonical(self, soup: bs4.BeautifulSoup) -> Optional[str]:
        tag = soup.find("link", attrs={"rel": "canonical"})
        if tag and tag.get("href"):
            return str(tag["href"]).strip()
        return None
