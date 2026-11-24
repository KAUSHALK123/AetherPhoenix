from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from shared.contracts.event import EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionResult,
    SupervisorDecision,
)
from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus, TaskType
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus
from app.core.permissions.manager import PermissionManager
from app.engine.orchestrator import PipelineOrchestrator
from app.tools.file_explorer import register_file_explorer_tool
from app.tools.file_explorer.adapter import FileExplorerToolAdapter
from app.tools.file_explorer.models import FileExplorerActionResult
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_list_folders_in_d_drive_end_to_end(tmp_path):
    """
    End-to-end regression test:
    Executing 'list folders in d drive' workflow produces a final message
    containing real folder names from a mocked directory.
    """
    event_bus = EventBus()
    permission_manager = PermissionManager()
    tool_registry = ToolRegistry()

    workflow_id = uuid4()

    # Pre-approve FILE_SYSTEM and FILE_WRITE permissions for workflow
    for p_type in (PermissionType.FILE_SYSTEM, PermissionType.FILE_WRITE):
        perm_req = PermissionRequest(
            workflow_id=workflow_id,
            permission_type=p_type,
            reason="Inspect D drive directory",
            risk_level=RiskLevel.SAFE,
            status=PermissionStatus.GRANTED,
        )
        permission_manager.request_permission(perm_req)

    # Register file_explorer tool
    register_file_explorer_tool(tool_registry)
    fe_adapter = FileExplorerToolAdapter(
        permission_manager=permission_manager,
    )

    # Mock list_files in executor to simulate real D: drive directory contents
    mock_items = [
        {"name": "Projects", "is_dir": True, "type": "folder", "path": "D:\\Projects"},
        {"name": "Music", "is_dir": True, "type": "folder", "path": "D:\\Music"},
        {
            "name": "Documents",
            "is_dir": True,
            "type": "folder",
            "path": "D:\\Documents",
        },
        {"name": "Games", "is_dir": True, "type": "folder", "path": "D:\\Games"},
        {"name": "setup.exe", "is_dir": False, "type": "file", "path": "D:\\setup.exe"},
    ]
    mock_result = FileExplorerActionResult(
        success=True,
        action="list_files",
        target_path="D:\\",
        message="Found 5 items in 'D:\\'",
        metadata={"items": mock_items, "count": 5},
    )

    with patch.object(
        fe_adapter.executor, "list_files", new=AsyncMock(return_value=mock_result)
    ):
        worker = WorkerAgent(
            tool_registry=tool_registry,
            permission_manager=permission_manager,
        )
        worker.register_adapter(
            "app.tools.file_explorer.adapter.FileExplorerToolAdapter", fe_adapter
        )
        worker.register_adapter("file_explorer", fe_adapter)

        supervisor = SupervisorAgent(
            event_bus=event_bus,
            max_retries=3,
        )

        orchestrator = PipelineOrchestrator(
            worker_agent=worker,
            supervisor_agent=supervisor,
            event_bus=event_bus,
        )

        # Track emitted events
        emitted_events = []

        async def capture_event(evt: RuntimeEvent):
            emitted_events.append(evt)

        event_bus.subscribe(EventType.WORKFLOW_COMPLETED, capture_event)

        state = SharedWorkflowState(
            metadata=WorkflowMetadata(
                workflow_id=workflow_id,
                goal="list folders in d drive",
                status=WorkflowStatus.CREATED,
            )
        )

        task = Task(
            workflow_id=workflow_id,
            task_name="Inspect D Drive Folders",
            description="List folders and directories in D:\\ drive",
            assigned_agent="WorkerAgent",
            required_tool="file_explorer",
            category=TaskCategory.FILE_SYSTEM,
            priority=TaskPriority.LOW,
            expected_output="List of folders in D:\\",
            inputs={"action": "list_files", "path": "D:\\"},
        )
        state.tasks[task.task_id] = task
        state.execution_queue.append(task.task_id)

        final_state = await orchestrator.run_workflow(state, max_retries=3)

        # 1. Assert workflow and task completion
        assert final_state.metadata.status == WorkflowStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

        # 2. Assert final response exists and contains real folder names
        assert final_state.final_response is not None
        answer = final_state.final_response.get("answer", "")
        raw_output = final_state.final_response.get("raw_output", {})

        assert "Projects" in answer
        assert "Music" in answer
        assert "Documents" in answer
        assert "Games" in answer

        # 3. Assert raw output preserved
        assert "Inspect D Drive Folders" in raw_output
        assert raw_output["Inspect D Drive Folders"]["action"] == "list_files"

        # 4. Assert WebSocket / EventBus payload contains answer and raw_output
        completed_events = [
            e for e in emitted_events if e.event_type == EventType.WORKFLOW_COMPLETED
        ]
        assert len(completed_events) == 1
        payload = completed_events[0].payload
        assert payload.get("answer") == answer
        assert "Projects" in payload.get("answer", "")
        assert payload.get("raw_output") is not None


@pytest.mark.asyncio
async def test_supervisor_fails_task_with_expected_output_returning_empty_or_noop():
    """
    Supervisor contract check:
    A task expected to produce output that returns empty output or no-op output
    must FAIL its contract check, not COMPLETE.
    """
    event_bus = EventBus()
    supervisor = SupervisorAgent(event_bus=event_bus, max_retries=3)
    workflow_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="List files",
            status=WorkflowStatus.RUNNING,
        )
    )

    task = Task(
        workflow_id=workflow_id,
        task_name="Directory Listing Task",
        description="List files in directory",
        required_tool="file_explorer",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="List of files",
        task_type=TaskType.LEAF,
    )
    state.tasks[task.task_id] = task
    state.running_tasks.append(task.task_id)

    # 1. Case: Empty dict output
    empty_result = ExecutionResult(
        task_id=task.task_id,
        workflow_id=workflow_id,
        success=True,
        output={},
        artifacts=[],
    )

    validation_empty = await supervisor.execute(task, result=empty_result, state=state)
    assert validation_empty.is_valid is False
    assert validation_empty.decision == SupervisorDecision.FAILED
    assert task.status == TaskStatus.FAILED

    # Reset task status for next test case
    task.status = TaskStatus.RUNNING
    state.running_tasks.append(task.task_id)
    if task.task_id in state.failed_tasks:
        state.failed_tasks.remove(task.task_id)

    # 2. Case: Placeholder / no-op output dictionary
    noop_result = ExecutionResult(
        task_id=task.task_id,
        workflow_id=workflow_id,
        success=True,
        output={"status": "COMPLETED", "phase": "Directory Listing Task"},
        artifacts=[],
    )

    validation_noop = await supervisor.execute(task, result=noop_result, state=state)
    assert validation_noop.is_valid is False
    assert validation_noop.decision == SupervisorDecision.FAILED
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_supervisor_fails_placeholder_leaf_task_without_tool():
    """
    Supervisor contract check:
    A placeholder or no-op task must never count as COMPLETED.
    """
    event_bus = EventBus()
    supervisor = SupervisorAgent(event_bus=event_bus, max_retries=3)
    workflow_id = uuid4()

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="Test Goal",
            status=WorkflowStatus.RUNNING,
        )
    )

    placeholder_task = Task(
        workflow_id=workflow_id,
        task_name="Execute Primary Action",
        description="Placeholder task with no assigned tool",
        required_tool="",  # No tool
        category=TaskCategory.OTHER,
        expected_output="Primary action completed",
        task_type=TaskType.LEAF,
    )
    state.tasks[placeholder_task.task_id] = placeholder_task
    state.running_tasks.append(placeholder_task.task_id)

    result = ExecutionResult(
        task_id=placeholder_task.task_id,
        workflow_id=workflow_id,
        success=True,
        output={"phase": "Execute Primary Action", "status": "COMPLETED"},
        artifacts=[],
    )

    validation = await supervisor.execute(placeholder_task, result=result, state=state)
    assert validation.is_valid is False
    assert validation.decision == SupervisorDecision.FAILED
    assert placeholder_task.status == TaskStatus.FAILED
    assert any(
        "placeholder" in issue.lower() or "no-op" in issue.lower()
        for issue in validation.issues
    )


@pytest.mark.asyncio
async def test_final_response_reports_tool_error_honestly():
    """
    Verifies that when a tool returns an error or fails, the final answer
    honestly and explicitly reports the failure rather than a generic completion.
    """
    event_bus = EventBus()
    supervisor = SupervisorAgent(event_bus=event_bus, max_retries=1)
    worker = AsyncMock(spec=WorkerAgent)

    orchestrator = PipelineOrchestrator(
        worker_agent=worker,
        supervisor_agent=supervisor,
        event_bus=event_bus,
    )

    workflow_id = uuid4()
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            goal="check d drive",
            status=WorkflowStatus.RUNNING,
        )
    )

    failed_task = Task(
        workflow_id=workflow_id,
        task_name="Check D Drive",
        description="Inspect D drive",
        required_tool="file_explorer",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="Directory inspection output",
        status=TaskStatus.FAILED,
    )
    state.tasks[failed_task.task_id] = failed_task
    state.failed_tasks.append(failed_task.task_id)
    state.task_outputs["Check D Drive"] = {"error": "Device D: not ready or accessible"}

    res = await orchestrator._generate_final_response(state)
    assert "error" in res["answer"].lower() or "Device D: not ready" in res["answer"]
    assert (
        res["raw_output"]["Check D Drive"]["error"]
        == "Device D: not ready or accessible"
    )


@pytest.mark.asyncio
async def test_large_output_truncation_before_synthesis():
    """
    Verifies that very large task outputs are properly truncated before
    being processed for the final response.
    """
    event_bus = EventBus()
    supervisor = SupervisorAgent(event_bus=event_bus)
    worker = AsyncMock(spec=WorkerAgent)

    orchestrator = PipelineOrchestrator(
        worker_agent=worker,
        supervisor_agent=supervisor,
        event_bus=event_bus,
    )

    huge_stdout = "line of log output\n" * 1000  # ~19,000 characters
    truncated = orchestrator._truncate_for_llm(huge_stdout, max_chars=2000)

    assert len(truncated) < 2200
    assert "[truncated" in truncated
