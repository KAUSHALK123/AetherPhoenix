import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from shared.contracts.permission import (
    PermissionRequest as SharedPermissionRequest,
)
from shared.contracts.permission import (
    PermissionStatus as SharedPermissionStatus,
)
from shared.contracts.permission import (
    PermissionType as SharedPermissionType,
)

from app.core.logging import get_logger

from .models import ExecutionMode, PermissionResponse
from .models import PermissionRequest as ModelPermissionRequest
from .models import PermissionStatus as ModelPermissionStatus
from .models import PermissionType as ModelPermissionType
from .policies import PermissionPolicy

logger = get_logger(__name__)


class PermissionManager:
    """
    Core Permission Manager for AetherPhoenix.
    Responsible for checking, logging, validating, and granting safety permissions.
    Handles both:
    1. Shared contract models used by agents and integration tests.
    2. Specific internal models and mode policies used by the core framework.
    """

    def __init__(self, mode: ExecutionMode = ExecutionMode.SAFE) -> None:
        self.mode = mode
        self.requests: Dict[str, ModelPermissionRequest] = {}
        self._shared_requests: Dict[UUID, SharedPermissionRequest] = {}

    def set_mode(self, mode: ExecutionMode) -> None:
        """Sets the execution mode (SAFE, ASSISTED, AUTONOMOUS)."""
        self.mode = mode

    def request_permission(
        self,
        workflow_id: Any,
        task_id: Optional[str] = None,
        permission_type: Optional[ModelPermissionType] = None,
        reason: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Any:
        """
        Submits/registers a safety permission request.

        Supports two invocation forms:
        - `request_permission(SharedPermissionRequest)` for Agent-level integration.
        - `request_permission(workflow_id, task_id, type, reason, context)`
          for Core platform policy enforcement.
        """
        # 1. Handle shared contract request from agents
        if isinstance(workflow_id, SharedPermissionRequest):
            request = workflow_id
            logger.info(
                f"Shared Permission requested: ID={request.permission_id}, "
                f"Type={request.permission_type}, Workflow={request.workflow_id}, "
                f"Risk={request.risk_level}, Reason={request.reason}"
            )

            # In development/test/autonomous mode, we auto-grant pending permissions
            if request.status == SharedPermissionStatus.PENDING:
                request.status = SharedPermissionStatus.GRANTED
                request.responded_at = datetime.now(timezone.utc)
                logger.info(f"Shared Permission {request.permission_id} auto-granted.")

            self._shared_requests[request.permission_id] = request
            return request

        # 2. Handle model-based internal signature
        request_id = str(uuid.uuid4())
        req = ModelPermissionRequest(
            request_id=request_id,
            workflow_id=workflow_id,
            task_id=task_id,
            permission_type=permission_type,
            reason=reason,
            context=context or {},
        )
        self.requests[request_id] = req
        return req

    def validate_permission(self, request_id: str) -> bool:
        """
        Validates whether a permission is approved or automatically allowed.
        """
        req = self.requests.get(request_id)
        if not req:
            raise ValueError(f"Permission request {request_id} not found.")

        # If it requires explicit approval based on policy
        if PermissionPolicy.requires_approval(req.permission_type, self.mode):
            return req.status == ModelPermissionStatus.APPROVED

        # If it doesn't require approval, it's auto-approved.
        req.status = ModelPermissionStatus.APPROVED
        return True

    def approve_permission(
        self, request_id: str, message: Optional[str] = None
    ) -> PermissionResponse:
        """
        Explicitly approves a pending permission request.
        """
        req = self.requests.get(request_id)
        if not req:
            raise ValueError(f"Permission request {request_id} not found.")

        req.status = ModelPermissionStatus.APPROVED
        return PermissionResponse(
            request_id=request_id,
            status=ModelPermissionStatus.APPROVED,
            message=message,
        )

    def reject_permission(
        self, request_id: str, message: Optional[str] = None
    ) -> PermissionResponse:
        """
        Explicitly rejects a pending permission request.
        """
        req = self.requests.get(request_id)
        if not req:
            raise ValueError(f"Permission request {request_id} not found.")

        req.status = ModelPermissionStatus.REJECTED
        return PermissionResponse(
            request_id=request_id,
            status=ModelPermissionStatus.REJECTED,
            message=message,
        )

    def get_pending_requests(
        self, workflow_id: Optional[str] = None
    ) -> List[ModelPermissionRequest]:
        """
        Returns a list of pending requests, optionally filtered by workflow.
        """
        pending = [
            req
            for req in self.requests.values()
            if req.status == ModelPermissionStatus.PENDING
        ]
        if workflow_id:
            pending = [req for req in pending if req.workflow_id == workflow_id]
        return pending

    # Helper methods for Shared Contract integrations
    def check_permission(
        self, workflow_id: UUID, permission_type: SharedPermissionType
    ) -> bool:
        """
        Checks if a permission has been granted for a specific workflow
        (Shared contract).
        """
        for req in self._shared_requests.values():
            if (
                req.workflow_id == workflow_id
                and req.permission_type == permission_type
            ):
                return req.status == SharedPermissionStatus.GRANTED
        return False

    def get_request(self, permission_id: UUID) -> Optional[SharedPermissionRequest]:
        """Retrieves a shared permission request by its ID."""
        return self._shared_requests.get(permission_id)
