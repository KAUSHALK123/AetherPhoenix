"""Permission Manager module for centralized security and permission handling."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)

from app.core.events.bus import EventBus
from app.core.events.models import Event, EventType
from app.core.exceptions import PermissionDeniedException
from app.core.logging import get_logger

logger = get_logger(__name__)


class PermissionManager:
    """
    Manages security permission requests, approvals, rejections, and enforcement
    across execution workflows and runtime tools.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        auto_approve_low_risk: bool = True,
    ):
        self.event_bus = event_bus
        self.auto_approve_low_risk = auto_approve_low_risk
        self._permissions: Dict[UUID, PermissionRequest] = {}

    async def request_permission(
        self,
        workflow_id: UUID,
        permission_type: PermissionType,
        reason: str,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        task_id: Optional[UUID] = None,
    ) -> PermissionRequest:
        """
        Creates and evaluates a new permission request.

        Args:
            workflow_id: Identifier of the associated workflow.
            permission_type: Type of system permission requested.
            reason: Explanation of why permission is required.
            risk_level: Assessed security risk level.
            task_id: Optional task identifier.

        Returns:
            The created PermissionRequest object.
        """
        request = PermissionRequest(
            workflow_id=workflow_id,
            task_id=task_id,
            permission_type=permission_type,
            reason=reason,
            risk_level=risk_level,
            status=PermissionStatus.PENDING,
        )
        self._permissions[request.permission_id] = request
        logger.info(
            f"Permission requested: {permission_type} (Risk: {risk_level}) "
            f"for workflow {workflow_id}"
        )

        if self.event_bus:
            await self.event_bus.publish(
                Event(
                    event_type=EventType.PERMISSION_REQUESTED,
                    workflow_id=str(workflow_id),
                    task_id=str(task_id) if task_id else None,
                    source_component="PermissionManager",
                    payload={
                        "permission_id": str(request.permission_id),
                        "permission_type": permission_type.value,
                        "risk_level": risk_level.value,
                        "reason": reason,
                    },
                )
            )

        # Auto-approve LOW risk permissions if configured
        if self.auto_approve_low_risk and risk_level == RiskLevel.LOW:
            await self.grant_permission(request.permission_id)

        return request

    async def grant_permission(self, permission_id: UUID) -> PermissionRequest:
        """
        Grants a pending permission request.

        Args:
            permission_id: UUID of the permission request.

        Returns:
            The updated PermissionRequest object.

        Raises:
            KeyError: If permission_id is not found.
        """
        request = self._permissions.get(permission_id)
        if not request:
            raise KeyError(f"Permission request {permission_id} not found.")

        request.status = PermissionStatus.GRANTED
        request.responded_at = datetime.now(timezone.utc)
        logger.info(f"Permission granted: {request.permission_type} ({permission_id})")

        if self.event_bus:
            await self.event_bus.publish(
                Event(
                    event_type=EventType.PERMISSION_GRANTED,
                    workflow_id=str(request.workflow_id),
                    task_id=str(request.task_id) if request.task_id else None,
                    source_component="PermissionManager",
                    payload={
                        "permission_id": str(permission_id),
                        "permission_type": request.permission_type.value,
                    },
                )
            )

        return request

    async def reject_permission(self, permission_id: UUID) -> PermissionRequest:
        """
        Rejects a pending permission request.

        Args:
            permission_id: UUID of the permission request.

        Returns:
            The updated PermissionRequest object.

        Raises:
            KeyError: If permission_id is not found.
        """
        request = self._permissions.get(permission_id)
        if not request:
            raise KeyError(f"Permission request {permission_id} not found.")

        request.status = PermissionStatus.REJECTED
        request.responded_at = datetime.now(timezone.utc)
        logger.warning(
            f"Permission rejected: {request.permission_type} ({permission_id})"
        )

        if self.event_bus:
            await self.event_bus.publish(
                Event(
                    event_type=EventType.PERMISSION_REJECTED,
                    workflow_id=str(request.workflow_id),
                    task_id=str(request.task_id) if request.task_id else None,
                    source_component="PermissionManager",
                    payload={
                        "permission_id": str(permission_id),
                        "permission_type": request.permission_type.value,
                    },
                )
            )

        return request

    def check_permission(
        self, permission_type: PermissionType, workflow_id: UUID
    ) -> bool:
        """
        Checks whether a specific permission type is granted for a workflow.

        Args:
            permission_type: Type of permission to verify.
            workflow_id: Workflow identifier.

        Returns:
            True if permission is GRANTED, False otherwise.
        """
        for req in self._permissions.values():
            if (
                req.workflow_id == workflow_id
                and req.permission_type == permission_type
                and req.status == PermissionStatus.GRANTED
            ):
                return True
        return False

    def enforce_permission(
        self, permission_type: PermissionType, workflow_id: UUID
    ) -> None:
        """
        Enforces permission verification, raising PermissionDeniedException
        if not granted.

        Args:
            permission_type: Type of permission to enforce.
            workflow_id: Workflow identifier.

        Raises:
            PermissionDeniedException: If permission is not granted.
        """
        if not self.check_permission(permission_type, workflow_id):
            raise PermissionDeniedException(
                message=(
                    f"Permission '{permission_type.value}' denied "
                    f"for workflow {workflow_id}."
                ),
                details={
                    "permission_type": permission_type.value,
                    "workflow_id": str(workflow_id),
                },
            )

    def list_permissions(
        self,
        workflow_id: Optional[UUID] = None,
        status: Optional[PermissionStatus] = None,
    ) -> List[PermissionRequest]:
        """
        Lists stored permission requests filtered by workflow and/or status.

        Args:
            workflow_id: Optional workflow ID filter.
            status: Optional status filter.

        Returns:
            List of matching PermissionRequest objects.
        """
        results = list(self._permissions.values())
        if workflow_id:
            results = [req for req in results if req.workflow_id == workflow_id]
        if status:
            results = [req for req in results if req.status == status]
        return results
