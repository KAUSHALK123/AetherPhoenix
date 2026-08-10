from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
)

from app.core.logging import get_logger

logger = get_logger(__name__)


class PermissionManager:
    """
    Core Permission Manager for AetherPhoenix.
    Responsible for checking, logging, and granting security permissions
    requested by agents or tools.
    """

    def __init__(self) -> None:
        self._requests: Dict[UUID, PermissionRequest] = {}

    def request_permission(self, request: PermissionRequest) -> PermissionRequest:
        """
        Processes a permission request.
        For V1/development, logs request and automatically grants permissions
        unless explicitly rejected.
        """
        logger.info(
            f"Permission requested: ID={request.permission_id}, "
            f"Type={request.permission_type}, Workflow={request.workflow_id}, "
            f"Risk={request.risk_level}, Reason={request.reason}"
        )

        # In development/test environment, we auto-grant pending permissions
        if request.status == PermissionStatus.PENDING:
            request.status = PermissionStatus.GRANTED
            request.responded_at = datetime.now(timezone.utc)
            logger.info(f"Permission {request.permission_id} auto-granted.")

        self._requests[request.permission_id] = request
        return request

    def check_permission(
        self, workflow_id: UUID, permission_type: PermissionType
    ) -> bool:
        """
        Checks if a permission has been granted for a specific workflow.
        Returns True if granted, False otherwise.
        """
        for req in self._requests.values():
            if (
                req.workflow_id == workflow_id
                and req.permission_type == permission_type
            ):
                return req.status == PermissionStatus.GRANTED
        return False

    def get_request(self, permission_id: UUID) -> Optional[PermissionRequest]:
        """Retrieves a permission request by its ID."""
        return self._requests.get(permission_id)
