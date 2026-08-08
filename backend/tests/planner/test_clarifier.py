import pytest
from shared.contracts.planner import IntentCategory, UserRequirement

from app.planner.clarifier import ClarificationEngine


@pytest.fixture
def clarifier():
    return ClarificationEngine()


def test_no_clarification_needed(clarifier):
    req = UserRequirement(
        intent=IntentCategory.SYSTEM_MODIFICATION,
        requirements=["Create a user"],
        constraints=[],
    )
    result = clarifier.evaluate_requirement(req)

    assert not result.needs_clarification
    assert result.question is None
    assert len(result.missing_fields) == 0


def test_missing_intent(clarifier):
    req = UserRequirement(
        intent=IntentCategory.UNKNOWN, requirements=["Do something"], constraints=[]
    )
    result = clarifier.evaluate_requirement(req)

    assert result.needs_clarification
    assert "intent" in result.missing_fields
    assert "goal" in result.question or "action" in result.question


def test_missing_requirements(clarifier):
    req = UserRequirement(
        intent=IntentCategory.DATA_RETRIEVAL, requirements=[], constraints=[]
    )
    result = clarifier.evaluate_requirement(req)

    assert result.needs_clarification
    assert "requirements" in result.missing_fields
    assert "specify" in result.question or "exactly" in result.question


def test_missing_both(clarifier):
    req = UserRequirement(
        intent=IntentCategory.UNKNOWN, requirements=[], constraints=[]
    )
    result = clarifier.evaluate_requirement(req)

    assert result.needs_clarification
    assert "intent" in result.missing_fields
    assert "requirements" in result.missing_fields
    assert "details" in result.question
