from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from shared.contracts.memory import MemoryCategory
from shared.contracts.rag import RAGSourceType, RetrievedContextItem


class AgentType(str, Enum):
    """Supported agent types for tailored context retrieval."""

    PLANNER = "planner"
    WORKER = "worker"
    SUPERVISOR = "supervisor"
    HEALING = "healing"
    ORCHESTRATOR = "orchestrator"
    GENERAL = "general"


class ContextRetrievalRequest(BaseModel):
    """
    Contract representing parameters submitted to the Context Retrieval service.
    Accepts workflow/task metadata, user request, agent type, and filtering criteria.
    """

    user_request: str | None = Field(
        default=None,
        description="The current user query or high-level request message.",
    )
    workflow_id: str | None = Field(
        default=None,
        description="Optional unique identifier of the active workflow.",
    )
    workflow_goal: str | None = Field(
        default=None,
        description="Optional goal description of the current workflow.",
    )
    task_id: str | None = Field(
        default=None,
        description="Optional unique identifier of the specific task being executed.",
    )
    task_name: str | None = Field(
        default=None,
        description="Optional title or name of the specific task.",
    )
    task_description: str | None = Field(
        default=None,
        description="Optional detailed description of the task.",
    )
    agent_type: AgentType | str = Field(
        default=AgentType.GENERAL,
        description="Agent requesting context (influences weighting and relevance heuristic).",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional conversation/session ID to scope retrieval.",
    )
    max_items: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of relevant context items to return.",
    )
    min_relevance_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Minimum relevance/similarity score threshold for filtering results.",
    )
    categories: list[MemoryCategory | str] | None = Field(
        default=None,
        description="Optional list of memory categories to filter or emphasize.",
    )
    source_types: list[RAGSourceType | str] | None = Field(
        default=None,
        description="Optional list of source memory backends to search.",
    )
    metadata_filter: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Key-value dictionary filter matched against stored record metadata.",
    )
    include_previous_tasks: bool = Field(
        default=True,
        description="Whether to search related past task execution history.",
    )
    include_knowledge_base: bool = Field(
        default=True,
        description="Whether to search vector database knowledge store.",
    )
    include_conversation_memory: bool = Field(
        default=True,
        description="Whether to search conversation memory entries.",
    )

    @field_validator("agent_type")
    @classmethod
    def validate_agent_type(cls, v: Any) -> AgentType | str:
        if isinstance(v, str):
            try:
                return AgentType(v.lower())
            except ValueError:
                return v
        return v


class ContextRetrievalResponse(BaseModel):
    """
    Contract representing the structured response returned by the Context Retrieval service.
    Contains ranked context items, formatted prompt Markdown, and execution metadata.
    """

    query_used: str = Field(
        ...,
        description="Constructed retrieval query text used for semantic search.",
    )
    items: list[RetrievedContextItem] = Field(
        default_factory=list,
        description="Ranked list of relevant context items passing relevance filters.",
    )
    formatted_context: str = Field(
        default="",
        description="Structured Markdown context block formatted for agent prompt injection.",
    )
    total_retrieved: int = Field(
        default=0,
        ge=0,
        description="Count of relevant context items returned.",
    )
    filtered_count: int = Field(
        default=0,
        ge=0,
        description="Count of candidate items filtered out due to score or criteria.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution details (search duration, agent_type, filters applied, status).",
    )
