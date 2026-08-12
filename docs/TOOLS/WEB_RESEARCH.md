# Web Research Capability

**Version:** 1.0  
**Category:** WEB_RESEARCH  
**Owner:** Worker Agent / AI Runtime Team  

---

## Overview

The **Web Research Capability** provides the Worker Agent with controlled, structured information gathering from publicly accessible web sources.

It abstracts web search execution, candidate source collection, HTML content extraction, result normalization, and source metadata preservation while ensuring complete compliance with safety constraints.

---

## Key Features

1. **Search Abstraction (`SearchEngineInterface`)**: Decouples web search logic from research execution. Includes `DuckDuckGoSearchEngine` (live HTML search) and `MockSearchEngine` (testing/offline environments).
2. **Content Extraction (`ContentExtractor`)**: Async HTML fetching via `httpx` and DOM sanitization via `BeautifulSoup`. Removes scripts, styles, navigation bars, and footers while extracting readable text.
3. **Structured Research Result (`StructuredResearchResult`)**: Returns a normalized model containing synthesized summary, preserved source metadata, extracted body contents, timing metrics, and success/failure counters.
4. **Source Metadata Preservation (`SourceMetadata`)**: Tracks target URL, page title, snippet preview, domain, fetch duration, content length, and explicit `SourceStatus` (`SUCCESS`, `FAILED`, `UNAVAILABLE`, `MALFORMED_URL`, `FETCH_ERROR`).
5. **Robust Error Handling**: Gracefully handles network timeouts, HTTP errors (404/500/403), malformed URLs, and unreachable domains without aborting the research pipeline for remaining sources.
6. **Centralized Logging Integration**: Full integration with `app.core.logging` structured logging framework.
7. **Tool Registry Integration**: Registered under `web_research` with status `READY` in `ToolRegistry`.

---

## Security & Operational Constraints

The Web Research capability strictly enforces the following constraints:
- **No Authentication Bypass**: Operates strictly on publicly accessible pages.
- **No CAPTCHA Evasion**: Does not attempt stealth or bot-detection evasion mechanisms.
- **No Private Data Scraping**: Scrapes only public HTML web content.
- **Source Attribution**: Preserves original source URL, domain, and metadata for every finding without treating unverified web content as unconditioned ground truth.

---

## Data Schemas

### `WebResearchRequest`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | *Required* | Search query or research topic |
| `max_results` | `int` | `5` | Maximum number of web sources to gather (1–20) |
| `extract_content` | `bool` | `True` | Whether to fetch and parse full page body text |
| `timeout_seconds` | `float` | `10.0` | HTTP request timeout threshold in seconds |

### `StructuredResearchResult`

| Attribute | Type | Description |
|---|---|---|
| `query` | `str` | Original research query |
| `summary` | `str` | Synthesized summary of research findings |
| `sources` | `List[SourceMetadata]` | Preserved metadata records for candidate sources |
| `extracted_contents` | `List[ExtractedPageContent]` | Extracted readable text bodies |
| `total_sources_found` | `int` | Count of candidate sources identified |
| `successful_sources_count` | `int` | Count of successfully processed sources |
| `failed_sources_count` | `int` | Count of failed or unavailable sources |
| `execution_time_seconds` | `float` | Total execution runtime in seconds |
| `timestamp` | `datetime` | UTC execution timestamp |

---

## Code Example

```python
from app.tools.web_research import WebResearchTool, WebResearchRequest, MockSearchEngine

# Instantiate with a search engine (DuckDuckGo or Mock)
tool = WebResearchTool()

request = WebResearchRequest(
    query="Python FastAPI best practices",
    max_results=3,
    extract_content=True
)

result = await tool.research(request)

print(f"Summary: {result.summary}")
for source in result.sources:
    print(f"- [{source.status}] {source.title} ({source.url})")
```
