import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.core.config import get_config
from app.services.artifact_storage import get_artifact_storage_service
from app.tools.adapter import BaseToolAdapter
from app.tools.web_research.schemas import WebResearchRequest
from app.tools.web_research.tool import WebResearchTool

logger = logging.getLogger(__name__)


class WebResearchToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging the Worker Agent and WebResearchTool.
    Executes web research, validates that at least 2 sources exist before completion,
    and optionally renders document deliverables (PDF/PPT) if requested.
    """

    def __init__(self, tool: Optional[WebResearchTool] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tool = tool or WebResearchTool()

    async def execute(self, task: Task) -> ExecutionResult:
        start_time = time.time()
        logs_captured = [f"WebResearchToolAdapter executing task '{task.task_name}'"]

        inputs: Dict[str, Any] = dict(task.inputs) if task.inputs else {}
        query = (
            inputs.get("query")
            or inputs.get("search_query")
            or task.task_name
            or "research"
        )
        target_format = inputs.get("target_format", "chat").lower()
        if not target_format or target_format == "chat":
            desc_lower = (task.description or "").lower()
            if "pdf" in desc_lower:
                target_format = "pdf"
            elif "ppt" in desc_lower or "presentation" in desc_lower:
                target_format = "pptx"

        try:
            req = WebResearchRequest(
                query=query,
                max_results=inputs.get("max_results", 5),
                extract_content=inputs.get("extract_content", True),
                timeout_seconds=inputs.get("timeout_seconds", 10.0),
            )
            result = await self.tool.research(req)
            execution_time_ms = (time.time() - start_time) * 1000.0

            # The research task is complete ONLY when a synthesized answer with at least 2 sources exists.
            from app.tools.web_research.schemas import SourceStatus
            successful_sources = [
                s for s in result.sources
                if getattr(s, "status", None) in (SourceStatus.SUCCESS, "SUCCESS", SourceStatus.SUCCESS.value)
            ]
            if len(successful_sources) < 2 or result.successful_sources_count < 2:
                logger.warning(
                    f"Research task {task.task_id} failed: fewer than 2 sources found ({len(successful_sources)})"
                )
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=False,
                    output={
                        "query": result.query,
                        "summary": result.summary,
                        "total_sources_found": result.total_sources_found,
                        "sources": [s.model_dump() for s in result.sources],
                        "chat_reply": result.summary,
                    },
                    error=TaskError(
                        error_code="INSUFFICIENT_SOURCES",
                        error_message=result.summary,
                        is_recoverable=False,
                    ),
                    logs=logs_captured + [
                        f"Research completed with insufficient sources ({len(successful_sources)} < 2)."
                    ],
                    metrics=ExecutionMetrics(execution_time_ms=execution_time_ms),
                )

            # Build standard output
            output: Dict[str, Any] = {
                "query": result.query,
                "summary": result.summary,
                "chat_reply": result.summary,
                "total_sources_found": result.total_sources_found,
                "sources": [s.model_dump() for s in result.sources],
            }
            artifacts: List[Artifact] = []

            # Deliver as PDF or PPT if requested
            if target_format == "pdf":
                try:
                    pdf_artifact = await self._export_research_pdf(
                        task, query, result.summary, successful_sources
                    )
                    if pdf_artifact:
                        artifacts.append(pdf_artifact)
                        output["artifact_id"] = str(pdf_artifact.artifact_id)
                        output["filepath"] = pdf_artifact.filepath
                        output["download_url"] = (
                            f"/api/v1/artifacts/{pdf_artifact.artifact_id}/download"
                        )
                except Exception as doc_err:
                    logger.warning(f"Could not generate PDF for research task: {doc_err}")

            elif target_format == "pptx":
                try:
                    ppt_artifact = await self._export_research_pptx(
                        task, query, result.summary, successful_sources
                    )
                    if ppt_artifact:
                        artifacts.append(ppt_artifact)
                        output["artifact_id"] = str(ppt_artifact.artifact_id)
                        output["filepath"] = ppt_artifact.filepath
                        output["download_url"] = (
                            f"/api/v1/artifacts/{ppt_artifact.artifact_id}/download"
                        )
                except Exception as doc_err:
                    logger.warning(f"Could not generate PPTX for research task: {doc_err}")

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output,
                artifacts=artifacts,
                logs=logs_captured + [
                    f"Web research completed with {len(successful_sources)} verified sources."
                ],
                metrics=ExecutionMetrics(execution_time_ms=execution_time_ms),
            )

        except Exception as exc:
            logger.error(f"Web research failed for task {task.task_id}: {exc}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="WEB_RESEARCH_FAILED",
                    error_message=str(exc),
                ),
                logs=logs_captured,
                metrics=ExecutionMetrics(
                    execution_time_ms=(time.time() - start_time) * 1000.0
                ),
            )

    async def _export_research_pdf(
        self, task: Task, query: str, summary: str, sources: list
    ) -> Optional[Artifact]:
        """Exports the synthesized research summary into a clean PDF document."""
        cfg = get_config()
        artifacts_dir = Path(cfg.ARTIFACTS_DIR)
        task_dir = artifacts_dir / str(task.workflow_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        clean_slug = re.sub(r"[^\w\-_]", "_", query.lower())[:30].strip("_")
        output_path = task_dir / f"research_{clean_slug}.pdf"

        try:
            from app.tools.pdf.generator import PDFDocumentInput, PDFGenerator

            generator = PDFGenerator()
            input_data = PDFDocumentInput(
                title=f"Research Report: {query.title()}",
                author="AetherPhoenix Web Research",
                output_path=str(output_path),
                workflow_id=task.workflow_id,
                elements=[
                    {"type": "heading", "content": f"Research Report: {query.title()}"},
                    {"type": "paragraph", "content": summary},
                ],
            )
            gen_res = generator.generate(input_data)
            if gen_res.success and output_path.exists():
                storage = get_artifact_storage_service()
                artifact = Artifact(
                    workflow_id=task.workflow_id,
                    task_id=task.task_id,
                    name=output_path.name,
                    filepath=str(output_path),
                    artifact_type=ArtifactType.PDF,
                    size_bytes=output_path.stat().st_size,
                    checksum="pdf_checksum",
                )
                saved = await storage.register_artifact(
                    artifact, content=output_path.read_bytes()
                )
                return saved
        except Exception as e:
            logger.warning(f"Failed to generate research PDF: {e}")
        return None

    async def _export_research_pptx(
        self, task: Task, query: str, summary: str, sources: list
    ) -> Optional[Artifact]:
        """Exports the synthesized research summary into a PPTX presentation."""
        cfg = get_config()
        artifacts_dir = Path(cfg.ARTIFACTS_DIR)
        task_dir = artifacts_dir / str(task.workflow_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        clean_slug = re.sub(r"[^\w\-_]", "_", query.lower())[:30].strip("_")
        output_path = task_dir / f"research_{clean_slug}.pptx"

        try:
            from app.tools.ppt.generator import PPTGenerator

            generator = PPTGenerator()
            content_dict = {
                "title": f"Research: {query.title()}",
                "slides": [
                    {
                        "title": f"Overview: {query.title()}",
                        "bullets": [
                            summary[:100] + "...",
                            f"Analyzed {len(sources)} verified sources.",
                        ],
                    }
                ],
            }
            res = generator.generate_from_content(content_dict, str(output_path))
            if res.success and output_path.exists():
                storage = get_artifact_storage_service()
                artifact = Artifact(
                    workflow_id=task.workflow_id,
                    task_id=task.task_id,
                    name=output_path.name,
                    filepath=str(output_path),
                    artifact_type=ArtifactType.PPT,
                    size_bytes=output_path.stat().st_size,
                    checksum="pptx_checksum",
                )
                saved = await storage.register_artifact(
                    artifact, content=output_path.read_bytes()
                )
                return saved
        except Exception as e:
            logger.warning(f"Failed to generate research PPTX: {e}")
        return None
