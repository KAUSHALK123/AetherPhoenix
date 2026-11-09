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

        try:
            req = WebResearchRequest(
                query=query,
                max_results=inputs.get("max_results", 5),
                extract_content=inputs.get("extract_content", True),
                timeout_seconds=inputs.get("timeout_seconds", 10.0),
            )
            result = await self.tool.research(req)
            execution_time_ms = (time.time() - start_time) * 1000.0

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output={
                    "query": result.query,
                    "summary": result.summary,
                    "total_sources_found": result.total_sources_found,
                    "sources": [s.model_dump() for s in result.sources],
                },
                logs=logs_captured + [f"Web research completed for '{query}'."],
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
