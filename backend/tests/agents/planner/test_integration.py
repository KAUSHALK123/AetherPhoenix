import json

import pytest
from shared.contracts.planner import PlannerRequest

from app.agents.planner.agent import PlannerAgent


@pytest.fixture
def agent():
    return PlannerAgent()


def test_clarification_flow(agent):
    # Incomplete request (unknown intent)
    req = PlannerRequest(session_id="test-session-1", message="do something")

    response = agent.process_request(req)

    # Should trigger clarification
    assert response.status == "clarifying"
    assert response.action == "await_user_input"
    assert "goal" in response.reply or "action" in response.reply


def test_end_to_end_planning_flow(agent):
    # Valid request
    req = PlannerRequest(
        session_id="test-session-2", message="Create a new user securely"
    )

    response = agent.process_request(req)

    # Should complete planning
    assert response.status == "ready"
    assert response.action == "execute_plan"

    # Assert JSON payload
    assert response.reply is not None
    plan_data = json.loads(response.reply)

    # Verify structure matches PlannerOutput
    assert "workflow_spec" in plan_data
    assert "estimated_time_seconds" in plan_data
    assert "risks" in plan_data
    assert "required_permissions" in plan_data

    # Verify mock engine integration
    assert len(plan_data["risks"]) > 0
    assert len(plan_data["required_permissions"]) > 0
