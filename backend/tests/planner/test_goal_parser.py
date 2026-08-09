import pytest
from shared.contracts.planner import GoalPriority, IntentCategory

from app.planner.goal_parser import GoalParser


@pytest.fixture
def parser():
    return GoalParser()


def test_parse_intent(parser):
    assert (
        parser.parse_intent("Create a PowerPoint presentation")
        == IntentCategory.SYSTEM_MODIFICATION
    )
    assert parser.parse_intent("Find system logs") == IntentCategory.DATA_RETRIEVAL
    assert (
        parser.parse_intent("Write a summary report")
        == IntentCategory.CONTENT_GENERATION
    )
    assert parser.parse_intent("Hello world") == IntentCategory.UNKNOWN


def test_parse_priority(parser):
    assert parser.parse_priority("Fix WiFi ASAP") == GoalPriority.CRITICAL
    assert parser.parse_priority("Important: update settings") == GoalPriority.HIGH
    assert parser.parse_priority("Clean temp files whenever") == GoalPriority.LOW
    assert parser.parse_priority("Create presentation") == GoalPriority.MEDIUM


def test_extract_subgoal_phrases(parser):
    phrases = parser.extract_subgoal_phrases(
        "Research AI trends then create PPT slides and then export to PDF"
    )
    assert len(phrases) == 3
    assert "Research AI trends" in phrases[0]
    assert "create PPT slides" in phrases[1]
    assert "export to PDF" in phrases[2]


def test_extract_outcomes(parser):
    outcomes = parser.extract_outcomes("Create a presentation and save as PDF")
    assert any("PRESENTATION" in o or "PPT" in o for o in outcomes)
    assert any("PDF" in o for o in outcomes)


def test_parse_raw_goal_single(parser):
    title, desc, subgoals, outcomes = parser.parse_raw_goal(
        "Research Quantum Computing"
    )
    assert title == "Research Quantum Computing"
    assert desc == "Research Quantum Computing"
    assert len(subgoals) == 0
    assert len(outcomes) >= 1


def test_parse_raw_goal_multi(parser):
    title, desc, subgoals, outcomes = parser.parse_raw_goal(
        "First research quantum computing, second write summary, finally save PDF"
    )
    assert "research quantum computing" in title.lower()
    assert len(subgoals) == 3
    assert any("PDF" in o for o in outcomes)
