from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.core.logging.logger import get_logger
from app.tools.desktop.exceptions import (
    DesktopSessionError,
    DesktopSessionExpiredError,
    DesktopSessionNotFoundError,
)
from app.tools.desktop.models import (
    ApplicationInfo,
    DesktopSessionConfig,
    DesktopSessionInfo,
)

logger = get_logger(__name__)


class DesktopSession:
    """
    Represents a managed desktop execution session for Worker tasks.
    Maintains session state, process tracking, lifetime limits, and activity metrics.
    """

    def __init__(
        self,
        session_id: Optional[UUID] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        config: Optional[DesktopSessionConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.session_id: UUID = session_id or uuid4()
        self.workflow_id: Optional[UUID] = workflow_id
        self.task_id: Optional[UUID] = task_id
        self.config: DesktopSessionConfig = config or DesktopSessionConfig()
        self.created_at: datetime = datetime.now(timezone.utc)
        self.last_activity_at: datetime = datetime.now(timezone.utc)
        self.is_active: bool = True
        self.launched_processes: Dict[int, ApplicationInfo] = {}
        self.metadata: Dict[str, Any] = metadata or {}

    def touch(self) -> None:
        """Updates the last activity timestamp to prevent idle timeout."""
        if not self.is_active:
            raise DesktopSessionError(
                f"Cannot touch inactive session {self.session_id}"
            )
        self.last_activity_at = datetime.now(timezone.utc)

    def is_expired(self, current_time: Optional[datetime] = None) -> bool:
        """Checks if the session has expired due to total or idle duration."""
        if not self.is_active:
            return True

        now = current_time or datetime.now(timezone.utc)

        # Check total session timeout
        total_seconds = (now - self.created_at).total_seconds()
        if total_seconds > self.config.session_timeout_seconds:
            return True

        # Check idle timeout
        idle_seconds = (now - self.last_activity_at).total_seconds()
        if idle_seconds > self.config.idle_timeout_seconds:
            return True

        return False

    def register_process(self, app_info: ApplicationInfo) -> None:
        """Registers a launched application process in this session."""
        if len(self.launched_processes) >= self.config.max_applications:
            raise DesktopSessionError(
                f"Maximum application limit ({self.config.max_applications}) reached."
            )
        self.launched_processes[app_info.process_id] = app_info
        self.touch()
        logger.info(
            f"Registered PID {app_info.process_id} ({app_info.name}) "
            f"in session {self.session_id}"
        )

    def unregister_process(self, pid: int) -> Optional[ApplicationInfo]:
        """Unregisters a terminated application process from this session."""
        app_info = self.launched_processes.pop(pid, None)
        if app_info:
            self.touch()
            logger.info(
                f"Unregistered PID {pid} ({app_info.name}) "
                f"from session {self.session_id}"
            )
        return app_info

    def get_processes(self) -> List[ApplicationInfo]:
        """Returns the list of active applications in this session."""
        return list(self.launched_processes.values())

    def close(self) -> None:
        """Marks the session as closed."""
        self.is_active = False
        logger.info(f"Desktop session {self.session_id} closed.")

    def to_info(self) -> DesktopSessionInfo:
        """Converts the session instance into a serializable Pydantic info model."""
        return DesktopSessionInfo(
            session_id=self.session_id,
            workflow_id=self.workflow_id,
            task_id=self.task_id,
            created_at=self.created_at,
            last_activity_at=self.last_activity_at,
            is_active=self.is_active and not self.is_expired(),
            active_applications=list(self.launched_processes.keys()),
            metadata=self.metadata,
        )


class DesktopSessionManager:
    """
    Manages the lifecycle of desktop sessions across workflows and tasks.
    Provides session lookup, creation, cleanup, and validation.
    """

    def __init__(self):
        self._sessions: Dict[str, DesktopSession] = {}
        self._active_session_id: Optional[str] = None

    def create_session(
        self,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        config: Optional[DesktopSessionConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DesktopSession:
        """Creates and activates a new desktop session."""
        session = DesktopSession(
            workflow_id=workflow_id,
            task_id=task_id,
            config=config,
            metadata=metadata,
        )
        sess_id_str = str(session.session_id)
        self._sessions[sess_id_str] = session
        self._active_session_id = sess_id_str
        logger.info(
            f"Created new desktop session: {sess_id_str} "
            f"(Workflow: {workflow_id}, Task: {task_id})"
        )
        return session

    def get_session(self, session_id: UUID | str) -> DesktopSession:
        """Retrieves a desktop session by ID, validating its existence and expiry."""
        sess_id_str = str(session_id)
        session = self._sessions.get(sess_id_str)
        if not session:
            raise DesktopSessionNotFoundError(
                f"Desktop session {session_id} not found."
            )

        if session.is_expired():
            session.close()
            if self._active_session_id == sess_id_str:
                self._active_session_id = None
            raise DesktopSessionExpiredError(
                f"Desktop session {session_id} has expired."
            )

        return session

    def get_active_session(self) -> Optional[DesktopSession]:
        """Returns the currently active session if one exists and is valid."""
        if not self._active_session_id:
            return None

        session = self._sessions.get(self._active_session_id)
        if not session or session.is_expired():
            if session:
                session.close()
            self._active_session_id = None
            return None

        return session

    def close_session(self, session_id: UUID | str) -> None:
        """Closes and deactivates a desktop session."""
        sess_id_str = str(session_id)
        session = self._sessions.get(sess_id_str)
        if session:
            session.close()
        if self._active_session_id == sess_id_str:
            self._active_session_id = None

    def cleanup_expired_sessions(self) -> int:
        """Cleans up all expired sessions and returns the count of purged sessions."""
        purged = 0
        now = datetime.now(timezone.utc)
        for sess_id_str, session in list(self._sessions.items()):
            if session.is_expired(now):
                session.close()
                if self._active_session_id == sess_id_str:
                    self._active_session_id = None
                purged += 1
        return purged
