import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.tools.browser.controller import get_browser_controller

router = APIRouter()
logger = logging.getLogger(__name__)


class StartSessionRequest(BaseModel):
    headless: Optional[bool] = None
    auth_profile: Optional[str] = None


class NavigateRequest(BaseModel):
    url: str
    timeout_ms: float = 30000.0


class InteractRequest(BaseModel):
    selector: str
    action: str = "click"
    value: Optional[str] = None
    timeout_ms: float = 10000.0


class StepRequest(BaseModel):
    action: str = "click"
    target: str
    value: Optional[str] = None
    expected_outcome: Optional[str] = None
    timeout_ms: float = 10000.0


class ScrollRequest(BaseModel):
    direction: str = "down"
    amount: int = 500


class TabRequest(BaseModel):
    action: str
    url: Optional[str] = "about:blank"
    tab_index: Optional[int] = None


@router.get("/session")
async def get_browser_session() -> Dict[str, Any]:
    """Retrieves the current active browser session state, URL, title, and live frame."""
    ctrl = get_browser_controller()
    return await ctrl.get_live_state()


@router.post("/session/start")
async def start_browser_session(
    request: Optional[StartSessionRequest] = None,
) -> Dict[str, Any]:
    """Starts or reuses a browser session."""
    ctrl = get_browser_controller()
    headless = request.headless if request else None
    auth_profile = request.auth_profile if request else None
    res = await ctrl.start_session(headless=headless, auth_profile=auth_profile)
    live_state = await ctrl.get_live_state()
    return {
        "success": res.success,
        "data": res.data,
        "error": res.error,
        "live_state": live_state,
    }


@router.post("/session/close")
async def close_browser_session() -> Dict[str, Any]:
    """Closes the current browser session."""
    ctrl = get_browser_controller()
    res = await ctrl.close_session()
    return {"success": res.success, "error": res.error}


@router.post("/navigate")
async def navigate_browser(request: NavigateRequest) -> Dict[str, Any]:
    """Navigates active browser tab to target URL."""
    ctrl = get_browser_controller()
    res = await ctrl.navigate(url=request.url, timeout_ms=request.timeout_ms)
    live_state = await ctrl.get_live_state()
    return {
        "success": res.success,
        "data": res.data,
        "error": res.error,
        "live_state": live_state,
    }


@router.post("/interact")
async def interact_browser(request: InteractRequest) -> Dict[str, Any]:
    """Performs click or fill interaction on an element."""
    ctrl = get_browser_controller()
    res = await ctrl.interact(
        selector=request.selector,
        action=request.action,
        value=request.value,
        timeout_ms=request.timeout_ms,
    )
    live_state = await ctrl.get_live_state()
    return {
        "success": res.success,
        "data": res.data,
        "error": res.error,
        "live_state": live_state,
    }


@router.post("/step")
async def execute_observe_act_verify_step(request: StepRequest) -> Dict[str, Any]:
    """Executes a full Observe-Act-Verify interaction step."""
    ctrl = get_browser_controller()
    res = await ctrl.execute_observe_act_verify(
        action=request.action,
        target=request.target,
        value=request.value,
        expected_outcome=request.expected_outcome,
        timeout_ms=request.timeout_ms,
    )
    live_state = await ctrl.get_live_state()
    return {
        "success": res.success,
        "data": res.data,
        "error": res.error,
        "live_state": live_state,
    }


@router.post("/scroll")
async def scroll_browser(request: ScrollRequest) -> Dict[str, Any]:
    """Scrolls the active browser window."""
    ctrl = get_browser_controller()
    res = await ctrl.scroll(direction=request.direction, amount=request.amount)
    live_state = await ctrl.get_live_state()
    return {
        "success": res.success,
        "data": res.data,
        "error": res.error,
        "live_state": live_state,
    }


@router.post("/tabs")
async def manage_tabs(request: TabRequest) -> Dict[str, Any]:
    """Manages browser tabs (new, switch, close, list)."""
    ctrl = get_browser_controller()
    if request.action == "new":
        res = await ctrl.new_tab(url=request.url or "about:blank")
    elif request.action == "switch":
        res = await ctrl.switch_tab(tab_index=request.tab_index or 0)
    elif request.action == "close":
        res = await ctrl.close_tab(tab_index=request.tab_index)
    else:
        res = None

    live_state = await ctrl.get_live_state()
    return {
        "success": res.success if res else True,
        "data": res.data if res else {"tabs": live_state["tabs"]},
        "error": res.error if res else None,
        "live_state": live_state,
    }


@router.get("/elements")
async def get_interactive_elements(limit: int = 50) -> Dict[str, Any]:
    """Discovers visible interactive elements on the active page."""
    ctrl = get_browser_controller()
    elements = await ctrl.get_interactive_elements(limit=limit)
    return {"elements": [el.model_dump() for el in elements], "count": len(elements)}


@router.get("/screenshot")
async def get_browser_screenshot() -> Response:
    """Returns the latest screenshot image as raw JPEG."""
    ctrl = get_browser_controller()
    res = await ctrl.capture_screenshot(image_type="jpeg", quality=75)
    if res.success and res.data and "screenshot_bytes" in res.data:
        return Response(content=res.data["screenshot_bytes"], media_type="image/jpeg")
    return Response(content=b"", status_code=404)


@router.get("/stream")
async def stream_live_browser():
    """
    Server-Sent Events (SSE) streaming endpoint pushing live browser state
    and view frames to the frontend at regular intervals.
    """
    ctrl = get_browser_controller()

    async def event_generator():
        while True:
            try:
                state = await ctrl.get_live_state()
                payload = json.dumps(state)
                yield f"data: {payload}\n\n"
            except Exception as e:
                logger.debug(f"Error in browser SSE stream: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
