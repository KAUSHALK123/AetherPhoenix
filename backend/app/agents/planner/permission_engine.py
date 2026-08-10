from typing import List, Tuple

from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)
from shared.contracts.task import Task, TaskCategory


class PermissionDetectionEngine:
    """
    Engine responsible for identifying actions that require explicit user approval
    before execution. It detects permissions, tags tasks with them, and assesses risk.
    """

    def detect_permissions(
        self, tasks: List[Task]
    ) -> Tuple[List[Task], List[PermissionRequest]]:
        permission_requests = []

        for task in tasks:
            detected_permissions = set()
            detected_risk = RiskLevel.LOW

            # Analyze Category
            if task.category == TaskCategory.BROWSER:
                detected_permissions.add(PermissionType.BROWSER_ACCESS)
                detected_permissions.add(PermissionType.INTERNET)
                detected_risk = RiskLevel.MEDIUM
            elif task.category == TaskCategory.DESKTOP:
                detected_permissions.add(PermissionType.ADMINISTRATOR)
                detected_permissions.add(PermissionType.CLIPBOARD)
                detected_risk = RiskLevel.HIGH
            elif task.category == TaskCategory.FILE_SYSTEM:
                detected_permissions.add(PermissionType.FILE_SYSTEM)
                detected_risk = RiskLevel.LOW
            elif task.category == TaskCategory.POWERSHELL:
                detected_permissions.add(PermissionType.POWERSHELL)
                detected_risk = RiskLevel.HIGH
            elif task.category == TaskCategory.WEB_RESEARCH:
                detected_permissions.add(PermissionType.INTERNET)

            # Keyword-based analysis in description and name for specific
            # sensitive actions
            description_lower = (task.description or "").lower()
            name_lower = (task.task_name or "").lower()
            combined_text = f"{name_lower} {description_lower}"

            # File deletion
            if "delete" in combined_text or "remove" in combined_text:
                if task.category in [TaskCategory.FILE_SYSTEM, TaskCategory.POWERSHELL]:
                    detected_risk = RiskLevel.CRITICAL

            # Software installation
            if "install" in combined_text:
                detected_permissions.add(PermissionType.ADMINISTRATOR)
                detected_permissions.add(PermissionType.FILE_SYSTEM)
                if detected_risk not in [RiskLevel.CRITICAL]:
                    detected_risk = RiskLevel.HIGH

            # External API access or Downloads
            if "api" in combined_text or "external api" in combined_text:
                detected_permissions.add(PermissionType.INTERNET)

            if "download" in combined_text:
                if "downloads folder" not in combined_text and "downloads directory" not in combined_text:
                    if task.category != TaskCategory.FILE_SYSTEM:
                        detected_permissions.add(PermissionType.INTERNET)
                        detected_permissions.add(PermissionType.DOWNLOADS)

            # Desktop Control or System Modifications
            if "registry" in combined_text:
                detected_permissions.add(PermissionType.REGISTRY)
                detected_permissions.add(PermissionType.ADMINISTRATOR)
                detected_risk = RiskLevel.CRITICAL

            # Update the task
            task.permissions = sorted([p.value for p in detected_permissions])
            task.risk_level = detected_risk.value

            # Generate PermissionRequests for all detected permissions
            for permission in detected_permissions:
                request = PermissionRequest(
                    workflow_id=task.workflow_id,
                    task_id=task.task_id,
                    permission_type=permission,
                    reason=(
                        f"Task '{task.task_name}' requires {permission.value} "
                        "permission to execute."
                    ),
                    risk_level=detected_risk,
                    status=PermissionStatus.PENDING,
                )
                permission_requests.append(request)

        # Sort the generated requests for deterministic output in tests
        permission_requests.sort(
            key=lambda req: (str(req.task_id), req.permission_type.value)
        )

        return tasks, permission_requests
