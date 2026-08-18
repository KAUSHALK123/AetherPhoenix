from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from shared.contracts.context_retrieval import (
    AgentType,
    ContextRetrievalRequest,
)
from shared.contracts.memory import MemoryCategory
from shared.contracts.rag import RAGSourceType
from shared.contracts.task import Task, TaskCategory

from app.memory.context_retrieval import (
    ContextRetrievalService,
    get_context_retrieval_service,
    reset_context_retrieval_service,
)
from app.memory.conversation_memory import ConversationMemoryService
from app.memory.rag_pipeline import RAGPipelineService
from app.memory.task_history import TaskHistoryService
from app.memory.vector_db import reset_vector_db_service


@pytest.fixture
def clean_context_retrieval_service():
    """Provides a fresh ContextRetrievalService with clean memory stores."""
    vector_db = reset_vector_db_service()
    conv_mem = ConversationMemoryService()
    task_hist = TaskHistoryService()
    rag_pipeline = RAGPipelineService(
        vector_db=vector_db,
        conversation_memory=conv_mem,
        task_history=task_hist,
    )
    service = ContextRetrievalService(
        rag_pipeline=rag_pipeline,
        task_history=task_hist,
        conversation_memory=conv_mem,
    )
    return service


@pytest.mark.asyncio
async def test_empty_memory_retrieval(clean_context_retrieval_service):
    """Verifies retrieval against empty database returns structured empty context."""
    req = ContextRetrievalRequest(
        user_request="What is the preferred slide presentation theme?",
        agent_type=AgentType.PLANNER,
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.total_retrieved == 0
    assert res.items == []
    assert res.formatted_context == ""
    assert res.metadata.get("status") == "success"


@pytest.mark.asyncio
async def test_relevant_context_retrieval(clean_context_retrieval_service):
    """Verifies relevant context is retrieved for a valid user request."""
    m_id = uuid4()
    await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
        memory_id=m_id,
        text=(
            "The user prefers slide presentation design preference "
            "with dark mode glassmorphism."
        ),
        metadata={"category": MemoryCategory.PREFERENCE.value},
    )

    req = ContextRetrievalRequest(
        user_request="slide presentation design preference",
        agent_type=AgentType.PLANNER,
        max_items=3,
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.total_retrieved == 1
    assert res.items[0].source_id == str(m_id)
    assert "glassmorphism" in res.items[0].content
    assert "Context Item 1" in res.formatted_context
    assert res.items[0].source_type == RAGSourceType.VECTOR_DB


@pytest.mark.asyncio
async def test_irrelevant_context_filtering(clean_context_retrieval_service):
    """Verifies irrelevant results below min_relevance_score are filtered."""
    m_id = uuid4()
    await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
        memory_id=m_id,
        text="Python backend code relies on FastAPI.",
        metadata={"category": "tech"},
    )

    req = ContextRetrievalRequest(
        user_request="Astrophysics cosmology black holes",
        min_relevance_score=0.99,
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.total_retrieved == 0
    assert res.items == []
    assert res.formatted_context == ""


@pytest.mark.asyncio
async def test_multiple_memories_ranking(clean_context_retrieval_service):
    """Verifies retrieved items are ranked in descending relevance score."""
    m1 = uuid4()
    m2 = uuid4()

    await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
        m1, "I love authentic Italian pizza."
    )
    await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
        m2, "My preferred dinner is authentic Italian pepperoni pizza."
    )

    req = ContextRetrievalRequest(
        user_request="Italian pizza dinner preference",
        max_items=5,
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.total_retrieved >= 2
    scores = [item.score for item in res.items]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_context_limit_max_items(clean_context_retrieval_service):
    """Verifies max_items strictly caps maximum returned context items."""
    for i in range(5):
        await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
            uuid4(), f"Automated test dataset instruction item index {i}"
        )

    req = ContextRetrievalRequest(
        user_request="test dataset instruction item",
        max_items=2,
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.total_retrieved == 2
    assert len(res.items) == 2


@pytest.mark.asyncio
async def test_workflow_specific_retrieval(clean_context_retrieval_service):
    """Verifies related tasks from same workflow are retrieved into context."""
    w_id = uuid4()
    t1 = Task(
        workflow_id=w_id,
        task_name="Extract web page contents",
        description="Scrape product data from target URL",
        required_tool="browser_tool",
        category=TaskCategory.WEB_SCRAPING,
        expected_output="Product data extracted",
    )

    clean_context_retrieval_service.task_history.record_task_created(t1)
    clean_context_retrieval_service.task_history.record_task_started(t1)
    from shared.contracts.execution import ExecutionResult

    clean_context_retrieval_service.task_history.record_task_completed(
        task_id=t1.task_id,
        result=ExecutionResult(
            task_id=t1.task_id,
            workflow_id=w_id,
            success=True,
            output_summary="Successfully scraped 15 items",
        ),
    )

    req = ContextRetrievalRequest(
        workflow_id=str(w_id),
        task_name="Summarize scraped product data",
        agent_type=AgentType.WORKER,
        include_previous_tasks=True,
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.total_retrieved >= 1
    hist_items = [
        item for item in res.items if item.source_type == RAGSourceType.TASK_HISTORY
    ]
    assert len(hist_items) >= 1
    assert "Extract web page contents" in hist_items[0].content


@pytest.mark.asyncio
async def test_missing_workflow_graceful_handling(clean_context_retrieval_service):
    """Verifies retrieval proceeds cleanly when workflow_id is missing or None."""
    req = ContextRetrievalRequest(
        workflow_id=None,
        task_name="Standalone document task",
        agent_type=AgentType.GENERAL,
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.metadata.get("status") == "success"
    assert res.metadata.get("workflow_id") is None


@pytest.mark.asyncio
async def test_retrieval_failure_handling(clean_context_retrieval_service):
    """Verifies errors during retrieval return a safe error response."""
    mock_pipeline = AsyncMock()
    mock_pipeline.retrieve.side_effect = RuntimeError("RAG Pipeline backend crashed")

    service = ContextRetrievalService(rag_pipeline=mock_pipeline)
    req = ContextRetrievalRequest(user_request="Test prompt query")

    res = await service.retrieve_context(req)

    assert res.total_retrieved == 0
    assert res.items == []
    assert res.formatted_context == ""
    assert res.metadata.get("status") == "error"
    assert "RAG Pipeline backend crashed" in res.metadata.get("error_message", "")


@pytest.mark.asyncio
async def test_source_metadata_preservation(clean_context_retrieval_service):
    """Verifies returned context items contain all required source metadata."""
    m_id = uuid4()
    await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
        memory_id=m_id,
        text="Report output font must be Helvetica 11pt.",
        metadata={"category": "preference", "session_id": "session_888"},
    )

    req = ContextRetrievalRequest(
        user_request="Report output font requirement",
        session_id="session_888",
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.total_retrieved == 1
    item = res.items[0]
    assert item.source_id == str(m_id)
    assert item.source_type == RAGSourceType.VECTOR_DB
    assert item.metadata.get("category") == "preference"
    assert item.created_at is not None


@pytest.mark.asyncio
async def test_agent_specific_helpers(clean_context_retrieval_service):
    """Verifies convenience helper methods for Planner, Worker, and Healing agents."""
    m_id = uuid4()
    await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
        memory_id=m_id,
        text="User prefers executive summary section at the top of PDF.",
        metadata={"category": MemoryCategory.PREFERENCE.value},
    )

    # 1. Planner helper
    planner_res = await clean_context_retrieval_service.get_context_for_planner(
        user_request="Executive summary section PDF layout",
        max_items=3,
    )
    assert planner_res.total_retrieved >= 1
    assert planner_res.metadata.get("agent_type") == AgentType.PLANNER.value

    # 2. Worker helper
    task = Task(
        workflow_id=uuid4(),
        task_name="Executive summary section PDF layout",
        description="Build PDF report",
        required_tool="pdf_tool",
        category=TaskCategory.PDF_GENERATION,
        expected_output="PDF report generated",
    )
    worker_res = await clean_context_retrieval_service.get_context_for_worker(
        task=task,
        max_items=3,
    )
    assert worker_res.total_retrieved >= 1
    assert worker_res.metadata.get("agent_type") == AgentType.WORKER.value

    # 3. Healing helper
    healing_res = await clean_context_retrieval_service.get_context_for_healing(
        task_id=str(task.task_id),
        error_summary="PDF rendering exception",
        max_items=3,
    )
    assert healing_res.metadata.get("agent_type") == AgentType.HEALING.value


@pytest.mark.asyncio
async def test_singleton_management():
    """Verifies singleton retrieval and reset functions."""
    s1 = get_context_retrieval_service()
    s2 = get_context_retrieval_service()
    assert s1 is s2

    s3 = reset_context_retrieval_service()
    assert s1 is not s3
