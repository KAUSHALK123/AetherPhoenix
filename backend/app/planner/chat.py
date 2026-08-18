import logging
from typing import Optional

from shared.contracts.planner import PlannerRequest, PlannerResponse

from app.memory.conversation_memory import ConversationMemoryService
from app.memory.planner_integration import PlannerMemoryContextAdapter
from app.planner.session import SessionManager

logger = logging.getLogger(__name__)


class PlannerChatInterface:
    """
    Gateway for all user interaction with the Planner Agent.
    Handles session retrieval, input validation, conversation memory
    integration, and forwarding the request.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        memory_service: Optional[ConversationMemoryService] = None,
    ):
        self.session_manager = session_manager
        self.memory_service = memory_service
        self.memory_adapter = (
            PlannerMemoryContextAdapter(memory_service) if memory_service else None
        )

    def handle_request(self, request: PlannerRequest) -> PlannerResponse:
        """
        Receives a validated PlannerRequest, enriches it with conversation
        memory if available, attaches it to the appropriate session, and
        passes it to the planning pipeline.
        """
        logger.info(f"Received request for session: {request.session_id}")

        enriched_request = request
        if self.memory_adapter:
            enriched_request = (
                self.memory_adapter.attach_memory_to_planner_request(request)
            )

        session = self.session_manager.get_or_create_session(
            enriched_request.session_id
        )
        session.add_request(enriched_request)


        # Note: Do NOT implement planning logic here as per constraints.
        # This will later forward to Intent Analyzer -> Context Analyzer, etc.

        return PlannerResponse(
            session_id=session.session_id,
            status="received",
            reply=None,
            action="forward_to_pipeline",
        )
