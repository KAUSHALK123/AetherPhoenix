from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class PlannerRequest(BaseModel):
    """
    Represents a user request sent to the Planner Chat Interface.
    """
    session_id: str = Field(..., description="Unique identifier for the conversation session.")
    message: str = Field(..., description="The text message or goal from the user.")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional context such as file paths or metadata."
    )


class PlannerResponse(BaseModel):
    """
    Represents the output from the Planner Chat Interface back to the user.
    """
    session_id: str = Field(..., description="Unique identifier for the conversation session.")
    status: str = Field(..., description="Status of the request (e.g., 'clarifying', 'planning', 'ready').")
    reply: Optional[str] = Field(None, description="A text reply, usually a clarification question.")
    action: Optional[str] = Field(None, description="The next action if applicable.")
