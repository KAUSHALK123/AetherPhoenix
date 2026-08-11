import time
from typing import Optional

from app.core.logging import get_logger
from app.tools.web_research.extractor import ContentExtractor
from app.tools.web_research.interface import BaseResearchTool, SearchEngineInterface
from app.tools.web_research.schemas import (
    ExtractedPageContent,
    SourceMetadata,
    SourceStatus,
    StructuredResearchResult,
    WebResearchRequest,
)
from app.tools.web_research.search import DuckDuckGoSearchEngine

logger = get_logger(__name__)


class WebResearchTool(BaseResearchTool):
    """
    Controlled Web Research capability for Worker Agent.
    Gathers, extracts, normalizes, and packages structured research findings.
    """

    def __init__(
        self,
        search_engine: Optional[SearchEngineInterface] = None,
        extractor: Optional[ContentExtractor] = None,
    ):
        self.search_engine = search_engine or DuckDuckGoSearchEngine()
        self.extractor = extractor or ContentExtractor()

    def _generate_summary(
        self,
        query: str,
        sources: list[SourceMetadata],
        contents: list[ExtractedPageContent],
    ) -> str:
        """Normalizes and synthesizes research findings into a readable summary."""
        successful_sources = [s for s in sources if s.status == SourceStatus.SUCCESS]
        if not successful_sources:
            return f"No accessible web sources were found for query: '{query}'."

        summary_lines = [f"Web Research Summary for '{query}':", ""]

        content_by_url = {
            c.url: c for c in contents if c.status == SourceStatus.SUCCESS
        }

        for idx, source in enumerate(successful_sources, 1):
            title = source.title or source.domain or "Untitled Source"
            snippet = source.snippet.strip()
            page_content = content_by_url.get(source.url)

            summary_lines.append(f"[{idx}] {title} ({source.domain})")
            summary_lines.append(f"    URL: {source.url}")
            if snippet:
                summary_lines.append(f"    Snippet: {snippet}")
            if page_content and page_content.content:
                # First 200 characters of extracted body text
                preview = page_content.content[:200].replace("\n", " ")
                summary_lines.append(f"    Content Preview: {preview}...")
            summary_lines.append("")

        return "\n".join(summary_lines).strip()

    async def research(self, request: WebResearchRequest) -> StructuredResearchResult:
        """Executes full web research workflow."""
        start_time = time.perf_counter()
        logger.info(
            "Web research capability initiated",
            query=request.query,
            max_results=request.max_results,
            extract_content=request.extract_content,
        )

        candidate_sources: list[SourceMetadata] = []
        extracted_contents: list[ExtractedPageContent] = []

        # Phase 1: Search Abstraction
        try:
            candidate_sources = await self.search_engine.search(
                query=request.query, max_results=request.max_results
            )
        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            logger.error(
                "Web research search phase failed", query=request.query, error=str(exc)
            )
            return StructuredResearchResult(
                query=request.query,
                summary=f"Web research failed during search phase: {str(exc)}",
                sources=[],
                extracted_contents=[],
                total_sources_found=0,
                successful_sources_count=0,
                failed_sources_count=0,
                execution_time_seconds=round(elapsed, 3),
            )

        if not candidate_sources:
            elapsed = time.perf_counter() - start_time
            logger.info(
                "Web research completed with no sources found", query=request.query
            )
            return StructuredResearchResult(
                query=request.query,
                summary=f"No web sources found matching query: '{request.query}'.",
                sources=[],
                extracted_contents=[],
                total_sources_found=0,
                successful_sources_count=0,
                failed_sources_count=0,
                execution_time_seconds=round(elapsed, 3),
            )

        # Phase 2: Source Collection & Content Extraction
        successful_count = 0
        failed_count = 0

        for source in candidate_sources:
            if request.extract_content:
                extracted, elapsed_source = await self.extractor.extract_content(
                    url=source.url, timeout_seconds=request.timeout_seconds
                )
                source.fetch_time_seconds = round(elapsed_source, 3)
                source.status = extracted.status
                source.error_message = extracted.error_message

                if extracted.status == SourceStatus.SUCCESS:
                    successful_count += 1
                    source.content_length = len(extracted.content)
                    if not source.title and extracted.title:
                        source.title = extracted.title
                    extracted_contents.append(extracted)
                else:
                    failed_count += 1
                    extracted_contents.append(extracted)
            else:
                source.status = SourceStatus.SUCCESS
                successful_count += 1

        # Phase 3: Result Normalization & Metadata Preservation
        total_time = time.perf_counter() - start_time
        summary_text = self._generate_summary(
            request.query, candidate_sources, extracted_contents
        )

        result = StructuredResearchResult(
            query=request.query,
            summary=summary_text,
            sources=candidate_sources,
            extracted_contents=extracted_contents,
            total_sources_found=len(candidate_sources),
            successful_sources_count=successful_count,
            failed_sources_count=failed_count,
            execution_time_seconds=round(total_time, 3),
        )

        logger.info(
            "Web research capability completed",
            query=request.query,
            total_sources=result.total_sources_found,
            successful=result.successful_sources_count,
            failed=result.failed_sources_count,
            execution_time=result.execution_time_seconds,
        )

        return result
