import logging

from shared.contracts.planner import PlannerRequest, PlannerResponse

from app.planner.session import SessionManager

logger = logging.getLogger(__name__)


class PlannerChatInterface:
    """
    Gateway for all user interaction with the Planner Agent.
    Handles session retrieval, input validation, and forwarding the request.
    """

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    def handle_request(self, request: PlannerRequest) -> PlannerResponse:
        """
        Receives a validated PlannerRequest, attaches it to the appropriate session,
        and (eventually) passes it to the planning pipeline.
        """
        logger.info(f"Received request for session: {request.session_id}")

        session = self.session_manager.get_or_create_session(request.session_id)
        session.add_request(request)

        # Note: Do NOT implement planning logic here as per constraints.
        # This will later forward to Intent Analyzer -> Context Analyzer, etc.

        return PlannerResponse(
            session_id=session.session_id,
            status="received",
            reply=None,
            action="forward_to_pipeline",
        )
