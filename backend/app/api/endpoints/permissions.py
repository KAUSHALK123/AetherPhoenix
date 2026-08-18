from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.permissions.manager import get_permission_manager
from app.core.permissions.models import PermissionResponse, PermissionStatus

router = APIRouter()
permission_manager = get_permission_manager()


class PermissionRequestAPIModel(BaseModel):
    request_id: str
    workflow_id: str
    task_id: Optional[str] = None
    permission_type: str
    reason: str
    risk_level: str
    status: str
    requested_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


def map_request_to_api_model(req: Any) -> PermissionRequestAPIModel:
    req_id = str(
        getattr(req, "permission_id", None) or getattr(req, "request_id", None)
    )
    wf_id = str(getattr(req, "workflow_id", ""))
    t_id = str(req.task_id) if getattr(req, "task_id", None) else None

    perm_type = getattr(req.permission_type, "value", str(req.permission_type))
    reason = getattr(req, "reason", "")
    risk_obj = getattr(req, "risk_level", "MEDIUM")
    risk_level = getattr(risk_obj, "value", str(risk_obj))
    status = getattr(req.status, "value", str(req.status))

    requested_at = getattr(req, "requested_at", None)
    expires_at = getattr(req, "expires_at", None)

    return PermissionRequestAPIModel(
        request_id=req_id,
        workflow_id=wf_id,
        task_id=t_id,
        permission_type=perm_type,
        reason=reason,
        risk_level=risk_level,
        status=status,
        requested_at=requested_at,
        expires_at=expires_at,
    )


@router.get("", response_model=List[PermissionRequestAPIModel])
async def list_permissions(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    status: Optional[PermissionStatus] = Query(None, description="Filter by status"),
):
    """
    List all permission requests.
    """
    try:
        requests = permission_manager.list_permissions(
            workflow_id=workflow_id,
            status=status,
        )
        return [map_request_to_api_model(req) for req in requests]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending", response_model=List[PermissionRequestAPIModel])
async def list_pending_permissions(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
):
    """
    List pending permission requests.
    """
    try:
        requests = permission_manager.get_pending_requests(workflow_id=workflow_id)
        return [map_request_to_api_model(req) for req in requests]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{request_id}/approve", response_model=PermissionResponse)
async def approve_permission(request_id: str, message: Optional[str] = None):
    """
    Approve a pending permission request.
    """
    try:
        req = permission_manager.requests.get(request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")

        status_str = getattr(req.status, "value", str(req.status))
        if status_str == "EXPIRED":
            raise HTTPException(
                status_code=400, detail="Permission request has expired"
            )

        res = permission_manager.approve_permission(request_id, message)
        return res
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{request_id}/reject", response_model=PermissionResponse)
async def reject_permission(request_id: str, message: Optional[str] = None):
    """
    Reject a pending permission request.
    """
    try:
        req = permission_manager.requests.get(request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")

        status_str = getattr(req.status, "value", str(req.status))
        if status_str == "EXPIRED":
            raise HTTPException(
                status_code=400, detail="Permission request has expired"
            )

        res = permission_manager.reject_permission(request_id, message)

        if not isinstance(res, PermissionResponse):
            res = PermissionResponse(
                request_id=request_id,
                status=PermissionStatus.REJECTED,
                message=message or "Rejected",
            )
        return res
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
