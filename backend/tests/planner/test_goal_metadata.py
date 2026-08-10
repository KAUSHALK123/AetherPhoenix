import pytest
from shared.contracts.planner import Goal, IntentCategory

from app.planner.goal_metadata import GoalMetadataGenerator


@pytest.fixture
def metadata_gen():
    return GoalMetadataGenerator()


def test_compute_confidence_score(metadata_gen):
    goal = Goal(
        title="Generate report",
        description="Detailed description for generating a report",
        category=IntentCategory.CONTENT_GENERATION,
        expected_outcomes=["Report PDF"],
    )
    score = metadata_gen.compute_confidence_score(goal)
    assert score >= 0.7


def test_detect_domain_tags(metadata_gen):
    tags = metadata_gen.detect_domain_tags(
        "Create a PPT presentation for browser search"
    )
    assert "content" in tags
    assert "browser" in tags


def test_estimate_risk_level(metadata_gen):
    safe_goal = Goal(title="Read file", description="Read text file")
    assert metadata_gen.estimate_risk_level(safe_goal) == "safe"

    critical_goal = Goal(
        title="Update registry key", description="Modify system registry"
    )
    assert metadata_gen.estimate_risk_level(critical_goal) == "critical"


def test_enrich_goal(metadata_gen):
    root = Goal(
        title="Root Goal",
        description="Root Goal Description",
        category=IntentCategory.SYSTEM_MODIFICATION,
    )
    child = Goal(
        title="Child Goal",
        description="Child Goal Description",
        category=IntentCategory.DATA_RETRIEVAL,
    )
    root.sub_goals.append(child)

    enriched = metadata_gen.enrich_goal(root)
    assert "created_at" in enriched.metadata
    assert "confidence_score" in enriched.metadata
    assert "created_at" in enriched.sub_goals[0].metadata
