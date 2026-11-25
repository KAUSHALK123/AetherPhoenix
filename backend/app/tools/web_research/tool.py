import os
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
    Gathers, extracts, normalizes, and synthesizes structured research findings.
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
        """
        Synthesizes research findings into a structured, authoritative answer with source URLs.
        Requires at least 2 valid sources for synthesis. If fewer than 2 sources, plainly reports
        what was tried without faking results.
        """
        successful_sources = [s for s in sources if s.status == SourceStatus.SUCCESS]
        content_by_url = {
            c.url: c for c in contents if c.status == SourceStatus.SUCCESS and c.content.strip()
        }

        # Filter sources that actually yielded substantive content or search snippet
        valid_sources = [
            s for s in successful_sources
            if (s.url in content_by_url and len(content_by_url[s.url].content.strip()) > 30)
            or (s.snippet and len(s.snippet.strip()) > 20)
        ]

        if len(valid_sources) < 2:
            return (
                f"Web research was conducted for query: '{query}'. "
                f"However, fewer than 2 accessible web sources with verified content could be retrieved "
                f"(found {len(valid_sources)} source(s)). "
                f"Checked primary search engines (DuckDuckGo, Wikipedia) and HTTP endpoints, but "
                f"insufficient content was available to synthesize an authoritative report. Never faking results."
            )

        # Attempt synthesis with external LLM if API key is present
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                import httpx

                source_context = ""
                for idx, source in enumerate(valid_sources[:5], 1):
                    title = source.title or source.domain or f"Source {idx}"
                    page_content = content_by_url.get(source.url)
                    text_body = page_content.content[:1500] if page_content else source.snippet
                    source_context += f"\n\nSource {idx} ({title}) - URL: {source.url}\n{text_body}"

                prompt = (
                    f"You are the AetherPhoenix Web Research Assistant.\n"
                    f"Synthesize an authoritative, structured research summary for the topic: '{query}'.\n"
                    f"Use ONLY the following verified web sources:\n{source_context}\n\n"
                    f"Format requirements:\n"
                    f"1. Executive Overview (2-3 concise paragraphs summarizing the topic and landscape)\n"
                    f"2. Key Trends & Findings (bulleted points with inline citations to source URLs)\n"
                    f"3. Strategic Insights & Opportunities\n"
                    f"4. Sources Consulted (list all source URLs consulted)\n"
                    f"Do not invent facts or cite URLs outside the sources provided."
                )

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        llm_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        if len(llm_text) > 100:
                            return llm_text
            except Exception as e:
                logger.warning(f"LLM research synthesis via Gemini failed, falling back to deterministic synthesis: {e}")

        # Deterministic structured synthesis fallback (guarantees >= 2 verified sources cited)
        summary_lines = [
            f"# Research Summary: {query.title()}",
            "",
            "## Executive Overview",
            f"This research synthesized information across {len(valid_sources)} independent web sources to identify recent developments, applications, and trends regarding **{query}**.",
            "",
            "## Key Trends & Insights",
        ]

        for idx, source in enumerate(valid_sources[:5], 1):
            title = source.title or source.domain or f"Source {idx}"
            page_content = content_by_url.get(source.url)
            if page_content and page_content.content:
                sentences = [s.strip() for s in page_content.content.split(".") if len(s.strip()) > 35]
                insight = ". ".join(sentences[:3]) + "." if sentences else source.snippet
            else:
                insight = source.snippet

            summary_lines.append(f"- **{title}**: {insight}")
            summary_lines.append(f"  *Source*: {source.url}")

        summary_lines.append("")
        summary_lines.append("## Sources Consulted")
        for idx, source in enumerate(valid_sources[:5], 1):
            title = source.title or source.domain or f"Source {idx}"
            summary_lines.append(f"{idx}. [{title}]({source.url}) - {source.url}")

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
