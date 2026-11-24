import logging
import time
from typing import Any, Dict, Optional

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.tools.adapter import BaseToolAdapter
from app.tools.web_research.schemas import WebResearchRequest
from app.tools.web_research.tool import WebResearchTool

logger = logging.getLogger(__name__)


class WebResearchToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging the Worker Agent and WebResearchTool.
    Executes multi-query web research, extracts facts from credible sources,
    cross-checks claims, and returns verified findings.
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
            or inputs.get("topic")
            or task.task_name
            or "research"
        )
        max_results = inputs.get("max_results", 5)

        try:
            req = WebResearchRequest(
                query=query,
                sub_queries=inputs.get("sub_queries", []),
                max_results=max_results,
                extract_content=inputs.get("extract_content", True),
                timeout_seconds=inputs.get("timeout_seconds", 10.0),
            )
            result = await self.tool.research(req)
            execution_time_ms = (time.time() - start_time) * 1000.0

            serialized_sources = [s.model_dump() for s in result.sources]

            output_payload = {
                "query": result.query,
                "summary": result.summary,
                "research_summary": result.summary,
                "topic": query,
                "notes": result.summary,
                "raw topic notes": result.summary,
                "total_sources_found": result.total_sources_found,
                "successful_sources_count": result.successful_sources_count,
                "sources": serialized_sources,
                "key_findings": result.key_findings,
                "cross_checked_claims": result.cross_checked_claims,
                "sub_queries_used": result.sub_queries_used,
            }
            if getattr(task, "expected_output", None):
                output_payload[task.expected_output] = result.summary

            logs_captured.append(
                f"Web research completed for '{query}': found {result.total_sources_found} sources "
                f"({result.successful_sources_count} successful)."
            )

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output_payload,
                logs=logs_captured,
                metrics=ExecutionMetrics(execution_time_ms=execution_time_ms, exit_code=0),
            )
        except Exception as exc:
            logger.error(f"Web research failed for task {task.task_id}: {exc}", exc_info=True)
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="WEB_RESEARCH_FAILED",
                    error_message=str(exc),
                    is_recoverable=True,
                ),
                logs=logs_captured,
                metrics=ExecutionMetrics(
                    execution_time_ms=(time.time() - start_time) * 1000.0,
                    exit_code=1,
                ),
            )
