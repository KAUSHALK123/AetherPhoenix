import pytest
from app.planner.goal_validator import GoalValidator

from shared.contracts.planner import Goal, IntentCategory


@pytest.fixture
def validator():
    return GoalValidator()


def test_validate_raw_request_valid(validator):
    is_valid, errors = validator.validate_raw_request(
        "Research AI developments and make a presentation"
    )
    assert is_valid
    assert len(errors) == 0


def test_validate_raw_request_empty(validator):
    is_valid, errors = validator.validate_raw_request("   ")
    assert not is_valid
    assert any("cannot be empty" in e for e in errors)


def test_validate_raw_request_short(validator):
    is_valid, errors = validator.validate_raw_request("hi")
    assert not is_valid
    assert any("too short" in e for e in errors)


def test_validate_raw_request_prohibited(validator):
    is_valid, errors = validator.validate_raw_request("Hack a bank and transfer money")
    assert not is_valid
    assert any("prohibited" in e for e in errors)


def test_validate_raw_request_vague(validator):
    is_valid, errors = validator.validate_raw_request("do something")
    assert not is_valid
    assert any("ambiguous" in e for e in errors)


def test_validate_goal_node(validator):
    valid_goal = Goal(
        title="Valid Goal",
        description="Valid Description",
        category=IntentCategory.DATA_RETRIEVAL,
    )
    is_valid, errors = validator.validate_goal_node(valid_goal)
    assert is_valid
    assert len(errors) == 0

    invalid_goal = Goal(title="", description="Valid Description")
    is_valid, errors = validator.validate_goal_node(invalid_goal)
    assert not is_valid
    assert any("title cannot be empty" in e for e in errors)


def test_validate_hierarchy(validator):
    root = Goal(title="Root Goal", description="Root Desc")
    child = Goal(title="Child Goal", description="Child Desc", parent_id=root.goal_id)
    root.sub_goals.append(child)

    is_valid, errors = validator.validate_hierarchy(root)
    assert is_valid
    assert len(errors) == 0
