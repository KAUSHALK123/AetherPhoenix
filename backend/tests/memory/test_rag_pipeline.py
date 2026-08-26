from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from shared.contracts.planner import PlannerRequest
from shared.contracts.rag import RAGSourceType, RetrievalQuery
from shared.contracts.task import Task, TaskCategory

from app.memory.conversation_memory import ConversationMemoryService
from app.memory.rag_pipeline import (
    RAGContextBuilder,
    RAGPipelineService,
    get_rag_pipeline,
    reset_rag_pipeline,
)
from app.memory.task_history import TaskHistoryService
from app.memory.vector_db import reset_vector_db_service


@pytest.fixture
def clean_pipeline():
    """Provides a fresh RAGPipelineService instance with clean backends."""
    vector_db = reset_vector_db_service()
    conv_mem = ConversationMemoryService()
    task_hist = TaskHistoryService()
    pipeline = RAGPipelineService(
        vector_db=vector_db,
        conversation_memory=conv_mem,
        task_history=task_hist,
    )
    return pipeline


@pytest.mark.asyncio
async def test_empty_knowledge_base(clean_pipeline):
    """Verifies retrieval against empty knowledge base returns empty context."""
    res = await clean_pipeline.retrieve("What is the preferred dark mode color theme?")
    assert res.total_retrieved == 0
    assert res.items == []
    assert res.formatted_context == ""
    assert res.retrieval_metadata.get("status") == "success"


@pytest.mark.asyncio
async def test_relevant_query_retrieval(clean_pipeline):
    """Verifies storing and retrieving relevant information via semantic query."""
    m1 = uuid4()
    await clean_pipeline.vector_db.store_memory(
        memory_id=m1,
        text=(
            "The user prefers slide presentations with a dark mode glassmorphism theme."
        ),
        metadata={"category": "preference", "session_id": "session_101"},
    )

    res = await clean_pipeline.retrieve(
        query="slide presentations dark mode glassmorphism theme",
        top_k=3,
    )
    assert res.total_retrieved == 1
    assert res.items[0].source_id == str(m1)
    assert "glassmorphism theme" in res.items[0].content
    assert res.items[0].score > 0.0
    assert res.items[0].source_type == RAGSourceType.VECTOR_DB
    assert "Context Item 1" in res.formatted_context


@pytest.mark.asyncio
async def test_irrelevant_query_and_min_score_filtering(clean_pipeline):
    """Verifies irrelevant results are filtered out by min_score threshold."""
    m1 = uuid4()
    await clean_pipeline.vector_db.store_memory(
        memory_id=m1,
        text="Python backend code uses FastAPI web server.",
        metadata={"category": "tech"},
    )

    # High min_score threshold should filter out low matching items
    res = await clean_pipeline.retrieve(
        query="Quantum physics string theory research",
        min_score=0.99,
    )
    assert res.total_retrieved == 0
    assert res.items == []
    assert res.formatted_context == ""


@pytest.mark.asyncio
async def test_multiple_matching_memories_ranking(clean_pipeline):
    """Verifies ranking multiple memories in descending order of score."""
    m1 = uuid4()
    m2 = uuid4()
    m3 = uuid4()

    await clean_pipeline.vector_db.store_memory(
        m1, "I love eating authentic Italian pizza."
    )
    await clean_pipeline.vector_db.store_memory(
        m2, "My preferred dinner food is spicy Italian pepperoni pizza."
    )
    await clean_pipeline.vector_db.store_memory(
        m3, "Electric vehicles run on high capacity lithium-ion battery packs."
    )

    res = await clean_pipeline.retrieve(query="Italian pizza dinner food", top_k=5)
    assert res.total_retrieved >= 2
    scores = [item.score for item in res.items]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_retrieval_with_retrieval_query_object(clean_pipeline):
    """Verifies execution using a structured RetrievalQuery contract object."""
    m1 = uuid4()
    await clean_pipeline.vector_db.store_memory(
        m1,
        "Project uses PostgreSQL database in production environment.",
        metadata={"domain": "database"},
    )

    query_contract = RetrievalQuery(
        query_text="What database is used?",
        top_k=2,
        min_score=-1.0,
        metadata_filter={"domain": "database"},
    )

    res = await clean_pipeline.retrieve(query=query_contract)
    assert res.total_retrieved == 1
    assert "PostgreSQL" in res.items[0].content


@pytest.mark.asyncio
async def test_context_formatting():
    """Verifies context formatting logic in RAGContextBuilder."""
    from shared.contracts.rag import RetrievedContextItem

    item1 = RetrievedContextItem(
        content="User instruction: Always format output as JSON.",
        score=0.92,
        source_type=RAGSourceType.CONVERSATION_MEMORY,
        source_id="mem_abc",
        metadata={"category": "instruction"},
    )
    item2 = RetrievedContextItem(
        content="User preference: Standard font is Arial 12pt.",
        score=0.75,
        source_type=RAGSourceType.VECTOR_DB,
        source_id="mem_xyz",
        metadata={"category": "preference"},
    )

    formatted = RAGContextBuilder.build_formatted_context([item1, item2], query="test")
    assert "### Relevant Context (Retrieved Knowledge)" in formatted
    assert "Context Item 1 (Source: conversation_memory | Score: 0.920" in formatted
    assert "User instruction: Always format output as JSON." in formatted
    assert "Context Item 2 (Source: vector_db | Score: 0.750" in formatted


@pytest.mark.asyncio
async def test_agent_context_injection_planner(clean_pipeline):
    """Verifies RAG context enrichment for PlannerRequest."""
    m1 = uuid4()
    await clean_pipeline.vector_db.store_memory(
        m1, "User prefers presentations with maximum 8 slides."
    )

    req = PlannerRequest(
        session_id="session_planner_01",
        message="presentations maximum 8 slides",
    )

    enriched_req = await clean_pipeline.enrich_planner_request(
        request=req, min_score=-1.0
    )

    assert "rag_context" in enriched_req.context
    assert "retrieved_knowledge" in enriched_req.context
    assert "maximum 8 slides" in enriched_req.context["retrieved_knowledge"]


@pytest.mark.asyncio
async def test_agent_context_injection_worker(clean_pipeline):
    """Verifies RAG context enrichment for Worker Task."""
    m1 = uuid4()
    await clean_pipeline.vector_db.store_memory(
        m1, "PDF document title should be 'Quarterly Financial Analysis'."
    )

    task = Task(
        workflow_id=uuid4(),
        task_name="PDF document title Quarterly Financial Analysis",
        description="Generate PDF document for stakeholders.",
        required_tool="pdf_tool",
        category=TaskCategory.PDF_GENERATION,
        expected_output="PDF document generated.",
    )

    enriched_task = await clean_pipeline.enrich_worker_task(task=task, min_score=-1.0)

    assert "rag_context" in enriched_task.inputs
    assert "retrieved_knowledge" in enriched_task.inputs
    assert "Quarterly Financial Analysis" in enriched_task.inputs["retrieved_knowledge"]


@pytest.mark.asyncio
async def test_graceful_retrieval_failure_handling():
    """Verifies internal backend exceptions are handled gracefully."""
    mock_vector_db = AsyncMock()
    mock_vector_db.search_similar.side_effect = RuntimeError(
        "Database connection failed"
    )

    pipeline = RAGPipelineService(vector_db=mock_vector_db)
    res = await pipeline.retrieve("Test query")

    assert res.total_retrieved == 0
    assert res.items == []
    assert res.retrieval_metadata.get("status") == "error"
    err_msg = res.retrieval_metadata.get("error_message", "")
    assert "Database connection failed" in err_msg


@pytest.mark.asyncio
async def test_singleton_management():
    """Verifies global RAG pipeline singleton functions."""
    p1 = get_rag_pipeline()
    p2 = get_rag_pipeline()
    assert p1 is p2

    p3 = reset_rag_pipeline()
    assert p1 is not p3
