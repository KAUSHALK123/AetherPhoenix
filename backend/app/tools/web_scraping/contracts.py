from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExtractionRule(BaseModel):
    """Rule defining how to extract a specific field from an HTML document."""

    field_name: str = Field(..., description="Target name of the extracted field")
    selector: str = Field(..., description="CSS selector for locating HTML element(s)")
    attribute: Optional[str] = Field(
        default=None,
        description=(
            "Attribute to extract (e.g. 'href', 'src', 'content'). "
            "If None, extracts element text."
        ),
    )
    default_value: Any = Field(
        default=None,
        description="Default value to return if selector matches no elements",
    )
    is_list: bool = Field(
        default=False,
        description=(
            "If True, extracts all matching elements as a list. "
            "If False, extracts first match."
        ),
    )


class ScrapeRequest(BaseModel):
    """Payload for configuring a web scraping operation."""

    url: str = Field(..., description="Target URL of the publicly accessible webpage")
    extraction_rules: List[ExtractionRule] = Field(
        default_factory=list,
        description="Optional list of CSS selector extraction rules",
    )
    timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        description="HTTP request timeout in seconds",
    )
    user_agent: str = Field(
        default="AetherPhoenix-WorkerAgent/1.0",
        description="HTTP User-Agent header",
    )
    parse_metadata: bool = Field(
        default=True,
        description="Whether to automatically extract page title and metadata",
    )


class SourceMetadata(BaseModel):
    """Metadata regarding the scraped page and HTTP response."""

    url: str = Field(..., description="Preserved target URL")
    status_code: Optional[int] = Field(default=None, description="HTTP status code")
    content_type: Optional[str] = Field(
        default=None, description="HTTP Content-Type header"
    )
    response_time_ms: float = Field(
        default=0.0, description="HTTP response time in milliseconds"
    )
    page_title: Optional[str] = Field(
        default=None, description="Page title extracted from HTML"
    )
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of when the page was scraped",
    )


class ScrapeResult(BaseModel):
    """Structured result returned from a web scraping execution."""

    url: str = Field(..., description="Target URL")
    success: bool = Field(default=True, description="Indicates if scraping succeeded")
    extracted_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured key-value pairs extracted from the page",
    )
    source_metadata: Optional[SourceMetadata] = Field(
        default=None,
        description="Preserved source metadata",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error description if scraping failed",
    )
