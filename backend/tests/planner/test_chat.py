import pytest
from app.planner.chat import PlannerChatInterface
from app.planner.session import SessionManager

from shared.contracts.planner import PlannerRequest


@pytest.fixture
def session_manager():
    return SessionManager()


@pytest.fixture
def chat_interface(session_manager):
    return PlannerChatInterface(session_manager)


def test_session_creation(session_manager):
    # Test new session creation
    session = session_manager.create_session()
    assert session.session_id is not None
    assert len(session.history) == 0

    # Test retrieval
    retrieved = session_manager.get_session(session.session_id)
    assert retrieved == session


def test_get_or_create_session(session_manager):
    # Create new when none provided
    session1 = session_manager.get_or_create_session(None)
    assert session1 is not None

    # Retrieve existing
    session2 = session_manager.get_or_create_session(session1.session_id)
    assert session1 == session2

    # Create new when invalid ID provided
    session3 = session_manager.get_or_create_session("invalid-id")
    assert session3.session_id != "invalid-id"
    assert session3 != session1


def test_planner_chat_handle_request(chat_interface):
    req = PlannerRequest(
        session_id="new-session",
        message="Create a presentation on AI.",
        context={"user": "test"},
    )

    # Process request
    response = chat_interface.handle_request(req)

    # Verify response schema
    assert response.session_id is not None
    assert response.status == "received"
    assert response.action == "forward_to_pipeline"

    # Verify state changes
    session = chat_interface.session_manager.get_session(response.session_id)
    assert session is not None
    assert len(session.history) == 1
    assert session.history[0].message == "Create a presentation on AI."
