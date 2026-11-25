from uuid import uuid4
import pytest

from shared.contracts.execution import ExecutionResult
from shared.contracts.planner import PlannerRequest
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.tool import ToolState

from app.agents.planner.agent import PlannerAgent
from app.agents.supervisor.failure_detector import FailureDetectorService
from app.engine.validator import OutputValidationService
from app.tools.registry import ToolRegistry
from app.tools.web_research import register_web_research_tool
from app.tools.web_research.adapter import WebResearchToolAdapter
from app.tools.web_research.schemas import SourceMetadata, SourceStatus
from app.tools.web_research.search import MockSearchEngine
from app.tools.web_research.tool import WebResearchTool


@pytest.fixture
def mock_edge_ai_sources():
    return [
        SourceMetadata(
            url="https://example.com/edge-ai-trends-2026",
            title="Key Edge AI Trends Transforming Industry in 2026",
            snippet="On-device NPU acceleration, quantized model inference, and hybrid edge-cloud topologies are dominating modern deployments.",
            domain="example.com",
            status=SourceStatus.SUCCESS,
        ),
        SourceMetadata(
            url="https://tech-insights.org/edge-ai-intelligence",
            title="Edge AI Trends and Architecture for Low Latency Applications",
            snippet="Deploying localized LLMs directly onto constrained gateway devices enables privacy-compliant real-time decisions.",
            domain="tech-insights.org",
            status=SourceStatus.SUCCESS,
        ),
        SourceMetadata(
            url="https://research.ai/edge-ai-computing",
            title="The Evolution of Edge AI Computing and Embedded AI",
            snippet="Autonomous systems leverage edge vision transformers for split-second inference without round-trip cloud latency.",
            domain="research.ai",
            status=SourceStatus.SUCCESS,
        ),
    ]


@pytest.mark.asyncio
async def test_planner_decomposes_research_goal_to_web_research_tool():
    """Verify planner routes 'research the latest trends in edge AI and summarize' to web_research_tool."""
    planner = PlannerAgent()
    req = PlannerRequest(
        session_id=str(uuid4()),
        message="research the latest trends in edge AI and summarize",
    )
    res = planner.process_request(req)

    assert res.status == "ready"
    assert res.action == "execute_plan"

    import json
    plan_data = json.loads(res.reply)
    leaf_tasks = [t for t in plan_data["tasks"] if t.get("required_tool")]
    assert len(leaf_tasks) >= 1
    assert leaf_tasks[0]["required_tool"] in ("web_research_tool", "web_research")
    assert leaf_tasks[0]["category"].lower() == "web_research"


@pytest.mark.asyncio
async def test_research_workflow_synthesizes_with_sources(mock_edge_ai_sources):
    """Verify research workflow executes search, extracts, and synthesizes answer with >= 2 sources."""
    mock_engine = MockSearchEngine(mock_results=mock_edge_ai_sources)
    tool = WebResearchTool(search_engine=mock_engine)
    adapter = WebResearchToolAdapter(tool=tool)

    workflow_id = uuid4()
    task = Task(
        workflow_id=workflow_id,
        task_name="Web Research & Sourced Synthesis: Edge AI",
        description="Research the latest trends in edge AI and summarize",
        required_tool="web_research_tool",
        category=TaskCategory.WEB_RESEARCH,
        inputs={"query": "edge AI trends", "max_results": 3, "extract_content": False},
        expected_output="Structured research summary with source citations",
    )

    result = await adapter.execute(task)

    assert result.success is True
    assert "summary" in result.output
    assert "chat_reply" in result.output
    summary = result.output["summary"]

    # Verify structured answer and citations
    assert "Research Summary" in summary
    assert "Sources Consulted" in summary
    assert "https://example.com/edge-ai-trends-2026" in summary
    assert "https://tech-insights.org/edge-ai-intelligence" in summary
    assert len(result.output["sources"]) >= 2


@pytest.mark.asyncio
async def test_research_fails_honestly_when_insufficient_sources():
    """Verify research task fails honestly without faking results when fewer than 2 sources are found."""
    single_source = [
        SourceMetadata(
            url="https://isolated-source.org/ai",
            title="Isolated AI",
            snippet="Only one source available",
            domain="isolated-source.org",
            status=SourceStatus.SUCCESS,
        )
    ]
    mock_engine = MockSearchEngine(mock_results=single_source)
    tool = WebResearchTool(search_engine=mock_engine)
    adapter = WebResearchToolAdapter(tool=tool)

    workflow_id = uuid4()
    task = Task(
        workflow_id=workflow_id,
        task_name="Research Obscure Topic",
        description="Research obscure topic",
        required_tool="web_research_tool",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="Structured research summary",
        inputs={"query": "obscure topic", "max_results": 1, "extract_content": False},
    )

    result = await adapter.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "INSUFFICIENT_SOURCES"
    assert "fewer than 2" in result.output["summary"].lower()


def test_supervisor_validates_research_contract(mock_edge_ai_sources):
    """Verify OutputValidationService and FailureDetectorService accept valid research outputs."""
    validator = OutputValidationService()
    fd = FailureDetectorService()

    workflow_id = uuid4()
    task = Task(
        workflow_id=workflow_id,
        task_name="Web Research & Sourced Synthesis",
        description="Synthesize research",
        required_tool="web_research_tool",
        category=TaskCategory.WEB_RESEARCH,
        expected_output="Structured research summary with source citations",
    )

    exec_result = ExecutionResult(
        task_id=task.task_id,
        workflow_id=workflow_id,
        success=True,
        output={
            "query": "edge AI trends",
            "summary": "This is a detailed research summary covering edge AI trends across the industry.",
            "chat_reply": "This is a detailed research summary covering edge AI trends across the industry.",
            "sources": [s.model_dump() for s in mock_edge_ai_sources],
        },
    )

    is_valid, checks, issues = validator.validate(task, exec_result)
    assert is_valid is True, f"Output validation failed: {issues}"

    is_missing = fd._is_output_missing(task, exec_result)
    assert is_missing is False, "FailureDetector incorrectly flagged valid research output as missing"
