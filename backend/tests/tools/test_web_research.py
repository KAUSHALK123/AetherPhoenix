from uuid import uuid4

import pytest
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.tool import ToolState

from app.agents.worker.research_capability import WorkerWebResearchCapability
from app.tools.registry import ToolRegistry
from app.tools.web_research.extractor import ContentExtractor
from app.tools.web_research.schemas import (
    SourceMetadata,
    SourceStatus,
    WebResearchRequest,
)
from app.tools.web_research.search import MockSearchEngine
from app.tools.web_research.tool import WebResearchTool


@pytest.fixture
def mock_sources():
    return [
        SourceMetadata(
            url="https://example.com/python-guide",
            title="Comprehensive Python Guide",
            snippet="Learn modern Python programming patterns and best practices.",
            domain="example.com",
            status=SourceStatus.SUCCESS,
        ),
        SourceMetadata(
            url="https://example.org/async-python",
            title="AsyncIO in Python",
            snippet="Asynchronous Python programming with asyncio and httpx.",
            domain="example.org",
            status=SourceStatus.SUCCESS,
        ),
    ]


@pytest.fixture
def mock_search_engine(mock_sources):
    return MockSearchEngine(mock_results=mock_sources)


@pytest.fixture
def web_research_tool(mock_search_engine):
    return WebResearchTool(search_engine=mock_search_engine)


@pytest.mark.asyncio
async def test_valid_research_query(web_research_tool):
    """Test 1: Valid research query returns structured results."""
    request = WebResearchRequest(query="Python", max_results=2, extract_content=False)
    result = await web_research_tool.research(request)

    assert result.query == "Python"
    assert result.total_sources_found == 2
    assert result.successful_sources_count == 2
    assert result.failed_sources_count == 0
    assert len(result.sources) == 2
    assert "Comprehensive Python Guide" in result.summary


@pytest.mark.asyncio
async def test_multiple_results(web_research_tool):
    """Test 2: Multiple results are preserved and limited by max_results."""
    request = WebResearchRequest(query="Python", max_results=1, extract_content=False)
    result = await web_research_tool.research(request)

    assert len(result.sources) == 1
    assert result.total_sources_found == 1
    assert result.sources[0].url == "https://example.com/python-guide"


@pytest.mark.asyncio
async def test_no_result_query():
    """Test 3: Query returning no results handles empty state gracefully."""
    empty_engine = MockSearchEngine(mock_results=[])
    tool = WebResearchTool(search_engine=empty_engine)

    request = WebResearchRequest(query="NonExistentTopic12345", max_results=5)
    result = await tool.research(request)

    assert result.total_sources_found == 0
    assert result.successful_sources_count == 0
    assert result.failed_sources_count == 0
    assert "No web sources found" in result.summary


@pytest.mark.asyncio
async def test_unavailable_source():
    """Test 4: Unavailable source (404/HTTP failure) is handled gracefully."""
    extractor = ContentExtractor()
    result_content, elapsed = await extractor.extract_content(
        "https://httpbin.org/status/404", timeout_seconds=5.0
    )

    assert result_content.status == SourceStatus.UNAVAILABLE
    assert (
        "404" in result_content.error_message or "HTTP" in result_content.error_message
    )
    assert elapsed >= 0.0


@pytest.mark.asyncio
async def test_malformed_url():
    """Test 5: Malformed URL returns MALFORMED_URL status without crashing."""
    extractor = ContentExtractor()
    result_content, elapsed = await extractor.extract_content("not_a_valid_url")

    assert result_content.status == SourceStatus.MALFORMED_URL
    assert "Invalid URL" in result_content.error_message


@pytest.mark.asyncio
async def test_search_failure():
    """Test 6: Total search engine failure returns clear error result."""
    failing_engine = MockSearchEngine(
        should_fail=True, error_message="Search backend unreachable"
    )
    tool = WebResearchTool(search_engine=failing_engine)

    request = WebResearchRequest(query="Python")
    result = await tool.research(request)

    assert result.total_sources_found == 0
    assert "failed during search phase" in result.summary


@pytest.mark.asyncio
async def test_result_normalization(web_research_tool):
    """Test 7: Result normalization produces consistent structured schema."""
    request = WebResearchRequest(query="Python", max_results=2, extract_content=False)
    result = await web_research_tool.research(request)

    assert isinstance(result.summary, str)
    assert result.timestamp is not None
    assert result.execution_time_seconds >= 0.0
    for source in result.sources:
        assert source.domain != ""
        assert source.url != ""


@pytest.mark.asyncio
async def test_tool_registry_and_worker_integration(mock_search_engine):
    """Test 8: ToolRegistry registration and Worker Agent capability execution."""
    registry = ToolRegistry()
    capability = WorkerWebResearchCapability(registry=registry)

    # Verify registration
    registered_tool = registry.get("web_research")
    assert registered_tool is not None
    assert registered_tool.status == ToolState.READY

    # Overwrite registered instance with mock engine tool
    mock_tool = WebResearchTool(search_engine=mock_search_engine)
    registry._instances["web_research"] = mock_tool

    # Create dummy Task
    workflow_id = uuid4()
    task = Task(
        workflow_id=workflow_id,
        task_name="Research AsyncIO",
        description="AsyncIO in Python",
        required_tool="web_research",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="Structured research results",
    )

    result = await capability.execute_task(
        task, {"query": "AsyncIO", "extract_content": False}
    )

    assert task.status == TaskStatus.COMPLETED
    assert result.total_sources_found > 0
    assert len(task.execution_logs) >= 2
