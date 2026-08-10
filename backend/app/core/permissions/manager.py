import uuid
from typing import Dict, List, Optional

from .models import (
    ExecutionMode,
    PermissionRequest,
    PermissionResponse,
    PermissionStatus,
    PermissionType,
)
from .policies import PermissionPolicy


class PermissionManager:
    def __init__(self, mode: ExecutionMode = ExecutionMode.SAFE):
        self.mode = mode
        self.requests: Dict[str, PermissionRequest] = {}

    def set_mode(self, mode: ExecutionMode):
        self.mode = mode

    async def check_permission(self, action: str, permission_type: PermissionType) -> bool:
        """
        Backward-compatibility method for executor testing.
        Automatically approves if safe, otherwise rejects.
        """
        req = self.request_permission(
            workflow_id="test",
            task_id="test",
            permission_type=permission_type,
            reason=f"Action: {action}"
        )
        return self.validate_permission(req.request_id)

    def request_permission(
        self,
        workflow_id: str,
        task_id: str,
        permission_type: PermissionType,
        reason: str,
        context: Optional[Dict] = None,
    ) -> PermissionRequest:
        """
        Registers a new permission request.
        """
        request_id = str(uuid.uuid4())
        req = PermissionRequest(
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
            return req.status == PermissionStatus.APPROVED

        # If it doesn't require approval, it's auto-approved.
        req.status = PermissionStatus.APPROVED
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

        req.status = PermissionStatus.APPROVED
        return PermissionResponse(
            request_id=request_id, status=PermissionStatus.APPROVED, message=message
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

        req.status = PermissionStatus.REJECTED
        return PermissionResponse(
            request_id=request_id, status=PermissionStatus.REJECTED, message=message
        )

    def get_pending_requests(
        self, workflow_id: Optional[str] = None
    ) -> List[PermissionRequest]:
        """
        Returns a list of pending requests, optionally filtered by workflow.
        """
        pending = [
            req
            for req in self.requests.values()
            if req.status == PermissionStatus.PENDING
        ]
        if workflow_id:
            pending = [req for req in pending if req.workflow_id == workflow_id]
        return pending
