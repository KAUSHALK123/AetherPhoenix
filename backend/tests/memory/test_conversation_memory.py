from datetime import datetime

import pytest
from shared.contracts.memory import (
    MemoryCategory,
    sanitize_memory_content,
    sanitize_memory_metadata,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.memory.conversation_memory import ConversationMemoryService
from app.memory.storage import InMemoryMemoryStorage, SQLAlchemyMemoryStorage


@pytest.fixture
def in_memory_service():
    storage = InMemoryMemoryStorage()
    return ConversationMemoryService(storage=storage)


@pytest.fixture
def sqlite_service():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    storage = SQLAlchemyMemoryStorage(db_session=db_session)
    service = ConversationMemoryService(storage=storage)
    yield service
    db_session.close()


@pytest.mark.parametrize("service_fixture", ["in_memory_service", "sqlite_service"])
def test_store_and_retrieve_memory(request, service_fixture):
    service: ConversationMemoryService = request.getfixturevalue(service_fixture)

    entry = service.store_memory(
        session_id="session-101",
        role="user",
        content="Prefer dark theme and blue color palette.",
        category=MemoryCategory.PREFERENCE,
        relevance_score=0.9,
        metadata={"ui_preference": True},
    )

    assert entry.memory_id is not None
    assert entry.session_id == "session-101"
    assert entry.role == "user"
    assert entry.content == "Prefer dark theme and blue color palette."
    assert entry.category == MemoryCategory.PREFERENCE
    assert entry.relevance_score == 0.9
    assert entry.metadata.get("ui_preference") is True
    assert isinstance(entry.created_at, datetime)
    assert isinstance(entry.updated_at, datetime)

    # Retrieve by ID
    retrieved = service.get_memory(entry.memory_id)
    assert retrieved is not None
    assert retrieved.memory_id == entry.memory_id
    assert retrieved.content == entry.content


@pytest.mark.parametrize("service_fixture", ["in_memory_service", "sqlite_service"])
def test_retrieve_by_session(request, service_fixture):
    service: ConversationMemoryService = request.getfixturevalue(service_fixture)

    service.store_memory(
        "sess-A", "user", "Message 1", category=MemoryCategory.GENERAL_CHAT
    )
    service.store_memory(
        "sess-A", "assistant", "Response 1", category=MemoryCategory.GENERAL_CHAT
    )
    service.store_memory(
        "sess-B", "user", "Other Session Message", category=MemoryCategory.GENERAL_CHAT
    )

    session_a_memories = service.get_session_memories("sess-A")
    assert len(session_a_memories) == 2
    assert session_a_memories[0].content == "Message 1"
    assert session_a_memories[1].content == "Response 1"

    session_b_memories = service.get_session_memories("sess-B")
    assert len(session_b_memories) == 1
    assert session_b_memories[0].content == "Other Session Message"


@pytest.mark.parametrize("service_fixture", ["in_memory_service", "sqlite_service"])
def test_empty_memory_retrieval(request, service_fixture):
    service: ConversationMemoryService = request.getfixturevalue(service_fixture)

    # Non-existent session
    memories = service.get_session_memories("non-existent-session")
    assert memories == []

    # Non-existent search criteria
    relevant = service.get_relevant_memories(
        session_id="non-existent-session", min_relevance=0.8
    )
    assert relevant == []


@pytest.mark.parametrize("service_fixture", ["in_memory_service", "sqlite_service"])
def test_invalid_memory_id_handling(request, service_fixture):
    service: ConversationMemoryService = request.getfixturevalue(service_fixture)

    assert service.get_memory("invalid-id-xyz") is None
    assert service.get_memory("") is None
    assert service.update_memory("invalid-id-xyz", {"content": "New content"}) is None
    assert service.delete_memory("invalid-id-xyz") is False


@pytest.mark.parametrize("service_fixture", ["in_memory_service", "sqlite_service"])
def test_update_memory(request, service_fixture):
    service: ConversationMemoryService = request.getfixturevalue(service_fixture)

    entry = service.store_memory(
        session_id="sess-update",
        role="user",
        content="Original instruction",
        category=MemoryCategory.INSTRUCTION,
        relevance_score=0.5,
        metadata={"version": 1},
    )

    updated = service.update_memory(
        entry.memory_id,
        {
            "content": "Updated instruction",
            "relevance_score": 0.95,
            "category": MemoryCategory.DECISION,
            "metadata": {"version": 2, "approved": True},
        },
    )

    assert updated is not None
    assert updated.memory_id == entry.memory_id
    assert updated.content == "Updated instruction"
    assert updated.relevance_score == 0.95
    assert updated.category == MemoryCategory.DECISION
    assert updated.metadata.get("version") == 2
    assert updated.metadata.get("approved") is True

    # Check persistence
    fetched = service.get_memory(entry.memory_id)
    assert fetched.content == "Updated instruction"


@pytest.mark.parametrize("service_fixture", ["in_memory_service", "sqlite_service"])
def test_delete_memory(request, service_fixture):
    service: ConversationMemoryService = request.getfixturevalue(service_fixture)

    entry = service.store_memory("sess-del", "user", "Delete me")

    assert service.get_memory(entry.memory_id) is not None

    deleted = service.delete_memory(entry.memory_id)
    assert deleted is True

    assert service.get_memory(entry.memory_id) is None


@pytest.mark.parametrize("service_fixture", ["in_memory_service", "sqlite_service"])
def test_clear_session_memories(request, service_fixture):
    service: ConversationMemoryService = request.getfixturevalue(service_fixture)

    service.store_memory("sess-clear", "user", "Msg 1")
    service.store_memory("sess-clear", "assistant", "Msg 2")
    service.store_memory("sess-clear", "user", "Msg 3")

    assert len(service.get_session_memories("sess-clear")) == 3

    cleared_count = service.clear_session_memories("sess-clear")
    assert cleared_count == 3
    assert len(service.get_session_memories("sess-clear")) == 0


@pytest.mark.parametrize("service_fixture", ["in_memory_service", "sqlite_service"])
def test_relevance_filtering(request, service_fixture):
    service: ConversationMemoryService = request.getfixturevalue(service_fixture)

    service.store_memory(
        "sess-rel",
        "user",
        "High priority instruction",
        category=MemoryCategory.INSTRUCTION,
        relevance_score=0.9,
    )
    service.store_memory(
        "sess-rel",
        "user",
        "Low priority note",
        category=MemoryCategory.GENERAL_CHAT,
        relevance_score=0.2,
    )
    service.store_memory(
        "sess-rel",
        "user",
        "Medium priority decision",
        category=MemoryCategory.DECISION,
        relevance_score=0.6,
    )

    high_rel = service.get_relevant_memories(session_id="sess-rel", min_relevance=0.7)
    assert len(high_rel) == 1
    assert high_rel[0].content == "High priority instruction"

    decisions = service.get_relevant_memories(
        session_id="sess-rel", category=MemoryCategory.DECISION
    )
    assert len(decisions) == 1
    assert decisions[0].content == "Medium priority decision"


def test_sensitive_data_sanitization():
    raw_content = (
        "Connect using api_key='sk-1234567890123456789012345' "
        "and password='secret_pass_123'"
    )
    sanitized = sanitize_memory_content(raw_content)
    assert "sk-1234567890123456789012345" not in sanitized
    assert "secret_pass_123" not in sanitized
    assert "[REDACTED]" in sanitized

    raw_metadata = {
        "password": "my_password",
        "api_key": "sk-key",
        "normal_key": "safe_value",
    }
    sanitized_meta = sanitize_memory_metadata(raw_metadata)
    assert sanitized_meta["password"] == "[REDACTED]"
    assert sanitized_meta["api_key"] == "[REDACTED]"
    assert sanitized_meta["normal_key"] == "safe_value"
