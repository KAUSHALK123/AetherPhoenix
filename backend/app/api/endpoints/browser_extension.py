from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from shared.contracts.browser_extension import ExtensionConnectionStatus

from app.core.logging import get_logger
from app.tools.browser_extension.connection_manager import (
    get_connection_manager,
)

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for the Chrome Browser Extension.
    Establishes connection and handles messages with AetherPhoenix.
    """
    manager = get_connection_manager()
    client_id = await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_incoming_message(data)
    except WebSocketDisconnect:
        logger.info(f"Browser Extension client {client_id} disconnected normally.")
    except Exception as e:
        logger.warning(f"Browser Extension client {client_id} websocket error: {e}")
    finally:
        await manager.disconnect()


@router.get("/status", response_model=ExtensionConnectionStatus)
async def get_extension_status():
    """Returns current connection status of the Chrome Browser Extension."""
    manager = get_connection_manager()
    return manager.get_status()
