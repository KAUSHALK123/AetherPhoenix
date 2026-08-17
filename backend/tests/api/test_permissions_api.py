import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.permissions.manager import get_permission_manager
from app.core.permissions.models import PermissionType, PermissionStatus

client = TestClient(app)
permission_manager = get_permission_manager()


def test_permissions_api_flow():
    # Clear existing requests for predictability
    permission_manager.requests.clear()

    # 1. Create a request directly in manager
    req = permission_manager.request_permission(
        workflow_id="wf-test",
        task_id="t-test",
        permission_type=PermissionType.FILE_DELETE,
        reason="Test deletion approval",
    )
    request_id = req.request_id

    # 2. Get pending requests via API
    response = client.get("/api/v1/permissions/pending")
    assert response.status_code == 200
    pending_list = response.json()
    assert len(pending_list) >= 1
    assert pending_list[0]["request_id"] == request_id
    assert pending_list[0]["permission_type"] == "FILE_DELETE"
    assert pending_list[0]["risk_level"] == "MEDIUM"

    # 3. Approve the request via API
    response = client.post(f"/api/v1/permissions/{request_id}/approve")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"

    # Verify status in manager
    assert permission_manager.requests[request_id].status == PermissionStatus.APPROVED

    # 4. Create another request to test rejection
    req2 = permission_manager.request_permission(
        workflow_id="wf-test",
        task_id="t-test",
        permission_type=PermissionType.POWERSHELL_EXECUTE,
        reason="Test command rejection",
    )
    request_id2 = req2.request_id

    # Reject via API
    response = client.post(f"/api/v1/permissions/{request_id2}/reject")
    assert response.status_code == 200
    data2 = response.json()
    assert data2["status"] == "REJECTED"

    # Verify status in manager
    assert permission_manager.requests[request_id2].status == PermissionStatus.REJECTED


def test_approve_reject_invalid_id():
    response = client.post("/api/v1/permissions/non-existent-id/approve")
    assert response.status_code == 404

    response = client.post("/api/v1/permissions/non-existent-id/reject")
    assert response.status_code == 404
