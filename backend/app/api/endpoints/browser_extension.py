from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from shared.contracts.browser_extension import ExtensionConnectionStatus

from app.core.logging import get_logger
from app.tools.browser_extension.connection_manager import (
    get_connection_manager,
)

logger = get_logger(__name__)

router = APIRouter()


class NavigateRequest(BaseModel):
    url: str
    workflow_id: str | None = None
    task_id: str | None = None


class InteractRequest(BaseModel):
    selector: str
    action: str = "click"
    value: str | None = None
    timeout_ms: float = 10000.0
    workflow_id: str | None = None
    task_id: str | None = None


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


@router.post("/navigate")
async def navigate_browser(request: NavigateRequest):
    """
    Commands browser to navigate to the target URL.
    Uses connected Chrome Extension if active, or launches system desktop browser.
    """
    from app.tools.browser_extension.controller import BrowserExtensionController

    controller = BrowserExtensionController()
    result = await controller.navigate(
        url=request.url,
        workflow_id=request.workflow_id,
        task_id=request.task_id,
    )
    return {"success": result.success, "data": result.data, "error": result.error}


@router.post("/interact")
async def interact_browser(request: InteractRequest):
    """
    Executes in-page DOM interaction (click button, fill input, submit)
    via the connected Chrome Browser Extension.
    """
    from app.tools.browser_extension.controller import BrowserExtensionController

    controller = BrowserExtensionController()
    result = await controller.interact(
        selector=request.selector,
        action=request.action,
        value=request.value,
        timeout_ms=request.timeout_ms,
        workflow_id=request.workflow_id,
        task_id=request.task_id,
    )
    return {"success": result.success, "data": result.data, "error": result.error}
