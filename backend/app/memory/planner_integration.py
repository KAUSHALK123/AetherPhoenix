from typing import Any

from shared.contracts.memory import MemoryCategory
from shared.contracts.planner import PlannerRequest

from app.memory.conversation_memory import ConversationMemoryService


class PlannerMemoryContextAdapter:
    """
    Dedicated interface adapter providing conversation memory to the Planner Agent.
    Decouples storage and retrieval logic from Planner execution logic.
    """

    def __init__(self, memory_service: ConversationMemoryService) -> None:
        self.memory_service = memory_service

    def get_planner_context(
        self, session_id: str, min_relevance: float = 0.5
    ) -> dict[str, Any]:
        """
        Retrieves relevant structured conversation context for the Planner Agent.

        Categories retrieved:
        - User preferences
        - Previous instructions
        - Decisions made during a task
        - Project context
        - Clarification answers
        - Relevant general conversation history
        """
        preferences = self.memory_service.get_relevant_memories(
            session_id=session_id,
            category=MemoryCategory.PREFERENCE,
            min_relevance=min_relevance,
        )
        instructions = self.memory_service.get_relevant_memories(
            session_id=session_id,
            category=MemoryCategory.INSTRUCTION,
            min_relevance=min_relevance,
        )
        decisions = self.memory_service.get_relevant_memories(
            session_id=session_id,
            category=MemoryCategory.DECISION,
            min_relevance=min_relevance,
        )
        project_context = self.memory_service.get_relevant_memories(
            session_id=session_id,
            category=MemoryCategory.PROJECT_CONTEXT,
            min_relevance=min_relevance,
        )
        clarifications = self.memory_service.get_relevant_memories(
            session_id=session_id,
            category=MemoryCategory.CLARIFICATION,
            min_relevance=min_relevance,
        )
        recent_history = self.memory_service.get_session_memories(
            session_id=session_id,
            limit=10,
        )

        return {
            "preferences": [m.content for m in preferences],
            "instructions": [m.content for m in instructions],
            "decisions": [m.content for m in decisions],
            "project_context": [m.content for m in project_context],
            "clarifications": [m.content for m in clarifications],
            "recent_history": [
                {"role": m.role, "content": m.content, "category": m.category.value}
                for m in recent_history
            ],
        }

    def attach_memory_to_planner_request(
        self, request: PlannerRequest, min_relevance: float = 0.5
    ) -> PlannerRequest:
        """
        Enriches a PlannerRequest context with relevant conversation memory.
        """
        context_dict = dict(request.context or {})
        memory_context = self.get_planner_context(
            session_id=request.session_id, min_relevance=min_relevance
        )
        context_dict["conversation_memory"] = memory_context

        # Also automatically store the incoming user request as a memory entry
        self.memory_service.store_memory(
            session_id=request.session_id,
            role="user",
            content=request.message,
            category=MemoryCategory.GENERAL_CHAT,
            relevance_score=1.0,
            metadata={"source": "planner_request"},
        )

        return PlannerRequest(
            session_id=request.session_id,
            message=request.message,
            context=context_dict,
            feedback=request.feedback,
        )
