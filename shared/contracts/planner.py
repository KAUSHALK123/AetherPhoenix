from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    DATA_RETRIEVAL = "data_retrieval"
    SYSTEM_MODIFICATION = "system_modification"
    CONTENT_GENERATION = "content_generation"
    UNKNOWN = "unknown"


class UserRequirement(BaseModel):
    """
    Represents the parsed structure of a user's request.
    """
    intent: IntentCategory = Field(default=IntentCategory.UNKNOWN, description="The primary goal of the request.")
    requirements: List[str] = Field(default_factory=list, description="Specific things the user wants.")
    constraints: List[str] = Field(default_factory=list, description="Limitations or constraints on the request.")
    category: str = Field(default="general", description="General classification tag.")


class ClarificationResult(BaseModel):
    """
    Result of the clarification engine's analysis.
    """
    needs_clarification: bool = Field(..., description="True if the request is incomplete.")
    question: Optional[str] = Field(None, description="The follow-up question to ask the user.")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields.")


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
