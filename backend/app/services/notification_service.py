import asyncio
import logging
from collections import deque
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import WebSocket

from app.core.events.bus import EventBus, get_event_bus
from app.core.events.models import (
    Event,
    EventType,
    Notification,
    NotificationCategory,
    NotificationSeverity,
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket Connection Manager for streaming real-time notifications to connected clients.
    """

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, notification: Notification) -> None:
        if not self.active_connections:
            return

        payload = notification.model_dump(mode="json")
        disconnected: List[WebSocket] = []

        for connection in self.active_connections:
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.warning(f"Failed to send notification to WebSocket client: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


class NotificationService:
    """
    Core notification service layer.
    Subscribes to EventBus events, converts them to user-facing Notification objects,
    maintains an in-memory history, and streams notifications via WebSocket.
    """

    def __init__(self, event_bus: Optional[EventBus] = None, max_notifications: int = 500) -> None:
        self.event_bus = event_bus or get_event_bus()
        self.notifications: deque[Notification] = deque(maxlen=max_notifications)
        self.connection_manager = ConnectionManager()

        # Subscribe to all events on EventBus
        self.event_bus.subscribe_all(self._on_event)

    async def _on_event(self, event: Event) -> None:
        """
        EventBus subscriber callback. Transforms relevant events into user notifications.
        """
        notification = self._map_event_to_notification(event)
        if notification:
            self.notifications.append(notification)
            logger.debug(f"Created notification [{notification.severity}]: {notification.title} - {notification.message}")
            await self.connection_manager.broadcast(notification)

    def _map_event_to_notification(self, event: Event) -> Optional[Notification]:
        """
        Transforms an EventBus Event into a user-friendly Notification.
        """
        event_type_str = (
            event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)
        )
        payload = event.payload or {}
        workflow_id = event.workflow_id or payload.get("workflow_id")
        task_id = event.task_id or payload.get("task_id")

        if event_type_str == EventType.WORKFLOW_STARTED.value:
            goal = payload.get("goal") or payload.get("workflow_name") or "Autonomous Workflow"
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title="Workflow Started",
                message=f"Workflow started for goal: {goal}",
                category=NotificationCategory.WORKFLOW,
                severity=NotificationSeverity.INFO,
                timestamp=event.timestamp,
                payload=payload,
            )

        elif event_type_str == EventType.PERMISSION_REQUESTED.value:
            perm_type = payload.get("permission_type") or payload.get("capability") or "System Resource"
            reason = payload.get("reason") or "Required for task execution"
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title="Permission Required",
                message=f"{perm_type} access requested: {reason}",
                category=NotificationCategory.PERMISSION,
                severity=NotificationSeverity.WARNING,
                timestamp=event.timestamp,
                payload=payload,
            )

        elif event_type_str == EventType.PERMISSION_GRANTED.value:
            perm_type = payload.get("permission_type") or "System Resource"
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title="Permission Approved",
                message=f"Permission approved for {perm_type}.",
                category=NotificationCategory.PERMISSION,
                severity=NotificationSeverity.SUCCESS,
                timestamp=event.timestamp,
                payload=payload,
            )

        elif event_type_str == EventType.PERMISSION_REJECTED.value:
            perm_type = payload.get("permission_type") or "System Resource"
            reason = payload.get("reason") or "Denied by user"
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title="Permission Rejected",
                message=f"Permission rejected for {perm_type}: {reason}",
                category=NotificationCategory.PERMISSION,
                severity=NotificationSeverity.ERROR,
                timestamp=event.timestamp,
                payload=payload,
            )

        elif event_type_str == EventType.TASK_COMPLETED.value:
            task_name = payload.get("task_name") or task_id or "Task"
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title="Task Completed",
                message=f"Task '{task_name}' completed successfully.",
                category=NotificationCategory.TASK,
                severity=NotificationSeverity.SUCCESS,
                timestamp=event.timestamp,
                payload=payload,
            )

        elif event_type_str == EventType.TASK_FAILED.value:
            task_name = payload.get("task_name") or task_id or "Task"
            error = payload.get("error") or "Execution failure"
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title="Task Failed",
                message=f"Task '{task_name}' failed: {error}",
                category=NotificationCategory.TASK,
                severity=NotificationSeverity.ERROR,
                timestamp=event.timestamp,
                payload=payload,
            )

        elif event_type_str == EventType.ARTIFACT_CREATED.value:
            artifact_name = payload.get("filename") or payload.get("name") or "Artifact"
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title="Artifact Generated",
                message=f"{artifact_name} is ready.",
                category=NotificationCategory.ARTIFACT,
                severity=NotificationSeverity.SUCCESS,
                timestamp=event.timestamp,
                payload=payload,
            )

        elif event_type_str == EventType.WORKFLOW_COMPLETED.value:
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title="Workflow Completed",
                message="Workflow completed successfully.",
                category=NotificationCategory.WORKFLOW,
                severity=NotificationSeverity.SUCCESS,
                timestamp=event.timestamp,
                payload=payload,
            )

        elif event_type_str in (EventType.WORKFLOW_FAILED.value, EventType.WORKFLOW_PERMANENTLY_FAILED.value, "WorkflowFailed"):
            error_reason = payload.get("error") or payload.get("reason") or "Execution encountered unrecoverable errors"
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title="Workflow Failed",
                message=f"Workflow failed permanently: {error_reason}",
                category=NotificationCategory.WORKFLOW,
                severity=NotificationSeverity.ERROR,
                timestamp=event.timestamp,
                payload=payload,
            )

        elif event_type_str in (
            EventType.HEALING_STARTED.value,
            EventType.TASK_RETRIED.value,
            EventType.HEALING_ESCALATED.value,
            EventType.ESCALATION_REQUESTED.value,
        ):
            details = payload.get("details") or payload.get("reason") or payload.get("escalation_reason") or "Self-healing activity requires user attention"
            title = "Healing Escalated" if "ESCALAT" in event_type_str.upper() else "Healing Activity"
            return Notification(
                event_id=str(event.id),
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type_str,
                title=title,
                message=f"Self-healing activity: {details}",
                category=NotificationCategory.HEALING,
                severity=NotificationSeverity.WARNING,
                timestamp=event.timestamp,
                payload=payload,
            )

        return None

    def get_notifications(
        self, workflow_id: Optional[str] = None, unread_only: bool = False, limit: int = 50
    ) -> List[Notification]:
        """
        Retrieves notifications ordered by timestamp descending.
        """
        filtered = list(self.notifications)
        if workflow_id:
            filtered = [n for n in filtered if n.workflow_id == workflow_id]
        if unread_only:
            filtered = [n for n in filtered if not n.read]

        sorted_list = sorted(filtered, key=lambda n: n.timestamp, reverse=True)
        return sorted_list[:limit]

    def mark_as_read(self, notification_id: Optional[str] = None, mark_all: bool = False) -> int:
        """
        Marks notification(s) as read. Returns number of updated notifications.
        """
        count = 0
        for n in self.notifications:
            if mark_all:
                if not n.read:
                    n.read = True
                    count += 1
            elif notification_id and (str(n.id) == notification_id or n.event_id == notification_id):
                if not n.read:
                    n.read = True
                    count += 1
                break
        return count


_notification_service_instance: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """
    Returns the global singleton NotificationService instance.
    """
    global _notification_service_instance
    if _notification_service_instance is None:
        _notification_service_instance = NotificationService(event_bus=get_event_bus())
    return _notification_service_instance
