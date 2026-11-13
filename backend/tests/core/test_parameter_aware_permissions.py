"""Stage 1 Adversarial Tests: Parameter-Aware Permission Enforcement.

Verifies that WorkerAgent, WorkerTaskExecutor, PermissionManager, and
SafeExecutionPolicy inspect sanitized execution parameters (command, script,
url, keys, path), enforce risk/action binding, and block CRITICAL violations
across both ExecutionMode.SAFE and ExecutionMode.AUTONOMOUS.
"""

from uuid import uuid4

import pytest
from shared.contracts.execution import ExecutionMetrics, ExecutionResult
from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.task import Task, TaskCategory
from shared.contracts.tool import Tool, ToolHealth, ToolState
from shared.contracts.workflow import ExecutionMode

from app.agents.worker.agent import WorkerAgent
from app.agents.worker.executor import WorkerTaskExecutor
from app.core.permissions.manager import PermissionManager
from app.tools.adapter import BaseToolAdapter
from app.tools.registry import ToolRegistry


class RecordingAdapter(BaseToolAdapter):
    """Test adapter recording whether execute() was reached."""

    def __init__(self) -> None:
        self.called = False
        self.last_task: Task | None = None

    async def execute(self, task: Task) -> ExecutionResult:
        self.called = True
        self.last_task = task
        return ExecutionResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            success=True,
            output={"status": "executed"},
            metrics=ExecutionMetrics(execution_time_ms=1.0, exit_code=0),
        )


def _setup_worker(mode: ExecutionMode, required_permissions: list[str] | None = None):
    pm = PermissionManager(mode=mode)
    registry = ToolRegistry()
    perms = (
        required_permissions
        if required_permissions is not None
        else [PermissionType.TERMINAL.value]
    )
    registry.register(
        Tool(
            name="terminal_tool",
            adapter="mock_exec_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            required_permissions=perms,
        )
    )
    registry.register(
        Tool(
            name="browser_tool",
            adapter="mock_exec_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            required_permissions=(
                required_permissions
                if required_permissions is not None
                else [PermissionType.BROWSER_ACCESS.value]
            ),
        )
    )
    registry.register(
        Tool(
            name="desktop_tool",
            adapter="mock_exec_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            required_permissions=(
                required_permissions
                if required_permissions is not None
                else [PermissionType.DESKTOP_AUTOMATION.value]
            ),
        )
    )
    registry.register(
        Tool(
            name="file_tool",
            adapter="mock_exec_adapter",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            required_permissions=(
                required_permissions
                if required_permissions is not None
                else [PermissionType.FILE_SYSTEM.value]
            ),
        )
    )
    adapter = RecordingAdapter()
    worker = WorkerAgent(tool_registry=registry, permission_manager=pm)
    worker.register_adapter("mock_exec_adapter", adapter)
    return worker, adapter, pm, registry


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [ExecutionMode.SAFE, ExecutionMode.AUTONOMOUS])
@pytest.mark.parametrize(
    "inputs",
    [
        {"command": "rm -rf /"},
        {"command": "rm   -rf   /var/data"},
        {"script": "Remove-Item -Recurse -Force C:\\Users"},
        {"params": {"command": "format c: /q"}},
        {"cmd": "del /f /s /q C:\\important"},
    ],
)
async def test_worker_blocks_destructive_commands_from_task_inputs(mode, inputs):
    worker, adapter, _, _ = _setup_worker(mode)
    task = Task(
        workflow_id=uuid4(),
        task_name="Run shell command",
        description="Execute command",
        required_tool="terminal_tool",
        category=TaskCategory.TERMINAL,
        expected_output="done",
        inputs=inputs,
    )

    result = await worker.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "PERMISSION_DENIED"
    assert adapter.called is False


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [ExecutionMode.SAFE, ExecutionMode.AUTONOMOUS])
@pytest.mark.parametrize(
    "bad_url",
    [
        "file:///etc/passwd",
        "FILE:///C:/Windows/System32/config/SAM",
        "javascript:alert(document.cookie)",
        "gopher://127.0.0.1:6379/_INFO",
        "data:text/html,<script>alert(1)</script>",
    ],
)
async def test_worker_blocks_restricted_urls_from_task_inputs(mode, bad_url):
    worker, adapter, _, _ = _setup_worker(mode)
    task = Task(
        workflow_id=uuid4(),
        task_name="Open URL",
        description="Navigate",
        required_tool="browser_tool",
        category=TaskCategory.BROWSER,
        expected_output="page content",
        inputs={"action": "browser_navigate", "url": bad_url},
    )

    result = await worker.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "PERMISSION_DENIED"
    assert adapter.called is False


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [ExecutionMode.SAFE, ExecutionMode.AUTONOMOUS])
@pytest.mark.parametrize(
    "hotkey_val",
    [
        "alt+f4",
        "CTRL+ALT+DEL",
        ["win", "r"],
        "ctrl+shift+esc",
    ],
)
async def test_worker_blocks_restricted_hotkeys_from_task_inputs(mode, hotkey_val):
    worker, adapter, _, _ = _setup_worker(mode)
    task = Task(
        workflow_id=uuid4(),
        task_name="Send hotkey",
        description="Desktop hotkey",
        required_tool="desktop_tool",
        category=TaskCategory.DESKTOP,
        expected_output="done",
        inputs={"action": "keyboard_hotkey", "keys": hotkey_val},
    )

    result = await worker.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "PERMISSION_DENIED"
    assert adapter.called is False


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [ExecutionMode.SAFE, ExecutionMode.AUTONOMOUS])
@pytest.mark.parametrize(
    "path_val",
    [
        "/etc/shadow",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "/home/user/.ssh/id_rsa",
    ],
)
async def test_worker_blocks_restricted_system_paths_from_task_inputs(mode, path_val):
    worker, adapter, _, _ = _setup_worker(mode)
    task = Task(
        workflow_id=uuid4(),
        task_name="Write system file",
        description="Modify path",
        required_tool="file_tool",
        category=TaskCategory.FILE_SYSTEM,
        expected_output="done",
        inputs={"action": "file_write", "path": path_val},
    )

    result = await worker.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "PERMISSION_DENIED"
    assert adapter.called is False


@pytest.mark.asyncio
async def test_unpermissioned_tool_cannot_bypass_critical_parameter_policy():
    """Even if a tool declares required_permissions=[], CRITICAL params are blocked."""
    worker, adapter, _, _ = _setup_worker(
        ExecutionMode.AUTONOMOUS, required_permissions=[]
    )
    task = Task(
        workflow_id=uuid4(),
        task_name="Bypass attempt",
        description="Tool without required_permissions",
        required_tool="terminal_tool",
        category=TaskCategory.OTHER,
        expected_output="done",
        inputs={"command": "rm -rf /tmp/everything"},
    )

    result = await worker.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "PERMISSION_DENIED"
    assert adapter.called is False


def test_executor_blocks_destructive_payload_in_autonomous_mode():
    _, _, pm, registry = _setup_worker(ExecutionMode.AUTONOMOUS)
    executor = WorkerTaskExecutor(tool_registry=registry, permission_manager=pm)
    called = False

    def _tool_fn(_inputs):
        nonlocal called
        called = True
        return {"ok": True}

    task = Task(
        workflow_id=uuid4(),
        task_name="Run command",
        description="Destructive",
        required_tool="terminal_tool",
        category=TaskCategory.TERMINAL,
        expected_output="done",
    )
    result = executor.execute_task(
        task=task,
        payload={"command": "rm -rf /"},
        tool_fn=_tool_fn,
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "PERMISSION_DENIED"
    assert called is False


@pytest.mark.asyncio
async def test_low_risk_workflow_grant_cannot_be_reused_for_higher_risk_action():
    """A granted LOW-risk workflow permission must not authorize HIGH/CRITICAL actions."""
    pm = PermissionManager(mode=ExecutionMode.SAFE, auto_approve_low_risk=True)
    wf_id = uuid4()

    # 1. Grant a LOW-risk DESKTOP_AUTOMATION request in the workflow
    req = pm.request_permission(
        wf_id,
        PermissionType.DESKTOP_AUTOMATION,
        "Read active window title",
        risk_level=RiskLevel.LOW,
        task_id=uuid4(),
    )
    assert req.status.value in ("GRANTED", "APPROVED")

    # 2. A HIGH-risk launch_app in the same workflow must NOT reuse the LOW grant
    check_high = pm.check_permission(
        action="launch_app",
        permission_type=PermissionType.DESKTOP_AUTOMATION,
        workflow_id=str(wf_id),
        task_id=str(uuid4()),
        context={"app_name": "powershell.exe"},
        timeout_seconds=0.02,
    )
    assert await check_high is False

    # 3. Even if a benign CRITICAL operation is checked in AUTONOMOUS mode,
    # it still requires explicit approval rather than auto-approving.
    pm_auto = PermissionManager(mode=ExecutionMode.AUTONOMOUS)
    check_crit = pm_auto.check_permission(
        action="powershell_execute",
        permission_type=PermissionType.POWERSHELL,
        workflow_id=str(wf_id),
        task_id=str(uuid4()),
        context={"command": "Get-Process"},
        timeout_seconds=0.02,
    )
    assert await check_crit is False
