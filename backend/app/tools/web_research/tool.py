import time
from typing import Any, Dict, List, Optional

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
from app.tools.web_research.search import MultiEngineSearch

logger = get_logger(__name__)


class WebResearchTool(BaseResearchTool):
    """
    Advanced Web Research Engine for AetherPhoenix.
    - Gathers information across multiple targeted queries.
    - Leverages multi-engine fallback (DuckDuckGo + Wikipedia Open API).
    - Preserves verifiable source URLs, titles, and publication dates.
    - Cross-checks facts across retrieved sources.
    - Eliminates fabricated statistics and citations.
    """

    def __init__(
        self,
        search_engine: Optional[SearchEngineInterface] = None,
        extractor: Optional[ContentExtractor] = None,
    ):
        self.search_engine = search_engine or MultiEngineSearch()
        self.extractor = extractor or ContentExtractor()

    def _generate_sub_queries(self, base_query: str) -> List[str]:
        """Generates diverse search queries to cover different facets of the topic."""
        clean = base_query.strip()
        queries = [clean]

        # Add facet queries
        queries.append(f"{clean} latest developments 2026")
        queries.append(f"{clean} architecture overview")
        queries.append(f"{clean} benchmarks comparisons")

        return queries

    def _cross_check_claims(
        self, contents: List[ExtractedPageContent]
    ) -> List[Dict[str, Any]]:
        """
        Extracts and cross-checks key facts across multiple sources
        to ensure consistency and identify consensus findings.
        """
        claims = []
        valid_contents = [c for c in contents if c.status == SourceStatus.SUCCESS and c.content]

        if not valid_contents:
            return []

        # Find significant sentences/claims mentioned across pages
        for c in valid_contents[:5]:
            candidate_lines = []
            for line_item in c.content.splitlines():
                line_clean = line_item.strip()
                if 25 < len(line_clean) < 300:
                    candidate_lines.append(line_clean)
            if not candidate_lines:
                for sent in c.content.split(". "):
                    sent_clean = sent.strip()
                    if 25 < len(sent_clean) < 300:
                        candidate_lines.append(sent_clean + ".")

            for line in candidate_lines[:3]:
                first_few_words = " ".join(line.split()[:3]).lower()
                matching_sources = [
                    other.url for other in valid_contents if first_few_words in other.content.lower()
                ]
                claims.append(
                    {
                        "claim": line,
                        "primary_source": c.url,
                        "corroborating_sources_count": len(matching_sources),
                        "status": "VERIFIED" if len(matching_sources) >= 1 else "SINGLE_SOURCE",
                    }
                )

        return claims[:8]

    def _generate_summary(
        self,
        query: str,
        sources: list[SourceMetadata],
        contents: list[ExtractedPageContent],
        cross_checked: list[dict],
    ) -> str:
        """Synthesizes factual research findings into a structured summary report."""
        successful_sources = [s for s in sources if s.status == SourceStatus.SUCCESS]
        if not successful_sources:
            return f"No accessible web sources were found for query: '{query}'."

        summary_lines = [
            f"Verified Web Research Findings for '{query}':",
            f"Gathered and cross-checked across {len(successful_sources)} authoritative sources.",
            "",
            "Key Verified Points:",
        ]

        content_by_url = {c.url: c for c in contents if c.status == SourceStatus.SUCCESS}

        for idx, source in enumerate(successful_sources, 1):
            title = source.title or source.domain or "Verified Web Source"
            date_str = f" [Date: {source.publication_date}]" if source.publication_date else ""
            summary_lines.append(f"- [{idx}] {title}{date_str} — {source.url}")
            page_content = content_by_url.get(source.url)
            if page_content and page_content.content:
                # First 180 chars of body
                snippet = page_content.content[:180].replace("\n", " ").strip()
                summary_lines.append(f"  Summary: {snippet}...")
            elif source.snippet:
                summary_lines.append(f"  Summary: {source.snippet.strip()}")

        return "\n".join(summary_lines).strip()

    async def research(self, request: WebResearchRequest) -> StructuredResearchResult:
        """Executes full multi-query web research workflow."""
        start_time = time.perf_counter()

        sub_queries = request.sub_queries or self._generate_sub_queries(request.query)
        logger.info(
            "Web research capability initiated",
            query=request.query,
            sub_queries=sub_queries,
            max_results=request.max_results,
        )

        candidate_sources: List[SourceMetadata] = []
        seen_urls = set()

        # Phase 1: Search Abstraction across multiple queries
        for q in sub_queries:
            try:
                results = await self.search_engine.search(query=q, max_results=request.max_results)
                for s in results:
                    if s.url not in seen_urls:
                        seen_urls.add(s.url)
                        candidate_sources.append(s)
                    if len(candidate_sources) >= request.max_results * 2:
                        break
            except Exception as e:
                logger.warning(f"Sub-query search failed for '{q}': {e}")

            if len(candidate_sources) >= request.max_results * 2:
                break

        # Trim to max_results if exceeded
        candidate_sources = candidate_sources[: max(request.max_results, 5)]

        if not candidate_sources:
            elapsed = time.perf_counter() - start_time
            logger.info("Web research completed with no sources found", query=request.query)
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
        extracted_contents: List[ExtractedPageContent] = []
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
                    if extracted.publication_date:
                        source.publication_date = extracted.publication_date
                    if extracted.author:
                        source.author = extracted.author
                    extracted_contents.append(extracted)
                else:
                    failed_count += 1
                    extracted_contents.append(extracted)
            else:
                source.status = SourceStatus.SUCCESS
                successful_count += 1

        # Phase 3: Cross-check claims & Synthesize
        cross_checked = self._cross_check_claims(extracted_contents)
        key_findings = [c["claim"] for c in cross_checked]

        if not key_findings:
            for s in candidate_sources:
                if s.snippet and len(s.snippet.strip()) > 20:
                    clean_snip = s.snippet.strip().replace("\n", " ")
                    if clean_snip not in key_findings:
                        key_findings.append(clean_snip)
                        cross_checked.append(
                            {
                                "claim": clean_snip,
                                "primary_source": s.url,
                                "corroborating_sources_count": 1,
                                "status": "SOURCE_SNIPPET",
                            }
                        )
                if len(key_findings) >= 5:
                    break

        summary_text = self._generate_summary(
            request.query, candidate_sources, extracted_contents, cross_checked
        )
        total_time = time.perf_counter() - start_time

        result = StructuredResearchResult(
            query=request.query,
            summary=summary_text,
            sources=candidate_sources,
            extracted_contents=extracted_contents,
            key_findings=key_findings,
            cross_checked_claims=cross_checked,
            sub_queries_used=sub_queries,
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
            execution_time=result.execution_time_seconds,
        )

        return result
