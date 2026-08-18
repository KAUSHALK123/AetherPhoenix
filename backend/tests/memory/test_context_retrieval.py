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
    """Verifies retrieval against empty memory returns empty context."""
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
        text="The user prefers slide design with dark mode glassmorphism.",
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
    """Verifies irrelevant results below threshold are filtered out."""
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
    """Verifies multiple items are ranked in descending order."""
    m1 = uuid4()
    m2 = uuid4()
    await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
        memory_id=m1,
        text="Low relevance note on styling details.",
        metadata={"category": "styling"},
    )
    await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
        memory_id=m2,
        text="Exact user preference: dark mode glassmorphism UI theme.",
        metadata={"category": MemoryCategory.PREFERENCE.value},
    )

    req = ContextRetrievalRequest(
        user_request="Exact user preference: dark mode glassmorphism UI theme.",
        agent_type=AgentType.PLANNER,
        max_items=5,
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.total_retrieved >= 1
    assert res.items[0].source_id == str(m2)


@pytest.mark.asyncio
async def test_context_limit_enforcement(clean_context_retrieval_service):
    """Verifies max_items constraint is strictly enforced."""
    for i in range(10):
        await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
            memory_id=uuid4(),
            text=f"Database migration configuration item number {i}",
            metadata={"category": "db"},
        )

    req = ContextRetrievalRequest(
        user_request="Database migration configuration",
        max_items=3,
    )
    res = await clean_context_retrieval_service.retrieve_context(req)

    assert res.total_retrieved == 3
    assert len(res.items) == 3


@pytest.mark.asyncio
async def test_workflow_specific_retrieval(clean_context_retrieval_service):
    """Verifies related tasks from the same workflow are retrieved."""
    w_id = uuid4()
    t1 = Task(
        workflow_id=w_id,
        task_name="Extract HTML content",
        description="Extract raw DOM text",
        category=TaskCategory.BROWSER,
        required_tool="BrowserTool",
        expected_output="HTML content",
    )
    clean_context_retrieval_service.task_history.record_task_created(t1)

    t2 = Task(
        workflow_id=w_id,
        task_name="Parse extracted text",
        description="Parse extracted DOM text into JSON",
        category=TaskCategory.CODE_GENERATION,
        required_tool="CodeTool",
        expected_output="Parsed JSON",
    )

    res = await clean_context_retrieval_service.get_context_for_worker(
        task=t2,
        session_id="sess_123",
        max_items=5,
    )

    assert res.total_retrieved >= 1
    source_ids = [item.source_id for item in res.items]
    assert str(t1.task_id) in source_ids


@pytest.mark.asyncio
async def test_agent_specific_context_weighting(
    clean_context_retrieval_service,
):
    """Verifies agent-tailored helpers apply appropriate category boosts."""
    pref_id = uuid4()
    await clean_context_retrieval_service.rag_pipeline.vector_db.store_memory(
        memory_id=pref_id,
        text="User design preference: Always use clean minimalist styles.",
        metadata={"category": MemoryCategory.PREFERENCE.value},
    )

    planner_res = await clean_context_retrieval_service.get_context_for_planner(
        user_request="clean minimalist design styles",
        max_items=5,
    )

    assert planner_res.total_retrieved >= 1
    assert planner_res.items[0].source_id == str(pref_id)


@pytest.mark.asyncio
async def test_retrieval_failure_handling(clean_context_retrieval_service):
    """Verifies unexpected errors return a safe error response."""
    mock_pipeline = AsyncMock()
    mock_pipeline.retrieve.side_effect = RuntimeError("RAG Pipeline backend crashed")

    service = ContextRetrievalService(rag_pipeline=mock_pipeline)
    req = ContextRetrievalRequest(
        user_request="Test error handling",
        agent_type=AgentType.PLANNER,
    )

    res = await service.retrieve_context(req)

    assert res.total_retrieved == 0
    assert res.items == []
    assert res.metadata.get("status") == "error"
    assert "crashed" in res.metadata.get("error_message", "")


@pytest.mark.asyncio
async def test_singleton_management():
    """Verifies singleton getter and reset functionality."""
    reset_context_retrieval_service()
    s1 = get_context_retrieval_service()
    s2 = get_context_retrieval_service()
    assert s1 is s2

    reset_context_retrieval_service()
    s3 = get_context_retrieval_service()
    assert s1 is not s3
