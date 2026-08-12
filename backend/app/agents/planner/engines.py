from typing import List
from uuid import uuid4

from shared.contracts.planner import UserRequirement
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus


class GoalExtractionEngine:
    """Mock implementation to extract a single goal from UserRequirement."""

    def extract_goal(self, requirement: UserRequirement) -> str:
        if requirement.requirements:
            return requirement.requirements[0]
        return "Unknown Goal"


class TaskDecompositionEngine:
    """Mock implementation to decompose a goal into Tasks."""

    def decompose(self, goal: str) -> List[Task]:
        return [
            Task(
                workflow_id=uuid4(),
                task_name="Mock Task",
                description=f"Initial step for: {goal}",
                category=TaskCategory.OTHER,
                required_tool="None",
                expected_output="Success",
                status=TaskStatus.CREATED,
                priority=TaskPriority.MEDIUM,
            )
        ]


class RiskAnalysisEngine:
    """Mock implementation to detect risks in tasks."""

    def analyze_risks(self, tasks: List[Task]) -> List[str]:
        return ["Data consistency risk if interrupted"]


class PermissionDetectionEngine:
    """Mock implementation to detect required permissions for tasks."""

    def detect_permissions(self, tasks: List[Task]) -> List[str]:
        return ["FILE_SYSTEM_READ", "FILE_SYSTEM_WRITE"]
