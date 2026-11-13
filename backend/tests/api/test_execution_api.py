import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_execute_workflow_api_success():
    """Test POST /api/v1/workflows/execute triggers workflow and returns RUNNING."""
    workflow_id = str(uuid.uuid4())
    task_id_1 = str(uuid.uuid4())
    task_id_2 = str(uuid.uuid4())

    plan_json = json.dumps({
        "workflow_id": workflow_id,
        "workflow_spec": "Autonomous Workflow",
        "metadata": {
            "workflow_id": workflow_id,
            "goal": "Run terminal diagnosis",
            "execution_mode": "ASSISTED",
        },
        "tasks": [
            {
                "task_id": task_id_1,
                "workflow_id": workflow_id,
                "task_name": "Phase 1: Diagnosis",
                "description": "Run diagnosis",
                "task_type": "PHASE",
                "status": "CREATED",
                "category": "TERMINAL",
                "required_tool": "",
                "dependencies": [],
            },
            {
                "task_id": task_id_2,
                "parent_task_id": task_id_1,
                "workflow_id": workflow_id,
                "task_name": "Check network status",
                "description": "Run whoami",
                "task_type": "LEAF",
                "status": "CREATED",
                "category": "TERMINAL",
                "required_tool": "terminal_tool",
                "dependencies": [],
                "inputs": {"command": "whoami"},
            },
        ],
    })

    response = client.post(
        "/api/v1/workflows/execute",
        json={"plan_json": plan_json, "execution_mode": "ASSISTED"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == workflow_id
    assert data["status"] == "RUNNING"
    assert "started" in data["message"].lower()


def test_execute_workflow_api_invalid_json():
    """Test POST /api/v1/workflows/execute with malformed json returns 422."""
    response = client.post(
        "/api/v1/workflows/execute",
        json={"plan_json": "{bad-json}"},
    )
    assert response.status_code == 422
