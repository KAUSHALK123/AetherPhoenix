import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_planner_organize_downloads():
    """Test A: 'Organize my Downloads folder'"""
    response = client.post(
        "/api/v1/planner/generate",
        json={
            "goal": "Create a plan to organize my Downloads folder by categorizing into PDFs, images, and videos."  # noqa: E501
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready", data.get("reply", "No reply")

    plan = json.loads(data["reply"])

    # 1. No INTERNET permission
    assert "INTERNET" not in plan.get("required_permissions", [])

    # 2. Risk should be LOW or MEDIUM (not CRITICAL)
    assert "CRITICAL" not in plan.get("execution_summary", "")
    assert "HIGH" not in plan.get("execution_summary", "")

    # 3. Task properties
    tasks = plan.get("tasks", [])
    for task in tasks:
        # Atomic capability usage instead of generic_executor
        assert task.get("required_tool") != "generic_executor"


def test_planner_delete_downloads():
    """Test B: 'Delete all files in Downloads'"""
    response = client.post(
        "/api/v1/planner/generate",
        json={"goal": "Delete all files in my Downloads folder."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready", data.get("reply", "No reply")

    plan = json.loads(data["reply"])
    summary = plan.get("execution_summary", "")

    # 1. HIGH or CRITICAL risk detected
    assert "HIGH" in summary or "CRITICAL" in summary

    # 2. Reasoning is specific to data loss
    risks = plan.get("risks", [])
    assert any(
        "data loss" in risk or "irreversible" in risk for risk in risks
    ), f"Risks did not contain 'data loss' or 'irreversible'. Actual risks: {risks}"

    # 3. No actual PlannerAgent execution task
    tasks = plan.get("tasks", [])
    for task in tasks:
        assert task.get("assigned_agent") != "PlannerAgent"


def test_planner_create_ppt():
    """Test C: 'Create a PPT about electric cars'"""
    response = client.post(
        "/api/v1/planner/generate",
        json={"goal": "Research electric cars and create a PowerPoint presentation."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready", data.get("reply", "No reply")

    plan = json.loads(data["reply"])

    # 1. INTERNET permission detected
    assert "INTERNET" in plan.get("required_permissions", [])

    # 2. Sequential dependencies exists
    dep_graph = plan.get("dependency_graph", {})
    has_deps = any(len(deps) > 0 for deps in dep_graph.values())
    assert has_deps


def test_planner_clarification_loop():
    """Test D: 'Make a presentation'"""
    response = client.post(
        "/api/v1/planner/generate",
        json={"goal": "Make a presentation."},
    )
    assert response.status_code == 200
    data = response.json()

    # Due to low confidence score (lack of context/requirements), it should ask for clarification  # noqa: E501
    assert data["status"] == "clarifying", data.get("reply", "No reply")
    assert (
        "vague" in data.get("reply", "").lower()
        or "details" in data.get("reply", "").lower()
        or "clarify" in data.get("reply", "").lower()
    )


def test_clarification_continuation():
    """Test F: Multi-turn clarification loop continuation"""
    # 1. Start vague session
    response1 = client.post(
        "/api/v1/planner/generate",
        json={"goal": "Create a plan to organize Downloads."},
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["status"] == "clarifying", data1.get("reply")
    session_id = data1["session_id"]
    assert session_id

    # 2. Provide clarification answer using the same session_id
    response2 = client.post(
        "/api/v1/planner/generate",
        json={
            "goal": "Sort by PDF.",
            "session_id": session_id,
        },
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["status"] == "ready", data2.get("reply")

    # 3. Verify final plan incorporates both original goal and clarification
    plan = json.loads(data2["reply"])
    execution_summary = plan.get("execution_summary", "")
    assert "organize Downloads" in execution_summary
    assert "PDF" in execution_summary


def test_session_isolation():
    """Test G: Session states do not bleed into each other"""
    # 1. Start vague session A
    response_a1 = client.post(
        "/api/v1/planner/generate",
        json={"goal": "Create a plan to organize Downloads."},
    )
    data_a1 = response_a1.json()
    assert data_a1["status"] == "clarifying"
    session_id_a = data_a1["session_id"]

    # 2. Start vague session B
    response_b1 = client.post(
        "/api/v1/planner/generate",
        json={"goal": "Make a presentation."},
    )
    data_b1 = response_b1.json()
    assert data_b1["status"] == "clarifying"
    session_id_b = data_b1["session_id"]

    assert session_id_a != session_id_b

    # 3. Complete session A
    response_a2 = client.post(
        "/api/v1/planner/generate",
        json={
            "goal": "Sort by file type.",
            "session_id": session_id_a,
        },
    )
    data_a2 = response_a2.json()
    assert data_a2["status"] == "ready"

    plan_a = json.loads(data_a2["reply"])
    execution_summary_a = plan_a.get("execution_summary", "")

    assert "organize Downloads" in execution_summary_a
    assert "presentation" not in execution_summary_a
    assert "cars" not in execution_summary_a


def test_planner_parallel_groups():
    """Test E: 'Independent research tasks'"""
    response = client.post(
        "/api/v1/planner/generate",
        json={"goal": "Research apples and research oranges separately."},
    )
    assert response.status_code == 200
    data = response.json()

    if data["status"] == "ready":
        plan = json.loads(data["reply"])
        groups = plan.get("parallel_groups", [])

        # Should not place parent tasks and child tasks in the same group
        tasks = {t["task_id"]: t for t in plan.get("tasks", [])}
        for group in groups:
            group_tasks = [tasks[tid] for tid in group if tid in tasks]
            for t1 in group_tasks:
                for t2 in group_tasks:
                    if t1["task_id"] != t2["task_id"]:
                        assert t1.get("parent_task_id") != t2["task_id"]
                        assert t2.get("parent_task_id") != t1["task_id"]
