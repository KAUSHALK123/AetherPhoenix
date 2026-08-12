import json
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from shared.contracts.task import Task, TaskCategory

from app.agents.worker.agent import WorkerAgent
from app.tools.registry import ToolRegistry
from app.tools.web_scraping import register_web_scraping_tool


@pytest.fixture
def worker_setup():
    registry = ToolRegistry()
    agent = WorkerAgent(tool_registry=registry)
    register_web_scraping_tool(registry=registry, worker_agent=agent)
    return registry, agent


@pytest.mark.asyncio
async def test_worker_web_scraping_plain_url(worker_setup):
    registry, agent = worker_setup

    task = Task(
        workflow_id=uuid.uuid4(),
        task_name="Scrape Tech Blog",
        description="https://example.com/blog",
        required_tool="web_scraping",
        category=TaskCategory.WEB_SCRAPING,
        expected_output="Blog title and content",
    )

    mock_html = (
        "<html><head><title>Tech Blog</title></head>"
        "<body><h1>Latest Tech</h1></body></html>"
    )
    mock_response = httpx.Response(
        status_code=200,
        html=mock_html,
        request=httpx.Request("GET", "https://example.com/blog"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await agent.execute(task)

    assert result.success is True
    assert result.task_id == task.task_id
    assert result.output["url"] == "https://example.com/blog"
    assert result.output["source_metadata"]["page_title"] == "Tech Blog"
    assert result.metrics.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_worker_web_scraping_json_payload(worker_setup):
    registry, agent = worker_setup

    json_payload = {
        "url": "https://example.com/products",
        "extraction_rules": [
            {"field_name": "product_name", "selector": ".product-title"},
            {"field_name": "price", "selector": ".price"},
        ],
    }

    task = Task(
        workflow_id=uuid.uuid4(),
        task_name="Scrape Product Details",
        description=json.dumps(json_payload),
        required_tool="web_scraping",
        category=TaskCategory.WEB_SCRAPING,
        expected_output="Structured product details",
    )

    mock_html = """
    <html><body>
        <h2 class="product-title">Quantum Laptop</h2>
        <span class="price">$1,299</span>
    </body></html>
    """
    mock_response = httpx.Response(
        status_code=200,
        html=mock_html,
        request=httpx.Request("GET", "https://example.com/products"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await agent.execute(task)

    assert result.success is True
    data = result.output["extracted_data"]
    assert data["product_name"] == "Quantum Laptop"
    assert data["price"] == "$1,299"


@pytest.mark.asyncio
async def test_worker_web_scraping_invalid_url(worker_setup):
    registry, agent = worker_setup

    task = Task(
        workflow_id=uuid.uuid4(),
        task_name="Scrape Invalid Local Target",
        description="http://localhost:9000/secret",
        required_tool="web_scraping",
        category=TaskCategory.WEB_SCRAPING,
        expected_output="Output",
    )

    result = await agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert (
        "URL Validation Error" in result.output["error_message"]
        or "EXECUTION_FAILED" in result.error.error_code
    )
