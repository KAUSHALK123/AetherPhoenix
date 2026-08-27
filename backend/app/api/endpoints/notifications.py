from typing import List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.core.events.models import Notification
from app.services.notification_service import get_notification_service

router = APIRouter()
notification_service = get_notification_service()


@router.websocket("/ws")
async def websocket_notification_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time notification streaming to frontend clients.
    """
    await notification_service.connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and process incoming messages if any
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_service.connection_manager.disconnect(websocket)
    except Exception:
        notification_service.connection_manager.disconnect(websocket)


@router.get("", response_model=List[Notification])
async def get_notifications(
    workflow_id: Optional[str] = None, unread_only: bool = False, limit: int = 50
) -> List[Notification]:
    """
    Get notifications history with optional filtering.
    """
    try:
        return notification_service.get_notifications(
            workflow_id=workflow_id, unread_only=unread_only, limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{notification_id}/read")
async def mark_notification_as_read(notification_id: str) -> dict:
    """
    Mark a specific notification as read.
    """
    count = notification_service.mark_as_read(notification_id=notification_id)
    if count == 0:
        raise HTTPException(status_code=404, detail="Notification not found or already read")
    return {"success": True, "message": "Notification marked as read", "count": count}


@router.post("/read-all")
async def mark_all_notifications_as_read() -> dict:
    """
    Mark all notifications as read.
    """
    count = notification_service.mark_as_read(mark_all=True)
    return {"success": True, "message": "All notifications marked as read", "count": count}
