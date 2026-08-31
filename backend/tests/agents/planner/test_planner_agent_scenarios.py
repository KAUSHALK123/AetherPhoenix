from unittest.mock import patch

import pytest
from shared.contracts.planner import PlannerRequest

from app.agents.planner.agent import PlannerAgent


@pytest.fixture
def planner_agent():
    return PlannerAgent()


def test_planner_normal_task_decomposition(planner_agent):
    """Test normal task decomposition for a clear, supported request."""
    request = PlannerRequest(
        session_id="session-normal-1",
        message="Create a PPT presentation summarizing sales figures.",
        context={"user_role": "admin"},
    )

    response = planner_agent.process_request(request)

    assert response.status == "ready"
    assert response.action == "execute_plan"
    assert response.reply is not None
    reply_lower = response.reply.lower()
    assert (
        "sales" in reply_lower
        or "presentation" in reply_lower
        or "tasks" in reply_lower
    )


def test_planner_multistep_task_decomposition(planner_agent):
    """Test multi-step task decomposition with dependency graph."""
    request = PlannerRequest(
        session_id="session-multistep-1",
        message="Create a PPT presentation on market trends and research topics.",
        context={},
    )

    response = planner_agent.process_request(request)

    assert response.status == "ready"
    assert response.reply is not None
    assert response.action == "execute_plan"


def test_planner_ambiguous_request(planner_agent):
    """Test ambiguous request requiring clarification."""
    request = PlannerRequest(
        session_id="session-ambiguous-1",
        message="do something vague",
        context={},
    )

    response = planner_agent.process_request(request)

    assert response.status in ("clarifying", "error")
    if response.status == "clarifying":
        assert response.action == "await_user_input"
        assert response.session_id in planner_agent.active_sessions


def test_planner_followup_request_after_clarification(planner_agent):
    """Test follow-up request after clarification restores session prompt."""
    session_id = "session-followup-1"

    # Step 1: Ambiguous initial request recorded in active sessions
    planner_agent.active_sessions[session_id] = "Create a presentation"

    # Step 2: User provides clarification response
    followup_request = PlannerRequest(
        session_id=session_id,
        message="Create a PPT presentation summarizing quarterly sales metrics.",
        context={},
    )

    response = planner_agent.process_request(followup_request)

    assert response.status == "ready"
    assert response.action == "execute_plan"
    # session cleared after completion
    assert session_id not in planner_agent.active_sessions


def test_planner_unsupported_capability(planner_agent):
    """Test request with unsupported capability fails safely with error status."""
    session_id = "session-unsupported-1"

    # Mock capability engine to return unsupported capabilities
    with patch.object(
        planner_agent.capability_engine, "discover_capabilities"
    ) as mock_discover:
        mock_discover.return_value = ([], ["quantum_computation_engine"])

        request = PlannerRequest(
            session_id=session_id,
            message="Create a PPT presentation using quantum computation modeling.",
            context={},
        )

        response = planner_agent.process_request(request)

        assert response.status == "error"
        assert "Unsupported capabilities detected" in response.reply
        assert response.action == "await_user_input"
        assert session_id not in planner_agent.active_sessions
