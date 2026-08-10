import logging
from uuid import UUID

from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
)

logger = logging.getLogger(__name__)


class PermissionManager:
    """Stub for Permission Manager to handle permission workflows."""

    async def request_permission(self, request: PermissionRequest) -> PermissionRequest:
        logger.info(
            f"Automatically granting permission request {request.permission_type}"
        )
        request.status = PermissionStatus.GRANTED
        return request

    async def check_permission(
        self, workflow_id: UUID, permission_type: PermissionType
    ) -> bool:
        logger.info(
            f"Automatically returning True for check_permission "
            f"{permission_type} on {workflow_id}"
        )
        return True

    def is_granted(self, permission_id: UUID) -> bool:
        return True
