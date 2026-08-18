import pytest
from shared.contracts.memory import MemoryCategory
from shared.contracts.planner import PlannerRequest

from app.memory.conversation_memory import ConversationMemoryService
from app.memory.planner_integration import PlannerMemoryContextAdapter
from app.memory.storage import InMemoryMemoryStorage
from app.planner.chat import PlannerChatInterface
from app.planner.session import SessionManager


@pytest.fixture
def memory_service():
    return ConversationMemoryService(storage=InMemoryMemoryStorage())


@pytest.fixture
def memory_adapter(memory_service):
    return PlannerMemoryContextAdapter(memory_service)


@pytest.fixture
def chat_interface_with_memory(memory_service):
    session_manager = SessionManager()
    return PlannerChatInterface(
        session_manager=session_manager, memory_service=memory_service
    )


def test_planner_memory_context_adapter(memory_service, memory_adapter):
    session_id = "planner-session-1"

    memory_service.store_memory(
        session_id=session_id,
        role="user",
        content="Always generate PowerPoint slides in blue theme.",
        category=MemoryCategory.PREFERENCE,
        relevance_score=0.9,
    )
    memory_service.store_memory(
        session_id=session_id,
        role="user",
        content="Use at least 5 slides.",
        category=MemoryCategory.INSTRUCTION,
        relevance_score=0.85,
    )
    memory_service.store_memory(
        session_id=session_id,
        role="assistant",
        content="Decided to use Playwright for browser task.",
        category=MemoryCategory.DECISION,
        relevance_score=0.8,
    )

    context = memory_adapter.get_planner_context(session_id=session_id)

    assert "Always generate PowerPoint slides in blue theme." in context["preferences"]
    assert "Use at least 5 slides." in context["instructions"]
    assert "Decided to use Playwright for browser task." in context["decisions"]
    assert len(context["recent_history"]) == 3


def test_attach_memory_to_planner_request(memory_service, memory_adapter):
    session_id = "planner-session-2"

    memory_service.store_memory(
        session_id=session_id,
        role="user",
        content="Target audience is enterprise clients.",
        category=MemoryCategory.PROJECT_CONTEXT,
        relevance_score=0.9,
    )

    req = PlannerRequest(
        session_id=session_id,
        message="Create a sales pitch for our product.",
        context={"env": "prod"},
    )

    enriched_req = memory_adapter.attach_memory_to_planner_request(req)

    assert "conversation_memory" in enriched_req.context
    conv_mem = enriched_req.context["conversation_memory"]
    assert "Target audience is enterprise clients." in conv_mem["project_context"]

    # Verify user message was automatically stored
    stored_memories = memory_service.get_session_memories(session_id)
    assert any(
        m.content == "Create a sales pitch for our product." for m in stored_memories
    )


def test_planner_chat_interface_with_memory(chat_interface_with_memory, memory_service):
    session = chat_interface_with_memory.session_manager.create_session()
    session_id = session.session_id

    memory_service.store_memory(
        session_id=session_id,
        role="user",
        content="Prefer minimal design.",
        category=MemoryCategory.PREFERENCE,
        relevance_score=0.95,
    )

    req = PlannerRequest(
        session_id=session_id,
        message="Design a landing page draft.",
    )

    response = chat_interface_with_memory.handle_request(req)

    assert response.session_id == session_id
    assert response.status == "received"

    stored_session = chat_interface_with_memory.session_manager.get_session(session_id)
    assert stored_session is not None
    assert len(stored_session.history) == 1

    stored_req = stored_session.history[0]
    assert "conversation_memory" in stored_req.context
    assert (
        "Prefer minimal design."
        in stored_req.context["conversation_memory"]["preferences"]
    )
