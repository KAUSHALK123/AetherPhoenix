from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.tools.desktop.exceptions import (
    DesktopSessionError,
    DesktopSessionExpiredError,
    DesktopSessionNotFoundError,
)
from app.tools.desktop.models import ApplicationInfo, DesktopSessionConfig
from app.tools.desktop.session import DesktopSession, DesktopSessionManager


def test_desktop_session_creation():
    wf_id = uuid4()
    task_id = uuid4()
    config = DesktopSessionConfig(
        session_timeout_seconds=100.0, idle_timeout_seconds=50.0
    )

    session = DesktopSession(
        workflow_id=wf_id,
        task_id=task_id,
        config=config,
        metadata={"env": "test"},
    )

    assert session.session_id is not None
    assert session.workflow_id == wf_id
    assert session.task_id == task_id
    assert session.is_active is True
    assert session.metadata["env"] == "test"
    assert session.is_expired() is False


def test_desktop_session_touch_and_expiry():
    session = DesktopSession(
        config=DesktopSessionConfig(
            session_timeout_seconds=10.0, idle_timeout_seconds=2.0
        )
    )

    # Initial state
    assert not session.is_expired()

    # Simulate total session timeout
    future_time = datetime.now(timezone.utc) + timedelta(seconds=15)
    assert session.is_expired(current_time=future_time) is True

    # Simulate idle timeout
    idle_future = datetime.now(timezone.utc) + timedelta(seconds=3)
    assert session.is_expired(current_time=idle_future) is True

    # Touch updates activity
    session.touch()
    assert session.is_active is True


def test_desktop_session_process_registration_and_limits():
    config = DesktopSessionConfig(max_applications=2)
    session = DesktopSession(config=config)

    app1 = ApplicationInfo(process_id=101, name="notepad.exe")
    app2 = ApplicationInfo(process_id=102, name="calc.exe")
    app3 = ApplicationInfo(process_id=103, name="explorer.exe")

    session.register_process(app1)
    session.register_process(app2)
    assert len(session.get_processes()) == 2

    # Exceed limit
    with pytest.raises(DesktopSessionError, match="Maximum application limit"):
        session.register_process(app3)

    # Unregister
    removed = session.unregister_process(101)
    assert removed == app1
    assert len(session.get_processes()) == 1


def test_desktop_session_close():
    session = DesktopSession()
    assert session.is_active is True
    session.close()
    assert session.is_active is False
    assert session.is_expired() is True

    with pytest.raises(DesktopSessionError, match="Cannot touch inactive session"):
        session.touch()


def test_desktop_session_to_info():
    session = DesktopSession()
    app = ApplicationInfo(process_id=201, name="test.exe")
    session.register_process(app)

    info = session.to_info()
    assert info.session_id == session.session_id
    assert info.is_active is True
    assert 201 in info.active_applications


def test_session_manager_lifecycle():
    manager = DesktopSessionManager()

    # Create
    session = manager.create_session()
    sess_id = session.session_id
    assert manager.get_active_session() == session

    # Retrieve
    retrieved = manager.get_session(sess_id)
    assert retrieved == session

    # Close
    manager.close_session(sess_id)
    assert manager.get_active_session() is None


def test_session_manager_not_found():
    manager = DesktopSessionManager()
    with pytest.raises(DesktopSessionNotFoundError):
        manager.get_session(uuid4())


def test_session_manager_expired_session_handling():
    manager = DesktopSessionManager()
    session = manager.create_session(
        config=DesktopSessionConfig(
            session_timeout_seconds=0.01, idle_timeout_seconds=0.01
        )
    )

    # Force expiration
    session.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)

    with pytest.raises(DesktopSessionExpiredError):
        manager.get_session(session.session_id)

    assert manager.get_active_session() is None


def test_session_manager_cleanup():
    manager = DesktopSessionManager()
    session1 = manager.create_session(
        config=DesktopSessionConfig(session_timeout_seconds=100)
    )
    session2 = manager.create_session(
        config=DesktopSessionConfig(session_timeout_seconds=100)
    )

    # Expire session1
    session1.created_at = datetime.now(timezone.utc) - timedelta(seconds=200)

    purged = manager.cleanup_expired_sessions()
    assert purged == 1
    assert session2.is_active is True
