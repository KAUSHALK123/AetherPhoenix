import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
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


class AwaitablePermissionCheck:
    def __init__(
        self,
        manager: "PermissionManager",
        request_id: str,
        timeout_seconds: float = None,
    ):
        self.manager = manager
        self.request_id = request_id
        if timeout_seconds is None:
            try:
                self.timeout_seconds = float(settings.PERMISSION_TIMEOUT_SECONDS)
            except Exception:
                self.timeout_seconds = 30.0
        else:
            self.timeout_seconds = timeout_seconds

    def __bool__(self) -> bool:
        try:
            return self.manager.validate_permission(self.request_id)
        except Exception:
            return False

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, AwaitablePermissionCheck):
            return bool(self) == bool(other)
        return bool(self) == bool(other)

    def __await__(self) -> Any:
        async def _wait():
            start_time = asyncio.get_event_loop().time()
            while True:
                req = self.manager.requests.get(self.request_id)
                if not req:
                    logger.error(f"Request {self.request_id} not found in check")
                    return False

                status_str = getattr(req.status, "value", str(req.status))
                if status_str in ("GRANTED", "APPROVED"):
                    return True
                elif status_str in ("REJECTED", "EXPIRED"):
                    return False

                # Handle expiration / timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= self.timeout_seconds:
                    logger.warning(
                        f"Permission request {self.request_id} timed out "
                        f"after {self.timeout_seconds}s"
                    )

                    if hasattr(req, "permission_id"):
                        from shared.contracts.permission import (
                            PermissionStatus as SharedPermissionStatus,
                        )

                        req.status = SharedPermissionStatus.EXPIRED
                    else:
                        req.status = PermissionStatus.EXPIRED

                    # Emit reject/expire event
                    if self.manager.event_bus:
                        from app.core.events.models import Event, EventType

                        try:
                            event = Event(
                                event_type=EventType.PERMISSION_REJECTED,
                                workflow_id=str(req.workflow_id),
                                task_id=(
                                    str(req.task_id)
                                    if getattr(req, "task_id", None)
                                    else None
                                ),
                                source_component="PermissionManager",
                                payload={
                                    "permission_id": str(
                                        getattr(req, "permission_id", self.request_id)
                                    ),
                                    "permission_type": getattr(
                                        req.permission_type,
                                        "value",
                                        str(req.permission_type),
                                    ),
                                    "reason": "Request timed out",
                                },
                            )
                            await self.manager.event_bus.publish(event)
                        except Exception as e:
                            logger.error(f"Failed to publish timeout event: {e}")
                    return False

                await asyncio.sleep(0.1)

        return _wait().__await__()


class AwaitableRequestWrapper:
    def __init__(self, request: Any, manager: Any = None, is_legacy: bool = False):
        self._request = request
        self._manager = manager
        self._is_legacy = is_legacy

    def __getattr__(self, name: str) -> Any:
        return getattr(self._request, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("_request", "_manager", "_is_legacy"):
            super().__setattr__(name, value)
        else:
            setattr(self._request, name, value)

    def __await__(self) -> Any:
        async def _await_impl():
            if self._is_legacy and self._manager:
                risk_str = getattr(self._request, "risk_level", "MEDIUM")
                risk_val = getattr(risk_str, "value", str(risk_str))

                if self._manager.event_bus:
                    from app.core.events.models import Event, EventType

                    await self._manager.event_bus.publish(
                        Event(
                            event_type=EventType.PERMISSION_REQUESTED,
                            workflow_id=str(self.workflow_id),
                            task_id=str(self.task_id) if self.task_id else None,
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

                if self._manager.auto_approve_low_risk and risk_val == "LOW":
                    await self._manager.grant_permission(self.permission_id)
            return self._request

        return _await_impl().__await__()


def make_awaitable(obj, manager=None, is_legacy=False):
    if obj is None:
        return None
    return AwaitableRequestWrapper(obj, manager=manager, is_legacy=is_legacy)


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
    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.SAFE,
        event_bus: Optional[Any] = None,
        auto_approve_low_risk: bool = True,
        *args,
        **kwargs,
    ):
        self.mode = mode
        self.event_bus = event_bus
        self.auto_approve_low_risk = auto_approve_low_risk
        self.requests: Dict[str, Any] = {}
        self._permissions = self.requests

    def set_mode(self, mode: ExecutionMode):
        self.mode = mode

    def _publish_event_sync(self, event_type: str, req: Any):
        if not self.event_bus:
            return

        req_id = str(
            getattr(req, "permission_id", None) or getattr(req, "request_id", None)
        )
        perm_type = getattr(req.permission_type, "value", str(req.permission_type))
        wf_id = str(getattr(req, "workflow_id", ""))
        t_id = str(req.task_id) if getattr(req, "task_id", None) else None

        from app.core.events.models import Event

        event = Event(
            event_type=event_type,
            workflow_id=wf_id,
            task_id=t_id,
            source_component="PermissionManager",
            payload={
                "permission_id": req_id,
                "permission_type": perm_type,
            },
        )

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self.event_bus.publish(event))
        except RuntimeError:
            pass

    def check_permission(self, *args, **kwargs) -> Any:
        """
        Dual signature check.
        Legacy: check_permission(self, permission_type, workflow_id)
        New: check_permission(self, action, permission_type)
        """
        from shared.contracts.permission import PermissionType as SharedPermissionType

        is_legacy = True
        if "action" in kwargs:
            is_legacy = False
        elif len(args) >= 1:
            first_arg = args[0]
            is_perm_enum = isinstance(
                first_arg, (PermissionType, SharedPermissionType)
            ) or (
                hasattr(first_arg, "value")
                and first_arg.__class__.__name__ == "PermissionType"
            )
            if not is_perm_enum:
                is_legacy = False

        if is_legacy:
            permission_type = (
                args[0] if len(args) > 0 else kwargs.get("permission_type")
            )
            workflow_id = args[1] if len(args) > 1 else kwargs.get("workflow_id")
            wf_id_str = str(workflow_id)
            perm_str = getattr(permission_type, "value", str(permission_type))

            for req in self.requests.values():
                if hasattr(req, "workflow_id") and hasattr(req, "permission_type"):
                    req_wf_str = str(req.workflow_id)
                    req_perm_str = getattr(
                        req.permission_type, "value", str(req.permission_type)
                    )
                    if req_wf_str == wf_id_str and req_perm_str == perm_str:
                        status_str = getattr(req.status, "value", str(req.status))
                        if status_str in ("GRANTED", "APPROVED"):
                            return True
            return False
        else:
            action = args[0] if len(args) > 0 else kwargs.get("action")
            permission_type = (
                args[1] if len(args) > 1 else kwargs.get("permission_type")
            )
            workflow_id = kwargs.get("workflow_id", "test")
            task_id = kwargs.get("task_id", "test")
            context = kwargs.get("context", {})

            # Check for duplicate pending requests
            perm_str = getattr(permission_type, "value", str(permission_type))
            for req in self.requests.values():
                if (
                    str(getattr(req, "workflow_id", "")) == str(workflow_id)
                    and str(getattr(req, "task_id", "")) == str(task_id)
                    and getattr(req.permission_type, "value", str(req.permission_type))
                    == perm_str
                    and getattr(req.status, "value", str(req.status)) == "PENDING"
                ):
                    # Check if already expired
                    if req.expires_at and datetime.now(timezone.utc) > req.expires_at:
                        if hasattr(req, "permission_id"):
                            from shared.contracts.permission import (
                                PermissionStatus as SharedPermissionStatus,
                            )

                            req.status = SharedPermissionStatus.EXPIRED
                        else:
                            req.status = PermissionStatus.EXPIRED
                        continue
                    dup_id = getattr(
                        req, "permission_id", getattr(req, "request_id", "")
                    )
                    logger.info(f"Duplicate pending permission request found: {dup_id}")
                    return AwaitablePermissionCheck(
                        self,
                        getattr(req, "permission_id", None)
                        or getattr(req, "request_id", None),
                    )

            req = self.request_permission(
                workflow_id=workflow_id,
                task_id=task_id,
                permission_type=permission_type,
                reason=f"Action: {action}",
                context=context,
            )

            # If the request is awaitable, get the underlying request
            req_id = getattr(req, "permission_id", None) or getattr(
                req, "request_id", None
            )
            if not req_id and hasattr(req, "r"):
                # Handle legacy awaitable wrapper
                req_id = getattr(req.r, "permission_id", None) or getattr(
                    req.r, "request_id", None
                )

            return AwaitablePermissionCheck(self, str(req_id))

    def request_permission(
        self,
        workflow_id: Any,
        *args,
        **kwargs,
    ) -> Any:
        """
        Dual signature request.
        Legacy: request_permission(self, workflow_id, permission_type, reason,
                                   risk_level=RiskLevel.MEDIUM, task_id=None)
        New: request_permission(self, workflow_id, task_id, permission_type,
                                reason, context=None)
        """
        from shared.contracts.permission import PermissionType as SharedPermissionType
        from shared.contracts.permission import RiskLevel as SharedRiskLevel

        is_legacy = False
        if len(args) >= 1:
            first_arg = args[0]
            if isinstance(first_arg, (PermissionType, SharedPermissionType)) or (
                hasattr(first_arg, "value")
                and first_arg.__class__.__name__ == "PermissionType"
            ):
                is_legacy = True
        if "permission_type" in kwargs and "task_id" not in kwargs and len(args) == 0:
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

            # Check duplicate
            perm_str = getattr(permission_type, "value", str(permission_type))
            for req in self.requests.values():
                if (
                    str(getattr(req, "workflow_id", "")) == str(workflow_id)
                    and getattr(req.permission_type, "value", str(req.permission_type))
                    == perm_str
                    and getattr(req.status, "value", str(req.status)) == "PENDING"
                ):
                    # Check if already expired
                    if req.expires_at and datetime.now(timezone.utc) > req.expires_at:
                        from shared.contracts.permission import (
                            PermissionStatus as SharedPermissionStatus,
                        )

                        req.status = SharedPermissionStatus.EXPIRED
                        continue
                    logger.info(
                        "Duplicate pending permission request found (legacy): "
                        f"{req.permission_id}"
                    )
                    return make_awaitable(req, manager=self, is_legacy=True)

            from shared.contracts.permission import (
                PermissionRequest as SharedPermissionRequest,
            )
            from shared.contracts.permission import (
                PermissionStatus as SharedPermissionStatus,
            )

            # Calculate expiration time
            try:
                timeout_s = float(settings.PERMISSION_TIMEOUT_SECONDS)
            except Exception:
                timeout_s = 30.0
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout_s)

            req = SharedPermissionRequest(
                workflow_id=workflow_id,
                task_id=task_id,
                permission_type=permission_type,
                reason=reason,
                risk_level=risk_level,
                status=SharedPermissionStatus.PENDING,
                expires_at=expires_at,
            )
            self.requests[req.permission_id] = req
            self.requests[str(req.permission_id)] = req

            logger.info(
                f"Permission requested (legacy): {permission_type} "
                f"for workflow {workflow_id} (Expires: {expires_at})"
            )

            return make_awaitable(req, manager=self, is_legacy=True)
        else:
            task_id = args[0] if len(args) > 0 else kwargs.get("task_id")
            permission_type = (
                args[1] if len(args) > 1 else kwargs.get("permission_type")
            )
            reason = args[2] if len(args) > 2 else kwargs.get("reason")
            context = args[3] if len(args) > 3 else kwargs.get("context")

            # Check duplicate
            perm_str = getattr(permission_type, "value", str(permission_type))
            for req in self.requests.values():
                if (
                    str(getattr(req, "workflow_id", "")) == str(workflow_id)
                    and str(getattr(req, "task_id", "")) == str(task_id)
                    and getattr(req.permission_type, "value", str(req.permission_type))
                    == perm_str
                    and getattr(req.status, "value", str(req.status)) == "PENDING"
                ):
                    # Check if already expired
                    if req.expires_at and datetime.now(timezone.utc) > req.expires_at:
                        if hasattr(req, "permission_id"):
                            from shared.contracts.permission import (
                                PermissionStatus as SharedPermissionStatus,
                            )

                            req.status = SharedPermissionStatus.EXPIRED
                        else:
                            req.status = PermissionStatus.EXPIRED
                        continue
                    dup_id = getattr(
                        req, "permission_id", getattr(req, "request_id", "")
                    )
                    logger.info(f"Duplicate pending permission request found: {dup_id}")
                    return make_awaitable(req)

            request_id = str(uuid.uuid4())

            # Calculate expiration time
            try:
                timeout_s = float(settings.PERMISSION_TIMEOUT_SECONDS)
            except Exception:
                timeout_s = 30.0
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout_s)

            req = PermissionRequest(
                request_id=request_id,
                workflow_id=str(workflow_id),
                task_id=str(task_id),
                permission_type=permission_type,
                reason=reason,
                context=context or {},
                status=PermissionStatus.PENDING,
                expires_at=expires_at,
            )
            self.requests[request_id] = req

            logger.info(
                f"Permission requested: {permission_type} "
                f"for workflow {workflow_id} (Expires: {expires_at})"
            )

            # Auto-approve based on mode
            if not PermissionPolicy.requires_approval(permission_type, self.mode):
                req.status = PermissionStatus.APPROVED

            return make_awaitable(req)

    def validate_permission(self, request_id: str) -> bool:
        req = self.requests.get(request_id)
        if not req:
            raise ValueError(f"Permission request {request_id} not found.")

        # Check if expired
        status_str = getattr(req.status, "value", str(req.status))
        if status_str == "EXPIRED":
            return False
        if status_str == "REJECTED":
            return False

        # Handle shared model
        if hasattr(req, "permission_id"):
            from shared.contracts.permission import (
                PermissionStatus as SharedPermissionStatus,
            )

            # Policy-based check using string conversion
            perm_str = getattr(req.permission_type, "value", str(req.permission_type))
            try:
                perm_enum = PermissionType(perm_str)
            except ValueError:
                # Fallback mapping
                perm_enum = PermissionType.BROWSER_ACCESS

            if PermissionPolicy.requires_approval(perm_enum, self.mode):
                return getattr(req.status, "value", str(req.status)) == "GRANTED"

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

        # Update status depending on request model type
        if hasattr(req, "permission_id"):
            from shared.contracts.permission import (
                PermissionStatus as SharedPermissionStatus,
            )

            req.status = SharedPermissionStatus.GRANTED
            try:
                req.responded_at = datetime.now(timezone.utc)
            except Exception:
                pass
            status_val = PermissionStatus.APPROVED
        else:
            req.status = PermissionStatus.APPROVED
            try:
                req.responded_at = datetime.now(timezone.utc)
            except Exception:
                pass
            status_val = PermissionStatus.APPROVED

        logger.info(
            f"Permission request {request_id} approved: {message or 'Approved'}"
        )
        from app.core.events.models import EventType

        self._publish_event_sync(EventType.PERMISSION_GRANTED, req)

        return PermissionResponse(
            request_id=request_id, status=status_val, message=message or "Approved"
        )

    def reject_permission(self, request_id: Any, message: Optional[str] = None) -> Any:
        perm_id_str = str(request_id)
        req = self.requests.get(request_id) or self.requests.get(perm_id_str)
        if not req:
            raise ValueError(f"Permission request {request_id} not found.")

        # Update status depending on request model type
        if hasattr(req, "permission_id"):
            from shared.contracts.permission import (
                PermissionStatus as SharedPermissionStatus,
            )

            req.status = SharedPermissionStatus.REJECTED
            try:
                req.responded_at = datetime.now(timezone.utc)
            except Exception:
                pass

            logger.info(
                f"Permission request {request_id} rejected (legacy): "
                f"{message or 'Rejected'}"
            )
            from app.core.events.models import EventType

            self._publish_event_sync(EventType.PERMISSION_REJECTED, req)

            async def _async_side_effects():
                return req

            class AwaitableRequestWrapper:
                def __init__(self, r):
                    self.r = r

                def __getattr__(self, name):
                    return getattr(self.r, name)

                def __await__(self):
                    return _async_side_effects().__await__()

            return AwaitableRequestWrapper(req)
        else:
            req.status = PermissionStatus.REJECTED
            try:
                req.responded_at = datetime.now(timezone.utc)
            except Exception:
                pass

            logger.info(
                f"Permission request {request_id} rejected: {message or 'Rejected'}"
            )
            from app.core.events.models import EventType

            self._publish_event_sync(EventType.PERMISSION_REJECTED, req)

            return PermissionResponse(
                request_id=str(request_id),
                status=PermissionStatus.REJECTED,
                message=message or "Rejected",
            )

    async def grant_permission(self, permission_id: Any) -> Any:
        """Legacy async grant method."""
        perm_id_str = str(permission_id)
        request = self.requests.get(permission_id) or self.requests.get(perm_id_str)
        if not request:
            raise KeyError(f"Permission request {permission_id} not found.")

        if hasattr(request, "permission_id"):
            from shared.contracts.permission import (
                PermissionStatus as SharedPermissionStatus,
            )

            request.status = SharedPermissionStatus.GRANTED
            try:
                request.responded_at = datetime.now(timezone.utc)
            except Exception:
                pass

            logger.info(f"Permission request {permission_id} granted legacy async")
            if self.event_bus:
                from app.core.events.models import Event, EventType

                await self.event_bus.publish(
                    Event(
                        event_type=EventType.PERMISSION_GRANTED,
                        workflow_id=str(request.workflow_id),
                        task_id=str(request.task_id) if request.task_id else None,
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
        """Legacy async reject method."""
        perm_id_str = str(permission_id)
        request = self.requests.get(permission_id) or self.requests.get(perm_id_str)
        if not request:
            raise KeyError(f"Permission request {permission_id} not found.")

        if hasattr(request, "permission_id"):
            from shared.contracts.permission import (
                PermissionStatus as SharedPermissionStatus,
            )

            request.status = SharedPermissionStatus.REJECTED
            try:
                request.responded_at = datetime.now(timezone.utc)
            except Exception:
                pass

            logger.warning(f"Permission request {permission_id} rejected legacy async")
            if self.event_bus:
                from app.core.events.models import Event, EventType

                await self.event_bus.publish(
                    Event(
                        event_type=EventType.PERMISSION_REJECTED,
                        workflow_id=str(request.workflow_id),
                        task_id=str(request.task_id) if request.task_id else None,
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

    # Keep async reject_permission mapping for legacy calls that await it
    async def reject_permission_async(self, permission_id: Any) -> Any:
        return await self.reject_permission_legacy(permission_id)

    def get_pending_requests(self, workflow_id: Optional[str] = None) -> List[Any]:
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
            pending = [req for req in pending if str(req.workflow_id) == wf_id_str]
        return pending

    def enforce_permission(self, permission_type: Any, workflow_id: Any) -> None:
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
                elif status_str in ("REJECTED", "PENDING", "EXPIRED"):
                    # Check policy
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
                        from app.core.exceptions import PermissionDeniedException

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

        # Not found request check policy
        try:
            perm_enum = PermissionType(perm_str)
        except ValueError:
            perm_enum = PermissionType.BROWSER_ACCESS

        if PermissionPolicy.requires_approval(perm_enum, self.mode):
            from app.core.exceptions import PermissionDeniedException

            raise PermissionDeniedException(
                message=(f"Permission '{perm_str}' denied for workflow {workflow_id}."),
                details={"permission_type": perm_str, "workflow_id": wf_id_str},
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
            ident = getattr(r, "permission_id", None) or getattr(r, "request_id", None)
            if ident not in seen:
                seen.add(ident)
                unique_results.append(r)

        if workflow_id:
            wf_id_str = str(workflow_id)
            unique_results = [
                req for req in unique_results if str(req.workflow_id) == wf_id_str
            ]
        if status:
            status_str = getattr(status, "value", str(status))
            unique_results = [
                req
                for req in unique_results
                if getattr(req.status, "value", str(req.status)) == status_str
                or (
                    status_str == "PENDING"
                    and getattr(req.status, "value", str(req.status)) == "PENDING"
                )
                or (
                    status_str == "GRANTED"
                    and getattr(req.status, "value", str(req.status)) == "APPROVED"
                )
                or (
                    status_str == "APPROVED"
                    and getattr(req.status, "value", str(req.status)) == "GRANTED"
                )
            ]
        return unique_results


_permission_manager_instance: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    global _permission_manager_instance
    if _permission_manager_instance is None:
        from app.core.events.bus import get_event_bus

        _permission_manager_instance = PermissionManager(event_bus=get_event_bus())
    return _permission_manager_instance
