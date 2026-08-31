from shared.contracts.planner import PlannerRequest

from app.planner.session import PlannerSession, SessionManager, get_session_manager


def test_planner_session_initialization():
    """Verify session initialized with generated or provided session_id."""
    session_auto = PlannerSession()
    assert session_auto.session_id is not None
    assert isinstance(session_auto.session_id, str)
    assert len(session_auto.history) == 0
    assert len(session_auto.metadata) == 0

    custom_id = "test-session-123"
    session_custom = PlannerSession(session_id=custom_id)
    assert session_custom.session_id == custom_id


def test_planner_session_add_request():
    """Verify adding PlannerRequest updates history and metadata last_goal."""
    session = PlannerSession()
    request = PlannerRequest(
        session_id=session.session_id,
        message="Create a test report",
        context={},
    )
    session.add_request(request)
    assert len(session.history) == 1
    assert session.history[0] == request
    assert session.metadata["last_goal"] == "Create a test report"


def test_planner_session_add_turn():
    """Verify adding conversation turn manually updates history and metadata."""
    session = PlannerSession()
    session.add_turn("How do I execute this?", {"plan_id": "123"})
    assert len(session.history) == 1
    assert session.history[0] == {
        "message": "How do I execute this?",
        "plan": {"plan_id": "123"},
    }
    assert session.metadata["last_goal"] == "How do I execute this?"


def test_planner_session_get_history_dicts():
    """Verify conversion of history items to dictionaries for agents."""
    session = PlannerSession()
    request = PlannerRequest(
        session_id=session.session_id,
        message="Request message",
        context={},
    )
    session.add_request(request)
    session.add_turn("Turn message", None)

    history_dicts = session.get_history_dicts()
    assert len(history_dicts) == 2
    assert history_dicts[0] == {"message": "Request message"}
    assert history_dicts[1] == {"message": "Turn message", "plan": None}


def test_planner_session_get_context_summary():
    """Verify context summary generation containing previous goal."""
    session = PlannerSession()
    assert session.get_context_summary() == ""

    session.add_turn("Synthesize data", None)
    assert "Previous goal: Synthesize data" in session.get_context_summary()


def test_session_manager_crud():
    """Verify SessionManager session lifecycle: create, get, get_or_create."""
    manager = SessionManager()

    # Create session
    session = manager.create_session()
    assert session.session_id in manager._sessions

    # Get session
    retrieved = manager.get_session(session.session_id)
    assert retrieved == session
    assert manager.get_session("nonexistent-id") is None

    # Get or create with None
    session_new = manager.get_or_create_session(None)
    assert session_new is not None
    assert session_new.session_id in manager._sessions
    assert session_new.session_id != session.session_id

    # Get or create with existing
    session_existing = manager.get_or_create_session(session.session_id)
    assert session_existing == session

    # Get or create with nonexistent creates new
    session_nonexistent = manager.get_or_create_session("nonexistent-id")
    assert session_nonexistent is not None
    assert session_nonexistent.session_id in manager._sessions


def test_session_manager_singleton():
    """Verify get_session_manager returns the same singleton instance."""
    m1 = get_session_manager()
    m2 = get_session_manager()
    assert m1 is m2


def test_session_isolation():
    """Verify history and metadata do not leak between different sessions."""
    manager = SessionManager()
    s1 = manager.create_session()
    s2 = manager.create_session()

    s1.add_turn("Goal 1", None)
    assert len(s1.history) == 1
    assert len(s2.history) == 0

    assert s1.get_context_summary() == "Previous goal: Goal 1"
    assert s2.get_context_summary() == ""
