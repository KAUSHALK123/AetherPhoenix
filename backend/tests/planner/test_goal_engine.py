import pytest
from app.planner.goal_engine import GoalExtractionEngine

from shared.contracts.planner import GoalExtractionResult, PlannerRequest


@pytest.fixture
def engine():
    return GoalExtractionEngine()


def test_extract_goals_single(engine):
    request = "Research quantum computing trends"
    result = engine.extract_goals(request)

    assert isinstance(result, GoalExtractionResult)
    assert result.is_valid
    assert result.primary_goal is not None
    assert result.goal_count >= 1
    assert result.confidence_score > 0.0
    assert result.primary_goal.title == "Research quantum computing trends"


def test_extract_goals_multi_subgoals(engine):
    request = "Research AI trends then create PPT presentation and save as PDF"
    result = engine.extract_goals(request)

    assert result.is_valid
    assert result.primary_goal is not None
    assert result.goal_count == 4  # Primary + 3 sub-goals
    assert len(result.primary_goal.sub_goals) == 3
    assert result.primary_goal.sub_goals[0].parent_id == result.primary_goal.goal_id
    assert any("PPT" in o for o in result.primary_goal.expected_outcomes)


def test_extract_goals_planner_request_object(engine):
    req_obj = PlannerRequest(
        session_id="test-session-123",
        message="Find log files and check system status",
        context={"env": "development"},
    )

    result = engine.extract_goals(req_obj)

    assert result.is_valid
    assert result.primary_goal is not None
    assert result.primary_goal.metadata.get("context") == {"env": "development"}


def test_extract_goals_invalid_prohibited(engine):
    result = engine.extract_goals("Hack a bank account")

    assert not result.is_valid
    assert result.primary_goal is None
    assert len(result.validation_messages) > 0
    assert any("prohibited" in m for m in result.validation_messages)


def test_extract_goals_empty_request(engine):
    result = engine.extract_goals("   ")

    assert not result.is_valid
    assert result.primary_goal is None
    assert any("cannot be empty" in m for m in result.validation_messages)
