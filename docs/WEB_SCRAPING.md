# Web Scraping Capability & Tool Documentation

**Version:** 1.0.0  
**Status:** Approved  
**Module:** `backend/app/tools/web_scraping/`  
**Tool Registry Key:** `web_scraping`  
**Adapter Key:** `web_scraping_adapter`  

---

## Overview

The **Web Scraping** capability provides the Worker Agent with controlled, structured extraction of information from publicly accessible web pages.

Unlike **Web Research** (which focuses on search, discovery, and synthesis), **Web Scraping** operates on a specific target URL to retrieve HTML content and parse targeted page elements into structured JSON objects using CSS selectors or standard metadata schemas.

---

## Architecture & Data Flow

```
WorkerAgent Task
      │
      ▼
WebScrapingAdapter (BaseToolAdapter)
      │
      ▼
  WebScraper
 ┌────┴──────────────────────────┐
 │ 1. URL Validation             │ (Enforces scheme & blocks private IPs/localhost)
 │ 2. Page Retrieval             │ (httpx AsyncClient)
 │ 3. HTML Parsing               │ (BeautifulSoup html.parser)
 │ 4. Structured Field Extract   │ (CSS Selectors / Attributes)
 │ 5. Logging & Source Metadata  │ (Preserves source URL & metrics)
 └────┬──────────────────────────┘
      ▼
ExecutionResult (output, metrics, logs)
```

---

## Safety & Security Constraints

The Web Scraping tool strictly adheres to project security and ethical guidelines:

- **Public Content Only:** Scraping is restricted to publicly accessible `http://` and `https://` URLs.
- **SSRF Prevention:** URLs targeting `localhost`, loopback addresses (`127.0.0.1`), RFC1918 private IP ranges (`10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`), and `.local` domains are automatically rejected.
- **No Evasion / Anti-Bot Bypassing:** Does not bypass CAPTCHAs, paywalls, authentication, or anti-scraping mechanisms.
- **Timeout Protection:** Request timeouts are enforced to prevent worker starvation.

---

## Data Contracts

### `ScrapeRequest`
| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `url` | `str` | Public target URL | *Required* |
| `extraction_rules` | `List[ExtractionRule]` | Custom CSS selector rules | `[]` |
| `timeout_seconds` | `float` | Maximum HTTP request duration | `10.0` |
| `user_agent` | `str` | HTTP User-Agent header | `"AetherPhoenix-WorkerAgent/1.0"` |
| `parse_metadata` | `bool` | Automatically extract title & meta tags | `True` |

### `ExtractionRule`
| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `field_name` | `str` | Output key name | *Required* |
| `selector` | `str` | CSS selector | *Required* |
| `attribute` | `Optional[str]` | HTML attribute (e.g. `'href'`, `'src'`) or text if `None` | `None` |
| `default_value` | `Any` | Fallback if selector yields no match | `None` |
| `is_list` | `bool` | Extract all matching elements into a list | `False` |

### `ScrapeResult`
| Field | Type | Description |
|-------|------|-------------|
| `url` | `str` | Preserved target URL |
| `success` | `bool` | `True` if page was retrieved and parsed successfully |
| `extracted_data` | `Dict[str, Any]` | Extracted structured key-value pairs |
| `source_metadata` | `SourceMetadata` | HTTP response code, content type, response time, title |
| `error_message` | `Optional[str]` | Error message if `success` is `False` |

---

## Tool Registry & Worker Integration

To register the tool and adapter:

```python
from app.tools.registry import ToolRegistry
from app.agents.worker.agent import WorkerAgent
from app.tools.web_scraping import register_web_scraping_tool

registry = ToolRegistry()
worker = WorkerAgent(tool_registry=registry)

# Registers "web_scraping" tool and "web_scraping_adapter"
register_web_scraping_tool(registry=registry, worker_agent=worker)
```

---

## Usage Examples

### 1. Simple URL Task Description
```python
task = Task(
    workflow_id=uuid.uuid4(),
    task_name="Scrape Article",
    description="https://example.com/news/article-123",
    required_tool="web_scraping",
    category=TaskCategory.WEB_SCRAPING,
    expected_output="Extracted article metadata and title",
)
```

### 2. Structured JSON Task Description with Custom Selectors
```python
json_payload = {
    "url": "https://example.com/store/laptop-1",
    "parse_metadata": True,
    "extraction_rules": [
        {"field_name": "product_name", "selector": "h1.product-title"},
        {"field_name": "price", "selector": "span.price"},
        {"field_name": "specs", "selector": "ul.specifications li", "is_list": True},
        {"field_name": "buy_url", "selector": "a#buy-btn", "attribute": "href"}
    ]
}

task = Task(
    workflow_id=uuid.uuid4(),
    task_name="Extract Product Info",
    description=json.dumps(json_payload),
    required_tool="web_scraping",
    category=TaskCategory.WEB_SCRAPING,
    expected_output="Product details dictionary",
)
```
