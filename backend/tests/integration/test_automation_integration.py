"""End-to-End Automation Subsystem Integration Test Suite (Sprint 6 - Issue #147).

Validates the full pipeline flow:
User / Planner -> Workflow Engine -> Worker Agent -> Tool / Capability Registry ->
Controllers (Browser, DOM, Desktop, Mouse, Keyboard, Screenshot) ->
Permission Manager & Safe Execution Mode -> Supervisor Validation & Healing Recovery.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from shared.contracts.browser import BrowserResult
from shared.contracts.permission import PermissionType
from shared.contracts.planner import PlannerOutput, PlannerRequest
from shared.contracts.task import (
    Task,
    TaskCategory,
    TaskStatus,
    TaskType,
)
from shared.contracts.workflow import (
    ExecutionMode,
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.agent import HealingAgent
from app.agents.planner.agent import PlannerAgent
from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus
from app.core.permissions.manager import PermissionManager
from app.engine.orchestrator import PipelineOrchestrator
from app.engine.registry import CapabilityRegistry
from app.tools.browser.controller import BrowserController
from app.tools.browser.interface import (
    BrowserAdapter,
    register_browser_capability,
)
from app.tools.desktop.controller import DesktopController
from app.tools.desktop.interface import (
    DesktopToolAdapter,
    register_desktop_tool,
)
from app.tools.desktop.models import DesktopActionResult
from app.tools.registry import ToolRegistry


@pytest.fixture
def automation_system_fixture():
    """Sets up an end-to-end integration environment with all components."""
    event_bus = EventBus()
    cap_registry = CapabilityRegistry()
    tool_registry = ToolRegistry()
    permission_manager = PermissionManager(mode=ExecutionMode.SAFE, event_bus=event_bus)

    # Instantiate Worker and Supervisor
    worker_agent = WorkerAgent(
        tool_registry=tool_registry,
        permission_manager=permission_manager,
    )
    supervisor_agent = SupervisorAgent(event_bus=event_bus)
    healing_agent = HealingAgent(event_bus=event_bus)

    # Register Browser and Desktop capabilities and tools
    register_browser_capability(
        tool_registry=tool_registry,
        cap_registry=cap_registry,
        worker_agent=worker_agent,
        permission_manager=permission_manager,
    )
    register_desktop_tool(
        registry=tool_registry,
        permission_manager=permission_manager,
        worker_agent=worker_agent,
    )

    orchestrator = PipelineOrchestrator(
        worker_agent=worker_agent,
        supervisor_agent=supervisor_agent,
        event_bus=event_bus,
        healing_agent=healing_agent,
    )

    return {
        "event_bus": event_bus,
        "cap_registry": cap_registry,
        "tool_registry": tool_registry,
        "permission_manager": permission_manager,
        "worker_agent": worker_agent,
        "supervisor_agent": supervisor_agent,
        "healing_agent": healing_agent,
        "orchestrator": orchestrator,
    }


@pytest.mark.asyncio
async def test_planner_generates_browser_and_desktop_tasks():
    """
    Verify PlannerAgent decomposes browser and desktop goals into tasks.
    """
    planner = PlannerAgent()

    # Browser task plan
    browser_req = PlannerRequest(
        session_id="sess-browser-1",
        message="Open a website and search for cars.",
    )
    browser_res = planner.process_request(browser_req)
    assert browser_res.status == "ready"
    browser_output = PlannerOutput.model_validate_json(browser_res.reply)
    assert any(t.required_tool == "browser_automation" for t in browser_output.tasks)

    # Desktop task plan
    desktop_req = PlannerRequest(
        session_id="sess-desktop-1",
        message="Open text editor and type Hello.",
    )
    desktop_res = planner.process_request(desktop_req)
    assert desktop_res.status == "ready"
    desktop_output = PlannerOutput.model_validate_json(desktop_res.reply)
    assert any(t.required_tool == "desktop_automation" for t in desktop_output.tasks)


@pytest.mark.asyncio
async def test_end_to_end_browser_automation_workflow(automation_system_fixture):
    """
    Verify end-to-end browser execution flow with Safe Mode and Supervisor.
    """
    env = automation_system_fixture
    orchestrator: PipelineOrchestrator = env["orchestrator"]
    worker_agent: WorkerAgent = env["worker_agent"]
    workflow_id = uuid4()

    # Mock BrowserController interactions within the registered adapter
    browser_adapter: BrowserAdapter = worker_agent._adapters["browser_adapter"]
    mock_controller = AsyncMock(spec=BrowserController)
    mock_controller.navigate.return_value = BrowserResult(
        success=True, data={"url": "https://example.com/cars", "status": "loaded"}
    )
    browser_adapter.controller = mock_controller

    # Create task
    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Navigate to cars search",
        description="Navigate to cars website and extract result",
        category=TaskCategory.BROWSER,
        required_tool="browser_automation",
        task_type=TaskType.LEAF,
        expected_output="url",
        inputs={"action": "navigate", "url": "https://example.com/cars"},
        status=TaskStatus.READY,
    )

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            session_id="sess-1",
            goal="Open website and search cars",
            status=WorkflowStatus.CREATED,
        ),
        tasks={task.task_id: task},
        execution_queue=[task.task_id],
    )

    # Pre-grant BROWSER_ACCESS and INTERNET permissions
    pm: PermissionManager = env["permission_manager"]
    for p_type in (PermissionType.BROWSER_ACCESS, PermissionType.INTERNET):
        req = pm.request_permission(
            workflow_id=workflow_id,
            permission_type=p_type,
            reason="Test browser automation",
        )
        pm.approve_permission(
            getattr(req, "permission_id", getattr(req, "request_id", None))
        )

    result_state = await orchestrator.run_workflow(state)

    assert result_state.metadata.status == WorkflowStatus.COMPLETED
    assert task.task_id in result_state.completed_tasks
    assert task.status == TaskStatus.COMPLETED
    mock_controller.navigate.assert_awaited_once()


@pytest.mark.asyncio
async def test_end_to_end_desktop_automation_workflow(automation_system_fixture):
    """
    Verify end-to-end desktop execution flow with Safe Mode and Supervisor.
    """
    env = automation_system_fixture
    orchestrator: PipelineOrchestrator = env["orchestrator"]
    worker_agent: WorkerAgent = env["worker_agent"]
    workflow_id = uuid4()

    # Mock DesktopController
    desktop_adapter: DesktopToolAdapter = worker_agent._adapters["desktop_adapter"]
    mock_desktop_controller = AsyncMock(spec=DesktopController)
    mock_desktop_controller.execute_action.return_value = DesktopActionResult(
        action="keyboard_type",
        success=True,
        output={"typed": "Hello World"},
        execution_time_ms=10.0,
    )
    desktop_adapter.controller = mock_desktop_controller

    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Type text in editor",
        description="Type Hello World into opened text editor",
        category=TaskCategory.DESKTOP,
        required_tool="desktop_automation",
        task_type=TaskType.LEAF,
        expected_output="typed",
        inputs={"action": "keyboard_type", "text": "Hello World"},
        status=TaskStatus.READY,
    )

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            session_id="sess-2",
            goal="Open a text editor and type Hello",
            status=WorkflowStatus.CREATED,
        ),
        tasks={task.task_id: task},
        execution_queue=[task.task_id],
    )

    # Pre-grant DESKTOP_AUTOMATION permission
    pm: PermissionManager = env["permission_manager"]
    req = pm.request_permission(
        workflow_id=workflow_id,
        permission_type=PermissionType.DESKTOP_AUTOMATION,
        reason="Test desktop automation",
    )
    pm.approve_permission(
        getattr(req, "permission_id", getattr(req, "request_id", None))
    )

    result_state = await orchestrator.run_workflow(state)

    assert result_state.metadata.status == WorkflowStatus.COMPLETED
    assert task.task_id in result_state.completed_tasks
    assert task.status == TaskStatus.COMPLETED
    mock_desktop_controller.execute_action.assert_awaited_once()


@pytest.mark.asyncio
async def test_safe_execution_mode_blocks_dangerous_operations(
    automation_system_fixture,
):
    """
    Verify restricted hotkeys and dangerous operations are blocked.
    """
    env = automation_system_fixture
    worker_agent: WorkerAgent = env["worker_agent"]
    workflow_id = uuid4()

    # 1. Desktop Restricted Hotkey
    desktop_task = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Press Alt+F4",
        description="Attempt to execute restricted Alt+F4 hotkey",
        category=TaskCategory.DESKTOP,
        required_tool="desktop_automation",
        task_type=TaskType.LEAF,
        expected_output="Window closed",
        inputs={"action": "keyboard_hotkey", "keys": ["alt", "f4"]},
        status=TaskStatus.READY,
    )

    # Real controller with Safe Execution Policy attached
    real_desktop_controller = DesktopController(
        permission_manager=env["permission_manager"]
    )
    worker_agent._adapters["desktop_adapter"].controller = real_desktop_controller

    result = await worker_agent.execute(desktop_task)
    assert result.success is False
    assert (
        "blocked" in result.error.error_message.lower()
        or "denied" in result.error.error_message.lower()
    )

    # 2. Browser Restricted URL Scheme
    browser_task = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Navigate to file scheme",
        description="Attempt to navigate to local file:/// scheme",
        category=TaskCategory.BROWSER,
        required_tool="browser_automation",
        task_type=TaskType.LEAF,
        expected_output="File content",
        inputs={"action": "navigate", "url": "file:///etc/shadow"},
        status=TaskStatus.READY,
    )

    real_browser_controller = BrowserController(
        permission_manager=env["permission_manager"]
    )
    worker_agent._adapters["browser_adapter"].controller = real_browser_controller

    result_b = await worker_agent.execute(browser_task)
    assert result_b.success is False
    assert (
        "denied" in result_b.error.error_message.lower()
        or "blocked" in result_b.error.error_message.lower()
    )


@pytest.mark.asyncio
async def test_permission_approval_flow_allows_execution(
    automation_system_fixture,
):
    """
    Verify that when required permission is approved, execution succeeds.
    """
    env = automation_system_fixture
    pm: PermissionManager = env["permission_manager"]
    worker_agent: WorkerAgent = env["worker_agent"]
    workflow_id = uuid4()
    task_id = uuid4()

    # Pre-grant permission in permission manager
    req = pm.request_permission(
        workflow_id=workflow_id,
        task_id=task_id,
        permission_type=PermissionType.DESKTOP_AUTOMATION,
        reason="Test user approved action",
    )
    pm.approve_permission(
        getattr(req, "permission_id", getattr(req, "request_id", None))
    )

    # Mock controller to return success
    desktop_adapter: DesktopToolAdapter = worker_agent._adapters["desktop_adapter"]
    mock_desktop = AsyncMock(spec=DesktopController)
    mock_desktop.execute_action.return_value = DesktopActionResult(
        action="mouse_click",
        success=True,
        output={"clicked": True},
        execution_time_ms=5.0,
    )
    desktop_adapter.controller = mock_desktop

    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="Approved click",
        description="Click button on screen",
        category=TaskCategory.DESKTOP,
        required_tool="desktop_automation",
        task_type=TaskType.LEAF,
        expected_output="Click confirmed",
        inputs={"action": "mouse_click", "x": 100, "y": 200},
        status=TaskStatus.READY,
    )

    result = await worker_agent.execute(task)
    assert result.success is True
    assert result.output == {"clicked": True}


@pytest.mark.asyncio
async def test_permission_rejection_flow_stops_execution(
    automation_system_fixture,
):
    """Verify that when a required permission is rejected, execution halts cleanly."""
    env = automation_system_fixture
    pm: PermissionManager = env["permission_manager"]
    worker_agent: WorkerAgent = env["worker_agent"]
    workflow_id = uuid4()
    task_id = uuid4()

    # Explicitly mock check_permission to return False (rejected)
    pm.check_permission = MagicMock(return_value=False)

    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="Unauthorized launch",
        description="Launch an unapproved external application",
        category=TaskCategory.DESKTOP,
        required_tool="desktop_automation",
        task_type=TaskType.LEAF,
        expected_output="App launched",
        inputs={"action": "launch_app", "app_path": "cmd.exe"},
        status=TaskStatus.READY,
    )

    result = await worker_agent.execute(task)
    assert result.success is False
    assert result.error.error_code == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_automation_failure_reports_to_supervisor_and_triggers_healing(
    automation_system_fixture,
):
    """
    Verify automation tool failures are captured by Supervisor & invoke Healing.
    """
    env = automation_system_fixture
    orchestrator: PipelineOrchestrator = env["orchestrator"]
    worker_agent: WorkerAgent = env["worker_agent"]
    workflow_id = uuid4()

    # Force adapter failure
    browser_adapter: BrowserAdapter = worker_agent._adapters["browser_adapter"]
    mock_controller = AsyncMock(spec=BrowserController)
    mock_controller.navigate.return_value = BrowserResult(
        success=False, error="Target page timed out"
    )
    browser_adapter.controller = mock_controller

    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Failing page load",
        description="Navigate to flaky web endpoint",
        category=TaskCategory.BROWSER,
        required_tool="browser_automation",
        task_type=TaskType.LEAF,
        expected_output="Loaded page",
        inputs={"action": "navigate", "url": "https://flaky-endpoint.internal"},
        status=TaskStatus.READY,
    )

    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            session_id="sess-failure",
            goal="Test recovery on failure",
            status=WorkflowStatus.CREATED,
        ),
        tasks={task.task_id: task},
        execution_queue=[task.task_id],
    )

    # Pre-grant BROWSER_ACCESS and INTERNET permissions
    # so failure originates from the tool execution
    pm: PermissionManager = env["permission_manager"]
    for p_type in (PermissionType.BROWSER_ACCESS, PermissionType.INTERNET):
        req = pm.request_permission(
            workflow_id=workflow_id,
            permission_type=p_type,
            reason="Test browser automation failure",
        )
        pm.approve_permission(
            getattr(req, "permission_id", getattr(req, "request_id", None))
        )

    result_state = await orchestrator.run_workflow(state, max_retries=1)

    # Supervisor should mark failed and invoke healing / feedback
    assert task.task_id in result_state.failed_tasks
    assert result_state.metadata.status in (
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
    )
    assert result_state.feedback is not None
