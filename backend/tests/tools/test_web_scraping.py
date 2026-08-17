from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.tools.web_scraping.contracts import (
    ExtractionRule,
    ScrapeRequest,
)
from app.tools.web_scraping.scraper import WebScraper


@pytest.fixture
def scraper():
    return WebScraper()


def test_url_validation_valid(scraper):
    assert scraper.validate_url("http://example.com") == "http://example.com"
    assert (
        scraper.validate_url("https://example.com/page?query=1")
        == "https://example.com/page?query=1"
    )


def test_url_validation_invalid_scheme(scraper):
    with pytest.raises(ValueError, match="Invalid URL scheme"):
        scraper.validate_url("ftp://example.com")

    with pytest.raises(ValueError, match="Invalid URL scheme"):
        scraper.validate_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="Target URL must be a non-empty string"):
        scraper.validate_url("")


def test_url_validation_restricted_addresses(scraper):
    with pytest.raises(ValueError, match="Access restricted"):
        scraper.validate_url("http://localhost:8000")

    with pytest.raises(ValueError, match="Access restricted"):
        scraper.validate_url("http://127.0.0.1/admin")

    with pytest.raises(ValueError, match="Access restricted"):
        scraper.validate_url("http://192.168.1.1/router")

    with pytest.raises(ValueError, match="Access restricted"):
        scraper.validate_url("http://10.0.0.5/api")


@pytest.mark.asyncio
async def test_scrape_valid_webpage(scraper):
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sample News Article</title>
        <meta name="description" content="This is a test article description">
    </head>
    <body>
        <h1 class="heading">Tech Breakthrough 2026</h1>
        <div class="author">By Jane Doe</div>
        <div class="content">
            <p>Artificial Intelligence continues to advance rapidly.</p>
        </div>
        <ul class="tags">
            <li>AI</li>
            <li>Tech</li>
            <li>Future</li>
        </ul>
        <a href="https://example.com/read-more" id="more-link">Read More</a>
    </body>
    </html>
    """

    rules = [
        ExtractionRule(field_name="title", selector="h1.heading"),
        ExtractionRule(field_name="author", selector="div.author"),
        ExtractionRule(field_name="tags", selector="ul.tags li", is_list=True),
        ExtractionRule(field_name="read_more", selector="#more-link", attribute="href"),
    ]

    request = ScrapeRequest(
        url="https://example.com/article",
        extraction_rules=rules,
        parse_metadata=True,
    )

    mock_response = httpx.Response(
        status_code=200,
        html=sample_html,
        headers={"Content-Type": "text/html"},
        request=httpx.Request("GET", "https://example.com/article"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await scraper.scrape(request)

    assert result.success is True
    assert result.url == "https://example.com/article"
    assert result.source_metadata is not None
    assert result.source_metadata.status_code == 200
    assert result.source_metadata.page_title == "Sample News Article"

    data = result.extracted_data
    assert data["title"] == "Tech Breakthrough 2026"
    assert data["author"] == "By Jane Doe"
    assert data["tags"] == ["AI", "Tech", "Future"]
    assert data["read_more"] == "https://example.com/read-more"
    assert data["metadata"]["description"] == "This is a test article description"


@pytest.mark.asyncio
async def test_scrape_missing_elements(scraper):
    sample_html = "<html><body><h1>Headline Only</h1></body></html>"
    rules = [
        ExtractionRule(field_name="title", selector="h1"),
        ExtractionRule(
            field_name="missing_field",
            selector=".nonexistent",
            default_value="N/A",
        ),
        ExtractionRule(
            field_name="missing_list",
            selector=".nonexistent-item",
            is_list=True,
        ),
    ]

    request = ScrapeRequest(
        url="https://example.com/page",
        extraction_rules=rules,
    )

    mock_response = httpx.Response(
        status_code=200,
        html=sample_html,
        request=httpx.Request("GET", "https://example.com/page"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await scraper.scrape(request)

    assert result.success is True
    assert result.extracted_data["title"] == "Headline Only"
    assert result.extracted_data["missing_field"] == "N/A"
    assert result.extracted_data["missing_list"] == []


@pytest.mark.asyncio
async def test_scrape_malformed_html(scraper):
    malformed_html = """
    <div><h1>Unclosed Header
    <p>Paragraph without closing tag
    <span>Broken inline element</div>
    <a href='/link'>Link Text</a>
    """
    rules = [
        ExtractionRule(field_name="header", selector="h1"),
        ExtractionRule(field_name="link", selector="a", attribute="href"),
    ]
    request = ScrapeRequest(
        url="https://example.com/malformed",
        extraction_rules=rules,
    )

    mock_response = httpx.Response(
        status_code=200,
        html=malformed_html,
        request=httpx.Request("GET", "https://example.com/malformed"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await scraper.scrape(request)

    assert result.success is True
    assert "Unclosed Header" in result.extracted_data["header"]
    assert result.extracted_data["link"] == "/link"


@pytest.mark.asyncio
async def test_scrape_network_timeout(scraper):
    request = ScrapeRequest(url="https://example.com/timeout", timeout_seconds=2.0)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Connection timed out")
        result = await scraper.scrape(request)

    assert result.success is False
    assert "Network Timeout" in result.error_message
    assert result.url == "https://example.com/timeout"


@pytest.mark.asyncio
async def test_scrape_http_error_404(scraper):
    request = ScrapeRequest(url="https://example.com/not-found")
    mock_response = httpx.Response(
        status_code=404,
        text="Not Found",
        request=httpx.Request("GET", "https://example.com/not-found"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await scraper.scrape(request)

    assert result.success is False
    assert "status code 404" in result.error_message
    assert result.source_metadata.status_code == 404
