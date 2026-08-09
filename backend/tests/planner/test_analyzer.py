import pytest
from shared.contracts.planner import IntentCategory, PlannerRequest

from app.planner.analyzer import RequirementAnalyzer


@pytest.fixture
def analyzer():
    return RequirementAnalyzer()


def test_analyze_intent(analyzer):
    res = analyzer.analyze_intent("Create a new user")
    assert res == IntentCategory.SYSTEM_MODIFICATION

    res = analyzer.analyze_intent("Find the latest logs")
    assert res == IntentCategory.DATA_RETRIEVAL

    res = analyzer.analyze_intent("Write an email")
    assert res == IntentCategory.CONTENT_GENERATION

    res = analyzer.analyze_intent("Hello world")
    assert res == IntentCategory.UNKNOWN


def test_extract_requirements(analyzer):
    reqs = analyzer.extract_requirements("Build a fast website")
    assert len(reqs) == 1
    assert reqs[0] == "Build a fast website"


def test_detect_constraints(analyzer):
    constraints = analyzer.detect_constraints("Make it secure and fast")
    assert "performance: high" in constraints
    assert "security: strict" in constraints

    constraints2 = analyzer.detect_constraints("Needs to work offline")
    assert "network: offline_only" in constraints2


def test_analyze_request(analyzer):
    req = PlannerRequest(
        session_id="test-session", message="Generate a report securely offline"
    )

    user_req = analyzer.analyze_request(req)

    assert user_req.intent == IntentCategory.CONTENT_GENERATION
    assert len(user_req.requirements) == 1
    assert "security: strict" in user_req.constraints
    assert "network: offline_only" in user_req.constraints
    assert user_req.category == IntentCategory.CONTENT_GENERATION.value
