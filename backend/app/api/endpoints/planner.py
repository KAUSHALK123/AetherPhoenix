import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from shared.contracts.planner import PlannerRequest, PlannerResponse

from app.agents.planner.agent import PlannerAgent

router = APIRouter()

# Instantiate the agent once per application lifecycle
planner_agent = PlannerAgent()


class GeneratePlanRequest(BaseModel):
    goal: str
    session_id: str | None = None


@router.post("/generate", response_model=PlannerResponse)
async def generate_plan(request: GeneratePlanRequest):
    """
    Generate an execution plan from a user goal.
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())

        # Convert API request to internal PlannerRequest
        planner_request = PlannerRequest(
            session_id=session_id, message=request.goal, context={}
        )

        # Process request offloaded to thread to avoid blocking event loop
        response = await asyncio.to_thread(planner_agent.process_request, planner_request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
