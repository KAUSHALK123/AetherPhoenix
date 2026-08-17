from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from shared.contracts.permission import (
    PermissionRequest as SharedPermissionRequest,
    PermissionStatus as SharedPermissionStatus,
    PermissionType as SharedPermissionType,
    RiskLevel as SharedRiskLevel,
)

from app.core.logging import get_logger

from .models import (
    ExecutionMode,
    PermissionRequest,
    PermissionResponse,
    PermissionStatus,
    PermissionType,
)
from .policies import PermissionPolicy

logger = get_logger(__name__)


def make_awaitable(
    obj: Any, manager: Optional[Any] = None, is_legacy: bool = False
) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "__await__"):
        return obj
    orig_class = obj.__class__

    class AwaitableWrapper(orig_class):
        def __await__(self):
            async def _val():
                if is_legacy and manager:
                    risk_str = getattr(self, "risk_level", "MEDIUM")
                    risk_val = getattr(risk_str, "value", str(risk_str))

                    if manager.event_bus:
                        from app.core.events.models import Event, EventType

                        await manager.event_bus.publish(
                            Event(
                                event_type=EventType.PERMISSION_REQUESTED,
                                workflow_id=str(self.workflow_id),
                                task_id=str(self.task_id)
                                if self.task_id
                                else None,
                                source_component="PermissionManager",
                                payload={
                                    "permission_id": str(self.permission_id),
                                    "permission_type": getattr(
                                        self.permission_type,
                                        "value",
                                        str(self.permission_type),
                                    ),
                                    "risk_level": risk_val,
                                    "reason": self.reason,
                                },
                            )
                        )

                    if manager.auto_approve_low_risk and risk_val == "LOW":
                        await manager.grant_permission(self.permission_id)
                return self

            return _val().__await__()

    obj.__class__ = AwaitableWrapper
    return obj


class AwaitableBool:
    def __init__(self, value: bool):
        self.value = value

    def __bool__(self) -> bool:
        return self.value

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, AwaitableBool):
            return self.value == other.value
        return self.value == bool(other)

    def __await__(self) -> Any:
        async def _val():
            return self.value

        return _val().__await__()


class PermissionManager:
    """
    Core Permission Manager for AetherPhoenix.

    Handles both:
    1. Shared permission contracts used across agents, workflow engines, and integrations.
    2. Internal permission models and execution-mode policies.
    """

    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.SAFE,
        event_bus: Optional[Any] = None,
        auto_approve_low_risk: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.mode = mode
        self.event_bus = event_bus
        self.auto_approve_low_risk = auto_approve_low_risk
        self.requests: Dict[str, Any] = {}
        self._permissions = self.requests
        self._shared_requests = self.requests

    def set_mode(self, mode: ExecutionMode) -> None:
        """Set the execution mode (SAFE, ASSISTED, AUTONOMOUS)."""
        self.mode = mode

    def get_request(self, permission_id: Any) -> Optional[Any]:
        """Retrieve a permission request by its ID."""
        return self.requests.get(permission_id) or self.requests.get(
            str(permission_id)
        )

    def check_permission(self, *args: Any, **kwargs: Any) -> Any:
        """
        Dual signature check.
        Legacy: check_permission(self, permission_type, workflow_id)
        New: check_permission(self, action, permission_type)
        """
        is_legacy = False
        if len(args) >= 1:
            first_arg = args[0]
            if isinstance(first_arg, (PermissionType, SharedPermissionType)) or (
                hasattr(first_arg, "value")
                and first_arg.__class__.__name__ == "PermissionType"
            ):
                is_legacy = True
        if "workflow_id" in kwargs:
            is_legacy = True

        if is_legacy:
            permission_type = (
                args[0] if len(args) > 0 else kwargs.get("permission_type")
            )
            workflow_id = (
                args[1] if len(args) > 1 else kwargs.get("workflow_id")
            )
            wf_id_str = str(workflow_id)
            perm_str = getattr(permission_type, "value", str(permission_type))

            for req in self.requests.values():
                if hasattr(req, "workflow_id") and hasattr(
                    req, "permission_type"
                ):
                    req_wf_str = str(req.workflow_id)
                    req_perm_str = getattr(
                        req.permission_type, "value", str(req.permission_type)
                    )
                    if req_wf_str == wf_id_str and req_perm_str == perm_str:
                        status_str = getattr(
                            req.status, "value", str(req.status)
                        )
                        if status_str in ("GRANTED", "APPROVED"):
                            return True
            return False
        else:
            action = args[0] if len(args) > 0 else kwargs.get("action")
            permission_type = (
                args[1] if len(args) > 1 else kwargs.get("permission_type")
            )

            req = self.request_permission(
                workflow_id="test",
                task_id="test",
                permission_type=permission_type,
                reason=f"Action: {action}",
            )
            return AwaitableBool(self.validate_permission(req.request_id))

    def request_permission(
        self,
        workflow_id: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Dual signature request.
        Shared object: request_permission(self, shared_permission_request)
        Legacy: request_permission(self, workflow_id, permission_type, reason,
                                   risk_level=RiskLevel.MEDIUM, task_id=None)
        New: request_permission(self, workflow_id, task_id, permission_type,
                                reason, context=None)
        """
        if hasattr(workflow_id, "permission_id") and hasattr(
            workflow_id, "risk_level"
        ):
            req = workflow_id
            self.requests[req.permission_id] = req
            self.requests[str(req.permission_id)] = req
            return req

        is_legacy = False
        if len(args) >= 1:
            first_arg = args[0]
            if isinstance(first_arg, (PermissionType, SharedPermissionType)) or (
                hasattr(first_arg, "value")
                and first_arg.__class__.__name__ == "PermissionType"
            ):
                is_legacy = True
        if (
            "permission_type" in kwargs
            and "task_id" not in kwargs
            and len(args) == 0
        ):
            is_legacy = True
        if "risk_level" in kwargs:
            is_legacy = True

        if is_legacy:
            permission_type = (
                args[0] if len(args) > 0 else kwargs.get("permission_type")
            )
            reason = args[1] if len(args) > 1 else kwargs.get("reason")
            risk_level = (
                args[2]
                if len(args) > 2
                else kwargs.get("risk_level", SharedRiskLevel.MEDIUM)
            )
            task_id = args[3] if len(args) > 3 else kwargs.get("task_id")

            req = SharedPermissionRequest(
                workflow_id=workflow_id,
                task_id=task_id,
                permission_type=permission_type,
                reason=reason,
                risk_level=risk_level,
                status=SharedPermissionStatus.PENDING,
            )
            self.requests[req.permission_id] = req
            self.requests[str(req.permission_id)] = req

            return make_awaitable(req, manager=self, is_legacy=True)
        else:
            task_id = args[0] if len(args) > 0 else kwargs.get("task_id")
            permission_type = (
                args[1] if len(args) > 1 else kwargs.get("permission_type")
            )
            reason = args[2] if len(args) > 2 else kwargs.get("reason")
            context = args[3] if len(args) > 3 else kwargs.get("context")

            request_id = str(uuid.uuid4())
            req = PermissionRequest(
                request_id=request_id,
                workflow_id=str(workflow_id),
                task_id=str(task_id) if task_id else None,
                permission_type=permission_type,
                reason=reason,
                context=context or {},
                status=PermissionStatus.PENDING,
            )
            self.requests[request_id] = req

            # Auto-approve based on mode
            if not PermissionPolicy.requires_approval(
                permission_type, self.mode
            ):
                req.status = PermissionStatus.APPROVED

            return make_awaitable(req)

    def validate_permission(self, request_id: str) -> bool:
        req = self.requests.get(request_id)
        if not req:
            raise ValueError(f"Permission request {request_id} not found.")

        # Handle shared model
        if hasattr(req, "permission_id"):
            perm_str = getattr(
                req.permission_type, "value", str(req.permission_type)
            )
            try:
                perm_enum = PermissionType(perm_str)
            except ValueError:
                perm_enum = PermissionType.BROWSER_ACCESS

            if PermissionPolicy.requires_approval(perm_enum, self.mode):
                return (
                    getattr(req.status, "value", str(req.status)) == "GRANTED"
                )

            req.status = SharedPermissionStatus.GRANTED
            return True

        # Handle local model
        if PermissionPolicy.requires_approval(req.permission_type, self.mode):
            return req.status == PermissionStatus.APPROVED

        req.status = PermissionStatus.APPROVED
        return True

    def approve_permission(
        self, request_id: str, message: Optional[str] = None
    ) -> PermissionResponse:
        req = self.requests.get(request_id)
        if not req:
            raise ValueError(f"Permission request {request_id} not found.")

        if hasattr(req, "permission_id"):
            req.status = SharedPermissionStatus.GRANTED
            status_val = PermissionStatus.APPROVED
        else:
            req.status = PermissionStatus.APPROVED
            status_val = PermissionStatus.APPROVED

        return PermissionResponse(
            request_id=request_id,
            status=status_val,
            message=message or "Approved",
        )

    def reject_permission(
        self, request_id: Any, message: Optional[str] = None
    ) -> Any:
        perm_id_str = str(request_id)
        req = self.requests.get(request_id) or self.requests.get(perm_id_str)
        if not req:
            raise ValueError(f"Permission request {request_id} not found.")

        if hasattr(req, "permission_id"):
            req.status = SharedPermissionStatus.REJECTED
            try:
                req.responded_at = datetime.now(timezone.utc)
            except Exception:
                pass

            async def _async_side_effects():
                if self.event_bus:
                    from app.core.events.models import Event, EventType

                    await self.event_bus.publish(
                        Event(
                            event_type=EventType.PERMISSION_REJECTED,
                            workflow_id=str(req.workflow_id),
                            task_id=str(req.task_id) if req.task_id else None,
                            source_component="PermissionManager",
                            payload={
                                "permission_id": str(req.permission_id),
                                "permission_type": getattr(
                                    req.permission_type,
                                    "value",
                                    str(req.permission_type),
                                ),
                            },
                        )
                    )
                return req

            class AwaitableRequestWrapper:
                def __init__(self, r: Any) -> None:
                    self.r = r

                def __getattr__(self, name: str) -> Any:
                    return getattr(self.r, name)

                def __await__(self) -> Any:
                    return _async_side_effects().__await__()

            return AwaitableRequestWrapper(req)
        else:
            req.status = PermissionStatus.REJECTED
            return PermissionResponse(
                request_id=str(request_id),
                status=PermissionStatus.REJECTED,
                message=message or "Rejected",
            )

    async def grant_permission(self, permission_id: Any) -> Any:
        """Async grant method."""
        perm_id_str = str(permission_id)
        request = self.requests.get(permission_id) or self.requests.get(
            perm_id_str
        )
        if not request:
            raise KeyError(f"Permission request {permission_id} not found.")

        if hasattr(request, "permission_id"):
            request.status = SharedPermissionStatus.GRANTED
            try:
                request.responded_at = datetime.now(timezone.utc)
            except Exception:
                pass

            if self.event_bus:
                from app.core.events.models import Event, EventType

                await self.event_bus.publish(
                    Event(
                        event_type=EventType.PERMISSION_GRANTED,
                        workflow_id=str(request.workflow_id),
                        task_id=str(request.task_id)
                        if request.task_id
                        else None,
                        source_component="PermissionManager",
                        payload={
                            "permission_id": str(permission_id),
                            "permission_type": getattr(
                                request.permission_type,
                                "value",
                                str(request.permission_type),
                            ),
                        },
                    )
                )
        else:
            request.status = PermissionStatus.APPROVED

        return request

    async def reject_permission_legacy(self, permission_id: Any) -> Any:
        """Async reject method."""
        perm_id_str = str(permission_id)
        request = self.requests.get(permission_id) or self.requests.get(
            perm_id_str
        )
        if not request:
            raise KeyError(f"Permission request {permission_id} not found.")

        if hasattr(request, "permission_id"):
            request.status = SharedPermissionStatus.REJECTED
            try:
                request.responded_at = datetime.now(timezone.utc)
            except Exception:
                pass

            if self.event_bus:
                from app.core.events.models import Event, EventType

                await self.event_bus.publish(
                    Event(
                        event_type=EventType.PERMISSION_REJECTED,
                        workflow_id=str(request.workflow_id),
                        task_id=str(request.task_id)
                        if request.task_id
                        else None,
                        source_component="PermissionManager",
                        payload={
                            "permission_id": str(permission_id),
                            "permission_type": getattr(
                                request.permission_type,
                                "value",
                                str(request.permission_type),
                            ),
                        },
                    )
                )
        else:
            request.status = PermissionStatus.REJECTED

        return request

    async def reject_permission_async(self, permission_id: Any) -> Any:
        return await self.reject_permission_legacy(permission_id)

    def get_pending_requests(
        self, workflow_id: Optional[str] = None
    ) -> List[Any]:
        pending = []
        seen = set()
        for req in self.requests.values():
            ident = getattr(req, "permission_id", None) or getattr(
                req, "request_id", None
            )
            if ident not in seen:
                status_str = getattr(req.status, "value", str(req.status))
                if status_str == "PENDING":
                    seen.add(ident)
                    pending.append(req)

        if workflow_id:
            wf_id_str = str(workflow_id)
            pending = [
                req for req in pending if str(req.workflow_id) == wf_id_str
            ]
        return pending

    def enforce_permission(
        self, permission_type: Any, workflow_id: Any
    ) -> None:
        wf_id_str = str(workflow_id)
        perm_str = getattr(permission_type, "value", str(permission_type))

        for req in self.requests.values():
            if str(req.workflow_id) == wf_id_str and (
                getattr(req.permission_type, "value", str(req.permission_type))
                == perm_str
            ):
                status_str = getattr(req.status, "value", str(req.status))
                if status_str in ("GRANTED", "APPROVED"):
                    return
                elif status_str in ("REJECTED", "PENDING"):
                    try:
                        perm_enum = PermissionType(perm_str)
                    except ValueError:
                        perm_enum = PermissionType.BROWSER_ACCESS

                    requires_app = PermissionPolicy.requires_approval(
                        perm_enum, self.mode
                    )
                    if (
                        requires_app
                        and status_str != "GRANTED"
                        and status_str != "APPROVED"
                    ):
                        from app.core.exceptions import (
                            PermissionDeniedException,
                        )

                        raise PermissionDeniedException(
                            message=(
                                f"Permission '{perm_str}' denied "
                                f"for workflow {workflow_id}."
                            ),
                            details={
                                "permission_type": perm_str,
                                "workflow_id": wf_id_str,
                            },
                        )
                    return

        try:
            perm_enum = PermissionType(perm_str)
        except ValueError:
            perm_enum = PermissionType.BROWSER_ACCESS

        if PermissionPolicy.requires_approval(perm_enum, self.mode):
            from app.core.exceptions import PermissionDeniedException

            raise PermissionDeniedException(
                message=(
                    f"Permission '{perm_str}' denied for workflow {workflow_id}."
                ),
                details={
                    "permission_type": perm_str,
                    "workflow_id": wf_id_str,
                },
            )

    def list_permissions(
        self,
        workflow_id: Optional[Any] = None,
        status: Optional[Any] = None,
    ) -> List[Any]:
        results = list(self.requests.values())
        unique_results = []
        seen = set()
        for r in results:
            ident = getattr(r, "permission_id", None) or getattr(
                r, "request_id", None
            )
            if ident not in seen:
                seen.add(ident)
                unique_results.append(r)

        if workflow_id:
            wf_id_str = str(workflow_id)
            unique_results = [
                req
                for req in unique_results
                if str(req.workflow_id) == wf_id_str
            ]
        if status:
            status_str = getattr(status, "value", str(status))
            unique_results = [
                req
                for req in unique_results
                if getattr(req.status, "value", str(req.status)) == status_str
                or (
                    status_str == "PENDING"
                    and getattr(req.status, "value", str(req.status))
                    == "PENDING"
                )
                or (
                    status_str == "GRANTED"
                    and getattr(req.status, "value", str(req.status))
                    == "APPROVED"
                )
                or (
                    status_str == "APPROVED"
                    and getattr(req.status, "value", str(req.status))
                    == "GRANTED"
                )
            ]
        return unique_results
