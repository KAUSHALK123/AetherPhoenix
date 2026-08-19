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
        if hasattr(request, "message"):
            self.metadata["last_goal"] = request.message

    def add_turn(self, message: str, plan_response: Optional[Any] = None) -> None:
        self.history.append({"message": message, "plan": plan_response})
        self.metadata["last_goal"] = message

    def get_history_dicts(self) -> List[Dict[str, Any]]:
        turns = []
        for item in self.history:
            if isinstance(item, dict):
                turns.append(item)
            elif hasattr(item, "message"):
                turns.append({"message": item.message})
        return turns

    def get_context_summary(self) -> str:
        if "last_goal" in self.metadata:
            return f"Previous goal: {self.metadata['last_goal']}"
        return ""


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


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Singleton getter for SessionManager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
