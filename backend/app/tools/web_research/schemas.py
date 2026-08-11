from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SourceStatus(str, Enum):
    """Execution status of a web research source."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    MALFORMED_URL = "MALFORMED_URL"
    FETCH_ERROR = "FETCH_ERROR"


class SourceMetadata(BaseModel):
    """Metadata representing a web source discovered during research."""

    url: str = Field(..., description="Target URL of the web source")
    title: str = Field(default="", description="Title of the webpage or source")
    snippet: str = Field(
        default="", description="Brief text snippet or preview from search results"
    )
    domain: str = Field(default="", description="Extracted domain name")
    status: SourceStatus = Field(
        default=SourceStatus.SUCCESS, description="Access/fetch status"
    )
    fetch_time_seconds: Optional[float] = Field(
        default=None, description="Time taken to fetch source"
    )
    error_message: Optional[str] = Field(
        default=None, description="Detailed error description if fetch failed"
    )
    content_length: int = Field(
        default=0, description="Character length of extracted text"
    )


class ExtractedPageContent(BaseModel):
    """Full text content extracted from an accessible webpage."""

    url: str = Field(..., description="Target URL")
    title: str = Field(default="", description="Document title")
    content: str = Field(default="", description="Cleaned readable page body text")
    status: SourceStatus = Field(
        default=SourceStatus.SUCCESS, description="Content extraction status"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if extraction failed"
    )


class WebResearchRequest(BaseModel):
    """Input request parameters for performing web research."""

    query: str = Field(..., description="Search query or research topic")
    max_results: int = Field(
        default=5, ge=1, le=20, description="Maximum number of sources to collect"
    )
    extract_content: bool = Field(
        default=True, description="Whether to fetch and extract full page body content"
    )
    timeout_seconds: float = Field(
        default=10.0, gt=0.0, description="HTTP timeout threshold in seconds"
    )


class StructuredResearchResult(BaseModel):
    """Normalized structured result returned by the Web Research capability."""

    query: str = Field(..., description="Original research query")
    summary: str = Field(
        default="", description="Synthesized text summary of extracted findings"
    )
    sources: List[SourceMetadata] = Field(
        default_factory=list, description="Preserved source metadata records"
    )
    extracted_contents: List[ExtractedPageContent] = Field(
        default_factory=list, description="Extracted page text records"
    )
    total_sources_found: int = Field(
        default=0, description="Total number of candidate sources found"
    )
    successful_sources_count: int = Field(
        default=0, description="Number of successfully processed sources"
    )
    failed_sources_count: int = Field(
        default=0, description="Number of failed or unavailable sources"
    )
    execution_time_seconds: float = Field(
        default=0.0, description="Total research runtime in seconds"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of research execution",
    )
