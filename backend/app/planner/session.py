import uuid
from typing import Dict, List, Optional

from shared.contracts.planner import PlannerRequest


class PlannerSession:
    """
    Represents an ongoing conversation between the user and the Planner Agent.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.history: List[PlannerRequest] = []
        self.metadata: Dict[str, str] = {}

    def add_request(self, request: PlannerRequest) -> None:
        self.history.append(request)


class SessionManager:
    """
    Manages active Planner sessions.
    Currently uses an in-memory dictionary.
    """

    def __init__(self):
        self._sessions: Dict[str, PlannerSession] = {}

    def get_session(self, session_id: str) -> Optional[PlannerSession]:
        return self._sessions.get(session_id)

    def create_session(self) -> PlannerSession:
        session = PlannerSession()
        self._sessions[session.session_id] = session
        return session

    def get_or_create_session(self, session_id: Optional[str]) -> PlannerSession:
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        return self.create_session()
