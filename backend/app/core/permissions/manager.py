import uuid
from typing import Any, Dict, List, Optional

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

    async def check_permission(
        self, action: str, permission_type: PermissionType
    ) -> bool:
        """
        Backward-compatibility method for executor testing.
        Automatically approves if safe, otherwise rejects.
        """
        req = self.request_permission(
            workflow_id="test",
            task_id="test",
            permission_type=permission_type,
            reason=f"Action: {action}",
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

    def enforce_permission(self, permission_type: Any, workflow_id: Any) -> None:
        """
        Enforces permission verification, raising PermissionDeniedException
        if not granted.
        """
        wf_id_str = str(workflow_id)
        for req in self.requests.values():
            if req.workflow_id == wf_id_str and (
                req.permission_type == permission_type
                or str(req.permission_type) == str(permission_type)
            ):
                if req.status == PermissionStatus.APPROVED:
                    return
                elif req.status in (
                    PermissionStatus.REJECTED,
                    PermissionStatus.PENDING,
                ):
                    perm_str = getattr(permission_type, "value", str(permission_type))
                    requires_app = PermissionPolicy.requires_approval(
                        req.permission_type, self.mode
                    )
                    if requires_app and req.status != PermissionStatus.APPROVED:
                        from app.core.exceptions import PermissionDeniedException

                        raise PermissionDeniedException(
                            message=(
                                f"Permission '{perm_str}' denied for "
                                f"workflow {workflow_id}."
                            ),
                            details={
                                "permission_type": perm_str,
                                "workflow_id": wf_id_str,
                            },
                        )
                    return

        perm_enum = permission_type
        if isinstance(permission_type, str):
            try:
                perm_enum = PermissionType(permission_type)
            except ValueError:
                pass

        perm_str = getattr(permission_type, "value", str(permission_type))
        if PermissionPolicy.requires_approval(perm_enum, self.mode):
            from app.core.exceptions import PermissionDeniedException

            raise PermissionDeniedException(
                message=(
                    f"Permission '{perm_str}' not granted for "
                    f"workflow {workflow_id}."
                ),
                details={"permission_type": perm_str, "workflow_id": wf_id_str},
            )

