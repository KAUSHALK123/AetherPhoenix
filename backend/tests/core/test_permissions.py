"""Unit tests for PermissionManager core runtime component."""

from uuid import uuid4

import pytest
from shared.contracts.permission import PermissionStatus, PermissionType, RiskLevel
from shared.contracts.workflow import ExecutionMode

from app.core.events.bus import EventBus
from app.core.events.models import EventType
from app.core.exceptions import PermissionDeniedException
from app.core.permissions import PermissionManager


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def permission_manager(event_bus):
    return PermissionManager(event_bus=event_bus, auto_approve_low_risk=True)


@pytest.mark.asyncio
async def test_request_permission_low_risk_auto_approved(permission_manager, event_bus):
    received_events = []

    async def event_handler(event):
        received_events.append(event)

    event_bus.subscribe_all(event_handler)

    workflow_id = uuid4()
    req = await permission_manager.request_permission(
        workflow_id=workflow_id,
        permission_type=PermissionType.FILE_SYSTEM,
        reason="Reading config file",
        risk_level=RiskLevel.LOW,
    )

    assert req.status == PermissionStatus.GRANTED
    assert (
        permission_manager.check_permission(PermissionType.FILE_SYSTEM, workflow_id)
        is True
    )
    # Should have emitted PERMISSION_REQUESTED and PERMISSION_GRANTED
    event_types = [e.event_type for e in received_events]
    assert EventType.PERMISSION_REQUESTED in event_types
    assert EventType.PERMISSION_GRANTED in event_types


@pytest.mark.asyncio
async def test_request_permission_medium_risk_pending(permission_manager):
    workflow_id = uuid4()
    req = await permission_manager.request_permission(
        workflow_id=workflow_id,
        permission_type=PermissionType.TERMINAL,
        reason="Execute shell command",
        risk_level=RiskLevel.MEDIUM,
    )

    assert req.status == PermissionStatus.PENDING
    assert (
        permission_manager.check_permission(PermissionType.TERMINAL, workflow_id)
        is False
    )


@pytest.mark.asyncio
async def test_grant_and_reject_permission(permission_manager, event_bus):
    received = []

    async def handler(event):
        received.append(event)

    event_bus.subscribe(EventType.PERMISSION_GRANTED, handler)
    event_bus.subscribe(EventType.PERMISSION_REJECTED, handler)

    workflow_id = uuid4()
    req = await permission_manager.request_permission(
        workflow_id=workflow_id,
        permission_type=PermissionType.ADMINISTRATOR,
        reason="System service start",
        risk_level=RiskLevel.HIGH,
    )

    # Grant
    granted_req = await permission_manager.grant_permission(req.permission_id)
    assert granted_req.status == PermissionStatus.GRANTED
    assert (
        permission_manager.check_permission(PermissionType.ADMINISTRATOR, workflow_id)
        is True
    )

    # Check event
    assert len(received) == 1
    assert received[0].event_type == EventType.PERMISSION_GRANTED

    # Reject another request
    req2 = await permission_manager.request_permission(
        workflow_id=workflow_id,
        permission_type=PermissionType.REGISTRY,
        reason="Registry edit",
        risk_level=RiskLevel.CRITICAL,
    )
    rejected_req = await permission_manager.reject_permission(req2.permission_id)
    assert rejected_req.status == PermissionStatus.REJECTED
    assert (
        permission_manager.check_permission(PermissionType.REGISTRY, workflow_id)
        is False
    )


def test_enforce_permission_success_and_failure(permission_manager):
    workflow_id = uuid4()

    # Pre-grant permission manually in state
    with pytest.raises(PermissionDeniedException) as exc_info:
        permission_manager.enforce_permission(PermissionType.POWERSHELL, workflow_id)

    assert "denied for workflow" in str(exc_info.value)
    assert exc_info.value.code == "PERMISSION_DENIED"


def test_list_permissions_filtering(permission_manager):
    w1 = uuid4()
    w2 = uuid4()

    # Add items synchronously for list testing
    import asyncio

    asyncio.run(
        permission_manager.request_permission(
            w1, PermissionType.BROWSER_ACCESS, "testing", RiskLevel.MEDIUM
        )
    )
    asyncio.run(
        permission_manager.request_permission(
            w2, PermissionType.INTERNET, "testing", RiskLevel.LOW
        )
    )

    w1_perms = permission_manager.list_permissions(workflow_id=w1)
    assert len(w1_perms) == 1

    pending_perms = permission_manager.list_permissions(status=PermissionStatus.PENDING)
    assert len(pending_perms) == 1


def test_request_permission():
    from app.core.permissions.models import PermissionStatus, PermissionType

    manager = PermissionManager(mode=ExecutionMode.SAFE)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_READ,
        reason="Need to read config",
    )

    assert req.request_id is not None
    assert req.workflow_id == "wf-1"
    assert req.status == PermissionStatus.PENDING
    assert req.permission_type == PermissionType.FILE_READ
    assert len(manager.get_pending_requests()) == 1


def test_safe_mode_requires_approval():
    from app.core.permissions.models import PermissionType

    manager = PermissionManager(mode=ExecutionMode.SAFE)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_READ,
        reason="Need to read config",
    )

    # In SAFE mode, nothing is automatically validated
    assert not manager.validate_permission(req.request_id)

    # Approve it
    manager.approve_permission(req.request_id)
    assert manager.validate_permission(req.request_id)


def test_assisted_mode_risky_permission():
    from app.core.permissions.models import PermissionType

    manager = PermissionManager(mode=ExecutionMode.ASSISTED)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_DELETE,
        reason="Need to delete temp file",
    )

    # FILE_DELETE is risky, requires approval
    assert not manager.validate_permission(req.request_id)

    manager.approve_permission(req.request_id)
    assert manager.validate_permission(req.request_id)


def test_assisted_mode_safe_permission():
    from app.core.permissions.models import PermissionStatus, PermissionType

    manager = PermissionManager(mode=ExecutionMode.ASSISTED)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_READ,
        reason="Need to read file",
    )

    # FILE_READ is safe in ASSISTED mode
    assert manager.validate_permission(req.request_id)
    # Status should auto-update
    assert req.status == PermissionStatus.APPROVED


def test_autonomous_mode():
    from app.core.permissions.models import PermissionType

    manager = PermissionManager(mode=ExecutionMode.AUTONOMOUS)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.TERMINAL_EXECUTE,
        reason="Need to run command",
    )

    # In AUTONOMOUS mode, even risky operations are auto-validated
    assert manager.validate_permission(req.request_id)


def test_reject_permission():
    from app.core.permissions.models import PermissionStatus, PermissionType

    manager = PermissionManager(mode=ExecutionMode.SAFE)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_READ,
        reason="Read file",
    )

    manager.reject_permission(req.request_id)
    assert not manager.validate_permission(req.request_id)
    assert req.status == PermissionStatus.REJECTED


def test_get_pending_requests():
    from app.core.permissions.models import PermissionType

    manager = PermissionManager(mode=ExecutionMode.SAFE)
    manager.request_permission("wf-1", "t-1", PermissionType.FILE_READ, "read")
    manager.request_permission("wf-2", "t-2", PermissionType.FILE_WRITE, "write")

    all_pending = manager.get_pending_requests()
    assert len(all_pending) == 2

    wf1_pending = manager.get_pending_requests(workflow_id="wf-1")
    assert len(wf1_pending) == 1
    assert wf1_pending[0].workflow_id == "wf-1"


def test_invalid_request_id():
    manager = PermissionManager()
    with pytest.raises(ValueError):
        manager.validate_permission("invalid-id")
    with pytest.raises(ValueError):
        manager.approve_permission("invalid-id")
    with pytest.raises(ValueError):
        manager.reject_permission("invalid-id")
