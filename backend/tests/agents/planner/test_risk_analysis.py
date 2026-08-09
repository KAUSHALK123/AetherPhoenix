from uuid import uuid4

import pytest
from shared.contracts import Task, TaskCategory, TaskPriority
from shared.contracts.permission import RiskLevel

from app.agents.planner.risk_analysis import RiskAnalysisEngine


@pytest.fixture
def risk_engine():
    return RiskAnalysisEngine()


def _create_task(
    name="Test Task",
    category=TaskCategory.OTHER,
    description="Safe task",
    permissions=None,
    deps=None,
    tool="test_tool",
):
    return Task(
        task_id=uuid4(),
        workflow_id=uuid4(),
        task_name=name,
        description=description,
        required_tool=tool,
        category=category,
        priority=TaskPriority.MEDIUM,
        expected_output="done",
        permissions=permissions or [],
        dependencies=deps or [],
    )


def test_safe_plan(risk_engine):
    t1 = _create_task(
        category=TaskCategory.WEB_RESEARCH, description="Search the web for info"
    )
    t1.risk_level = "SAFE"
    t2 = _create_task(category=TaskCategory.OTHER, description="Summarize text")
    t2.risk_level = "SAFE"

    result = risk_engine.analyze_tasks([t1, t2])

    assert result.overall_risk_level == RiskLevel.SAFE
    assert len(result.conflicts) == 0
    assert result.highest_score == 0
    assert all(a.risk_level == RiskLevel.SAFE for a in result.assessments)


def test_high_risk_category(risk_engine):
    t1 = _create_task(category=TaskCategory.POWERSHELL, description="Run a script")

    result = risk_engine.analyze_tasks([t1])

    assert result.overall_risk_level == RiskLevel.HIGH
    assert result.highest_score == 60


def test_critical_permission(risk_engine):
    t1 = _create_task(permissions=["ADMINISTRATOR"])

    result = risk_engine.analyze_tasks([t1])

    assert result.overall_risk_level == RiskLevel.CRITICAL
    assert result.highest_score == 100
    assert "ADMINISTRATOR" in result.safety_metadata["required_permissions"]


def test_destructive_operations(risk_engine):
    t1 = _create_task(description="Delete all temporary files")

    result = risk_engine.analyze_tasks([t1])

    assert result.overall_risk_level == RiskLevel.HIGH
    assert len(result.safety_metadata["destructive_actions"]) == 1


def test_conflict_detection(risk_engine):
    # Two tasks operating on the file system with similar keywords and no dependencies
    t1 = _create_task(
        category=TaskCategory.FILE_SYSTEM, description="Delete the file log.txt"
    )
    t2 = _create_task(
        category=TaskCategory.FILE_SYSTEM, description="Read the file log.txt"
    )

    result = risk_engine.analyze_tasks([t1, t2])

    assert len(result.conflicts) == 1
    assert "log.txt" in result.conflicts[0].description
    assert result.overall_risk_level == RiskLevel.HIGH
    assert "Task conflicts detected." in result.safety_metadata["warnings"]


def test_no_conflict_if_dependent(risk_engine):
    t1 = _create_task(
        category=TaskCategory.FILE_SYSTEM, description="Delete the file log.txt"
    )
    t2 = _create_task(
        category=TaskCategory.FILE_SYSTEM,
        description="Read the file log.txt",
        deps=[t1.task_id],
    )

    result = risk_engine.analyze_tasks([t1, t2])

    # Dependent tasks aren't considered parallel conflicts in this simplified engine
    assert len(result.conflicts) == 0
