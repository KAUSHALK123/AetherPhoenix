import pytest

from app.core.events.bus import EventBus
from app.core.events.models import (
    Event,
    EventType,
    NotificationCategory,
    NotificationSeverity,
)
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_notification_service_maps_workflow_started():
    event_bus = EventBus()
    service = NotificationService(event_bus=event_bus)

    event = Event(
        workflow_id="wf-123",
        event_type=EventType.WORKFLOW_STARTED,
        source_component="Orchestrator",
        payload={"goal": "Generate Presentation"},
    )
    await event_bus.publish(event)

    notifications = service.get_notifications()
    assert len(notifications) == 1
    n = notifications[0]
    assert n.workflow_id == "wf-123"
    assert n.title == "Workflow Started"
    assert "Generate Presentation" in n.message
    assert n.category == NotificationCategory.WORKFLOW
    assert n.severity == NotificationSeverity.INFO


@pytest.mark.asyncio
async def test_notification_service_maps_permission_requested():
    event_bus = EventBus()
    service = NotificationService(event_bus=event_bus)

    event = Event(
        workflow_id="wf-123",
        event_type=EventType.PERMISSION_REQUESTED,
        source_component="PermissionManager",
        payload={
            "permission_type": "Internet Access",
            "reason": "Fetch live market data",
        },
    )
    await event_bus.publish(event)

    notifications = service.get_notifications()
    assert len(notifications) == 1
    n = notifications[0]
    assert n.title == "Permission Required"
    assert "Internet Access" in n.message
    assert n.category == NotificationCategory.PERMISSION
    assert n.severity == NotificationSeverity.WARNING


@pytest.mark.asyncio
async def test_notification_service_maps_artifact_created():
    event_bus = EventBus()
    service = NotificationService(event_bus=event_bus)

    event = Event(
        workflow_id="wf-123",
        event_type=EventType.ARTIFACT_CREATED,
        source_component="ArtifactManager",
        payload={"filename": "EV_Presentation.pptx"},
    )
    await event_bus.publish(event)

    notifications = service.get_notifications()
    assert len(notifications) == 1
    n = notifications[0]
    assert n.title == "Artifact Generated"
    assert "EV_Presentation.pptx is ready" in n.message
    assert n.category == NotificationCategory.ARTIFACT
    assert n.severity == NotificationSeverity.SUCCESS


@pytest.mark.asyncio
async def test_notification_service_mark_as_read():
    event_bus = EventBus()
    service = NotificationService(event_bus=event_bus)

    event = Event(
        workflow_id="wf-123",
        event_type=EventType.WORKFLOW_COMPLETED,
        source_component="Orchestrator",
        payload={},
    )
    await event_bus.publish(event)

    notifications = service.get_notifications(unread_only=True)
    assert len(notifications) == 1

    notification_id = str(notifications[0].id)
    service.mark_as_read(notification_id=notification_id)

    unread_notifications = service.get_notifications(unread_only=True)
    assert len(unread_notifications) == 0

    all_notifications = service.get_notifications(unread_only=False)
    assert len(all_notifications) == 1
    assert all_notifications[0].read is True
