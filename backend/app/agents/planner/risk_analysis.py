from typing import Dict, List, Set
from uuid import UUID

from shared.contracts import Task, TaskCategory
from shared.contracts.permission import RiskLevel
from shared.contracts.risk import Conflict, RiskAnalysisResult, RiskAssessment


class RiskAnalysisEngine:
    """
    Engine responsible for identifying potentially dangerous, conflicting,
    or high-impact actions before execution.
    """

    _RISK_SCORES = {
        RiskLevel.SAFE: 0,
        RiskLevel.LOW: 10,
        RiskLevel.MEDIUM: 30,
        RiskLevel.HIGH: 60,
        RiskLevel.CRITICAL: 100,
    }

    _HIGH_RISK_CATEGORIES = {
        TaskCategory.POWERSHELL: RiskLevel.HIGH,
        "REGISTRY": RiskLevel.CRITICAL,  # Some tasks might have this in permissions
    }

    _MEDIUM_RISK_CATEGORIES = {
        TaskCategory.FILE_SYSTEM: RiskLevel.MEDIUM,
        TaskCategory.GIT: RiskLevel.MEDIUM,
    }

    def analyze_tasks(self, tasks: List[Task]) -> RiskAnalysisResult:
        """
        Main entry point for risk analysis.
        Analyzes individual tasks for risks, detects conflicts between tasks,
        and aggregates safety metadata.
        """
        if not tasks:
            return RiskAnalysisResult()

        assessments: List[RiskAssessment] = []
        conflicts: List[Conflict] = []
        safety_metadata: Dict[str, List[str]] = {
            "required_permissions": [],
            "destructive_actions": [],
            "warnings": [],
        }

        highest_score = 0
        overall_risk = RiskLevel.SAFE

        # 1. Analyze Individual Tasks
        for task in tasks:
            assessment = self._assess_task(task)
            assessments.append(assessment)

            if assessment.score > highest_score:
                highest_score = assessment.score
                overall_risk = assessment.risk_level

            # Collect Safety Metadata
            for perm in task.permissions:
                if perm not in safety_metadata["required_permissions"]:
                    safety_metadata["required_permissions"].append(perm)

            if self._is_destructive(task):
                safety_metadata["destructive_actions"].append(
                    f"Task {task.task_name} might perform destructive operations."
                )

            if assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                safety_metadata["warnings"].append(
                    f"High risk task detected: {task.task_name} "
                    f"({assessment.reasoning})"
                )

        # 2. Detect Conflicts
        conflicts = self._detect_conflicts(tasks)

        # Upgrade overall risk if conflicts exist
        if conflicts:
            if highest_score < self._RISK_SCORES[RiskLevel.HIGH]:
                highest_score = self._RISK_SCORES[RiskLevel.HIGH]
                overall_risk = RiskLevel.HIGH
            safety_metadata["warnings"].append("Task conflicts detected.")

        return RiskAnalysisResult(
            assessments=assessments,
            conflicts=conflicts,
            overall_risk_level=overall_risk,
            highest_score=highest_score,
            safety_metadata=safety_metadata,
        )

    def _assess_task(self, task: Task) -> RiskAssessment:
        """
        Evaluate a single task to determine its risk level and score.
        """
        risk_level = RiskLevel.SAFE
        reasoning = "Task only involves safe operations with no side-effects."

        if task.category in [TaskCategory.PPT_GENERATION, TaskCategory.PDF_GENERATION, TaskCategory.CODE_GENERATION]:
            risk_level = RiskLevel.LOW
            reasoning = f"Task category '{task.category.value}' writes files to disk."
        elif task.category in [TaskCategory.WEB_RESEARCH, TaskCategory.SEARCH]:
            risk_level = RiskLevel.SAFE
            reasoning = f"Task category '{task.category.value}' performs safe read-only network activity."
        elif task.category == TaskCategory.BROWSER:
            risk_level = RiskLevel.LOW
            reasoning = "Task involves browser interactions."

        # Check explicit task risk level
        explicit_risk = task.risk_level.upper()
        if explicit_risk in [r.value for r in RiskLevel]:
            explicit_level = RiskLevel(explicit_risk)
            if self._RISK_SCORES[explicit_level] > self._RISK_SCORES[risk_level]:
                risk_level = explicit_level
                if risk_level == RiskLevel.LOW:
                    reasoning = "Standard operation with minimal system impact."
                elif risk_level != RiskLevel.SAFE:
                    reasoning = f"Task risk evaluated as {explicit_risk} based on initial parameters."

        # Check Category
        if risk_level in [RiskLevel.SAFE, RiskLevel.LOW]:
            if task.category in self._HIGH_RISK_CATEGORIES:
                risk_level = self._HIGH_RISK_CATEGORIES[task.category]
                reasoning = (
                    f"Task category '{task.category.value}' inherently carries a "
                    f"{risk_level.value} risk due to potential system-wide impact."
                )
            elif task.category in self._MEDIUM_RISK_CATEGORIES:
                risk_level = self._MEDIUM_RISK_CATEGORIES[task.category]
                reasoning = (
                    f"Task category '{task.category.value}' carries a "
                    f"{risk_level.value} risk because it modifies user data or files."
                )

        # Check Permissions
        high_risk_perms = ["ADMINISTRATOR", "REGISTRY", "POWERSHELL"]
        for perm in task.permissions:
            if perm.upper() in high_risk_perms:
                if (
                    self._RISK_SCORES[RiskLevel.CRITICAL]
                    > self._RISK_SCORES[risk_level]
                ):
                    risk_level = RiskLevel.CRITICAL
                    reasoning = (
                        f"Execution requires critical system permission: {perm}, "
                        "which can alter system state."
                    )
                break

        # Check Destructive operations
        if self._is_destructive(task):
            destructive_reasoning = (
                "Operation modifies filesystem contents or configuration "
                "and may cause irreversible data loss."
            )
            if self._RISK_SCORES[RiskLevel.HIGH] > self._RISK_SCORES[risk_level]:
                risk_level = RiskLevel.HIGH
                reasoning = destructive_reasoning
            else:
                reasoning += f" {destructive_reasoning}"

        return RiskAssessment(
            task_id=task.task_id,
            risk_level=risk_level,
            score=self._RISK_SCORES[risk_level],
            reasoning=reasoning,
        )

    def _is_destructive(self, task: Task) -> bool:
        """
        Heuristic to detect destructive operations based on description or tool name.
        """
        destructive_keywords = [
            "delete",
            "remove",
            "destroy",
            "drop",
            "uninstall",
            "kill",
        ]
        desc_lower = task.description.lower()
        tool_lower = task.required_tool.lower()

        for keyword in destructive_keywords:
            if keyword in desc_lower or keyword in tool_lower:
                return True
        return False

    def _detect_conflicts(self, tasks: List[Task]) -> List[Conflict]:
        """
        Detects conflicts among tasks, such as parallel modifications to the
        same resource.
        """
        conflicts: List[Conflict] = []

        # Build dependency graph
        dependents: Dict[UUID, Set[UUID]] = {t.task_id: set() for t in tasks}
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in dependents:
                    dependents[dep_id].add(task.task_id)

        # Detect parallel tasks with destructive overlapping keywords.
        # This is naive; in a real system tasks would have specific targets.
        for i, task1 in enumerate(tasks):
            for task2 in tasks[i + 1 :]:
                # Check if tasks are parallel (neither depends on the other)
                if not self._is_dependent(
                    task1.task_id, task2.task_id, dependents
                ) and not self._is_dependent(task2.task_id, task1.task_id, dependents):
                    # If both are file system operations and share keywords
                    if (
                        task1.category == TaskCategory.FILE_SYSTEM
                        and task2.category == TaskCategory.FILE_SYSTEM
                    ):
                        words1 = set(task1.description.lower().split())
                        words2 = set(task2.description.lower().split())

                        # Exclude common words
                        common_words = words1.intersection(words2) - {
                            "file",
                            "the",
                            "a",
                            "to",
                            "in",
                            "on",
                            "delete",
                            "remove",
                            "read",
                            "write",
                        }

                        if common_words and (
                            self._is_destructive(task1) or self._is_destructive(task2)
                        ):
                            conflicts.append(
                                Conflict(
                                    tasks_involved=[task1.task_id, task2.task_id],
                                    description=(
                                        "Parallel tasks might conflict over shared "
                                        f"resources: {', '.join(common_words)}"
                                    ),
                                )
                            )

        return conflicts

    def _is_dependent(
        self, task_a: UUID, task_b: UUID, dependents: Dict[UUID, Set[UUID]]
    ) -> bool:
        """
        Check if task_b is dependent on task_a (task_a must finish before task_b)
        """
        visited = set()
        stack = [task_a]
        while stack:
            current = stack.pop()
            if current == task_b:
                return True
            if current not in visited:
                visited.add(current)
                if current in dependents:
                    stack.extend(dependents[current])
        return False
