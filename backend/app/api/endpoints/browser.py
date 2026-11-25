from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.tools.browser.controller import get_browser_controller

router = APIRouter()


class ResumeHandoffRequest(BaseModel):
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None


@router.post("/resume")
@router.post("/human-handoff/resume")
async def resume_browser_handoff(request: ResumeHandoffRequest = ResumeHandoffRequest()):
    """
    Resumes browser automation after human sign-in/captcha completion.
    Re-checks that the authentication wall is cleared and continues execution.
    """
    controller = get_browser_controller()
    success = controller.resume_human_handoff(
        workflow_id=request.workflow_id,
        task_id=request.task_id,
    )
    if not success:
        return {
            "status": "not_waiting",
            "message": "No active human handoff waiting for resume.",
        }
    return {
        "status": "resumed",
        "message": "Resumed human handoff check.",
    }


@router.get("/human-handoff/status")
async def get_browser_handoff_status():
    """Returns active human handoff status and details."""
    controller = get_browser_controller()
    return {
        "is_waiting": getattr(controller, "_handoff_active", False),
        "handoff_info": getattr(controller, "_handoff_info", None),
    }
