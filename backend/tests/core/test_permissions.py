import pytest

from app.core.permissions import (
    ExecutionMode,
    PermissionManager,
    PermissionStatus,
    PermissionType,
)


def test_request_permission():
    manager = PermissionManager(mode=ExecutionMode.SAFE)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_READ,
        reason="Need to read config",
    )

    assert req.request_id is not None
    assert req.workflow_id == "wf-1"
    assert req.status == PermissionStatus.PENDING
    assert req.permission_type == PermissionType.FILE_READ
    assert len(manager.get_pending_requests()) == 1


def test_safe_mode_requires_approval():
    manager = PermissionManager(mode=ExecutionMode.SAFE)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_READ,
        reason="Need to read config",
    )

    # In SAFE mode, nothing is automatically validated
    assert not manager.validate_permission(req.request_id)

    # Approve it
    manager.approve_permission(req.request_id)
    assert manager.validate_permission(req.request_id)


def test_assisted_mode_risky_permission():
    manager = PermissionManager(mode=ExecutionMode.ASSISTED)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_DELETE,
        reason="Need to delete temp file",
    )

    # FILE_DELETE is risky, requires approval
    assert not manager.validate_permission(req.request_id)

    manager.approve_permission(req.request_id)
    assert manager.validate_permission(req.request_id)


def test_assisted_mode_safe_permission():
    manager = PermissionManager(mode=ExecutionMode.ASSISTED)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_READ,
        reason="Need to read file",
    )

    # FILE_READ is safe in ASSISTED mode
    assert manager.validate_permission(req.request_id)
    # Status should auto-update
    assert req.status == PermissionStatus.APPROVED


def test_autonomous_mode():
    manager = PermissionManager(mode=ExecutionMode.AUTONOMOUS)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.TERMINAL_EXECUTE,
        reason="Need to run command",
    )

    # In AUTONOMOUS mode, even risky operations are auto-validated
    assert manager.validate_permission(req.request_id)


def test_reject_permission():
    manager = PermissionManager(mode=ExecutionMode.SAFE)
    req = manager.request_permission(
        workflow_id="wf-1",
        task_id="task-1",
        permission_type=PermissionType.FILE_READ,
        reason="Read file",
    )

    manager.reject_permission(req.request_id)
    assert not manager.validate_permission(req.request_id)
    assert req.status == PermissionStatus.REJECTED


def test_get_pending_requests():
    manager = PermissionManager(mode=ExecutionMode.SAFE)
    manager.request_permission("wf-1", "t-1", PermissionType.FILE_READ, "read")
    manager.request_permission("wf-2", "t-2", PermissionType.FILE_WRITE, "write")

    all_pending = manager.get_pending_requests()
    assert len(all_pending) == 2

    wf1_pending = manager.get_pending_requests(workflow_id="wf-1")
    assert len(wf1_pending) == 1
    assert wf1_pending[0].workflow_id == "wf-1"


def test_invalid_request_id():
    manager = PermissionManager()
    with pytest.raises(ValueError):
        manager.validate_permission("invalid-id")
    with pytest.raises(ValueError):
        manager.approve_permission("invalid-id")
    with pytest.raises(ValueError):
        manager.reject_permission("invalid-id")
