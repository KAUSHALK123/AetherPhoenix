from typing import Any, Dict, Optional

from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.tool import Tool, ToolState

from app.core.logging import get_logger
from app.tools.registry import ToolRegistry
from app.tools.web_research.schemas import (
    StructuredResearchResult,
    WebResearchRequest,
)
from app.tools.web_research.tool import WebResearchTool

logger = get_logger(__name__)


class WorkerWebResearchCapability:
    """
    Capability runner allowing Worker Agent to execute web research tasks.
    Delegates research execution to registered WebResearchTool.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry()
        self._ensure_registered()

    def _ensure_registered(self) -> None:
        """Registers default WebResearchTool contract and instance if missing."""
        if not self.registry.get("web_research"):
            tool_contract = Tool(
                name="web_research",
                version="1.0.0",
                status=ToolState.READY,
                adapter="web_research_adapter",
            )
            self.registry.register(tool_contract, instance=WebResearchTool())

    async def execute_task(
        self, task: Task, task_inputs: Optional[Dict[str, Any]] = None
    ) -> StructuredResearchResult:
        """
        Executes a Web Research task delegated to the Worker Agent.
        """
        logger.info(
            "Worker Agent requested Web Research capability", task_id=str(task.task_id)
        )

        if task.category != TaskCategory.WEB_RESEARCH:
            logger.warning(
                "Task category mismatch for web research capability",
                task_id=str(task.task_id),
                category=task.category,
            )

        inputs = task_inputs or {}
        query = inputs.get("query") or task.description or task.task_name
        max_results = inputs.get("max_results", 5)
        extract_content = inputs.get("extract_content", True)
        timeout_seconds = inputs.get("timeout_seconds", 10.0)

        research_tool: Optional[WebResearchTool] = self.registry.get_instance(
            "web_research"
        )
        if not research_tool:
            research_tool = WebResearchTool()

        request = WebResearchRequest(
            query=query,
            max_results=max_results,
            extract_content=extract_content,
            timeout_seconds=timeout_seconds,
        )

        task.status = TaskStatus.RUNNING
        task.execution_logs.append(f"Initiated Web Research for query: '{query}'")

        try:
            result = await research_tool.research(request)
            task.status = TaskStatus.COMPLETED
            task.execution_logs.append(
                f"Completed Web Research. Found {result.total_sources_found} "
                f"sources ({result.successful_sources_count} ok, "
                f"{result.failed_sources_count} failed)."
            )
            return result
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.execution_logs.append(f"Web Research execution failed: {str(exc)}")
            logger.error(
                "Worker Web Research execution error",
                task_id=str(task.task_id),
                error=str(exc),
                exc_info=True,
            )
            raise
