import json
from typing import Any, Dict

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.core.logging import get_logger
from app.tools.adapter import BaseToolAdapter
from app.tools.web_scraping.contracts import ExtractionRule, ScrapeRequest
from app.tools.web_scraping.scraper import WebScraper

logger = get_logger(__name__)


class WebScrapingAdapter(BaseToolAdapter):
    """
    Adapter bridging the Worker Agent and the WebScraper tool.
    Executes web scraping tasks and maps output into standard ExecutionResult contracts.
    """

    def __init__(self, scraper: WebScraper | None = None):
        self.scraper = scraper or WebScraper()

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Parses task inputs, invokes WebScraper, and returns ExecutionResult.
        """
        logger.info(f"WebScrapingAdapter executing task {task.task_id}")

        try:
            scrape_request = self._parse_task_to_request(task)
            scrape_result = await self.scraper.scrape(scrape_request)

            response_time_ms = (
                scrape_result.source_metadata.response_time_ms
                if scrape_result.source_metadata
                else 0.0
            )

            if not scrape_result.success:
                err_msg = scrape_result.error_message or "Web scraping failed."
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=False,
                    error=TaskError(
                        error_code="SCRAPING_FAILED",
                        error_message=err_msg,
                    ),
                    output=scrape_result.model_dump(),
                    metrics=ExecutionMetrics(execution_time_ms=response_time_ms),
                )

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=scrape_result.model_dump(),
                metrics=ExecutionMetrics(execution_time_ms=response_time_ms),
            )

        except Exception as e:
            logger.error(
                f"Error in WebScrapingAdapter for task {task.task_id}: {str(e)}",
                exc_info=True,
            )
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="ADAPTER_ERROR",
                    error_message=f"WebScrapingAdapter error: {str(e)}",
                ),
                metrics=ExecutionMetrics(execution_time_ms=0.0),
            )

    def _parse_task_to_request(self, task: Task) -> ScrapeRequest:
        """
        Extracts target URL and rules from task description or expected_output.
        """
        desc = task.description.strip() if task.description else ""

        if desc.startswith("{") and desc.endswith("}"):
            try:
                data: Dict[str, Any] = json.loads(desc)
                url = data.get("url", "")
                rules_raw = data.get("extraction_rules", [])
                rules = [
                    ExtractionRule(**r) if isinstance(r, dict) else r for r in rules_raw
                ]
                timeout = float(data.get("timeout_seconds", 10.0))
                parse_meta = bool(data.get("parse_metadata", True))

                return ScrapeRequest(
                    url=url,
                    extraction_rules=rules,
                    timeout_seconds=timeout,
                    parse_metadata=parse_meta,
                )
            except Exception as exc:
                logger.warning(f"Failed to parse JSON task description: {str(exc)}")

        if desc.startswith("http://") or desc.startswith("https://"):
            return ScrapeRequest(url=desc)

        if task.expected_output and (
            task.expected_output.startswith("http://")
            or task.expected_output.startswith("https://")
        ):
            return ScrapeRequest(url=task.expected_output.strip())

        raise ValueError(
            "Task description must be a valid HTTP/HTTPS URL "
            "or a JSON string specifying 'url'."
        )
