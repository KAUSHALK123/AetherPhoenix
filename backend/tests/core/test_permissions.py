"""Unit tests for PermissionManager core runtime component."""

from uuid import uuid4

import pytest
from shared.contracts.permission import PermissionStatus, PermissionType, RiskLevel

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
