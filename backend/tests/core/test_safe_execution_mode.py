"""Unit and integration tests for Safe Execution Mode policy."""

import pytest
from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.workflow import ExecutionMode

from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.core.permissions.policies import (
    RESTRICTED_HOTKEYS,
    RESTRICTED_URL_SCHEMES,
    SafeExecutionPolicy,
)
from app.tools.browser.controller import BrowserController


def test_action_risk_classification():
    # Low risk actions
    assert SafeExecutionPolicy.classify_risk("browser_extract_content") == RiskLevel.LOW
    assert SafeExecutionPolicy.classify_risk("get_windows") == RiskLevel.LOW
    assert SafeExecutionPolicy.classify_risk("mouse_move") == RiskLevel.LOW
    assert SafeExecutionPolicy.classify_risk("get_active_window") == RiskLevel.LOW

    # Medium risk actions
    assert SafeExecutionPolicy.classify_risk("browser_navigate") == RiskLevel.MEDIUM
    assert SafeExecutionPolicy.classify_risk("mouse_click") == RiskLevel.MEDIUM
    assert SafeExecutionPolicy.classify_risk("keyboard_type") == RiskLevel.MEDIUM

    # High / Critical risk actions
    assert SafeExecutionPolicy.classify_risk("keyboard_hotkey") == RiskLevel.HIGH
    assert SafeExecutionPolicy.classify_risk("launch_app") == RiskLevel.HIGH
    assert SafeExecutionPolicy.classify_risk("terminate_app") == RiskLevel.HIGH
    assert SafeExecutionPolicy.classify_risk("powershell_execute") == RiskLevel.CRITICAL


def test_restricted_hotkeys_classification():
    # Restricted hotkeys must be classified as CRITICAL
    for hotkey in RESTRICTED_HOTKEYS:
        assert (
            SafeExecutionPolicy.classify_risk(
                "keyboard_hotkey", context={"keys": hotkey}
            )
            == RiskLevel.CRITICAL
        )


def test_restricted_urls_classification():
    # Dangerous schemes must be classified as CRITICAL
    for scheme in RESTRICTED_URL_SCHEMES:
        assert (
            SafeExecutionPolicy.classify_risk(
                "browser_navigate", context={"url": f"{scheme}test"}
            )
            == RiskLevel.CRITICAL
        )


def test_safe_execution_policy_evaluation_safe_mode():
    # Low-risk allowed without explicit approval
    decision = SafeExecutionPolicy.evaluate(
        "get_active_window", mode=ExecutionMode.SAFE
    )
    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.risk_level == RiskLevel.LOW

    # Medium/high-risk allowed but requires approval
    decision = SafeExecutionPolicy.evaluate("mouse_click", mode=ExecutionMode.SAFE)
    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.risk_level == RiskLevel.MEDIUM

    # Restricted hotkey blocked completely
    decision = SafeExecutionPolicy.evaluate(
        "keyboard_hotkey",
        mode=ExecutionMode.SAFE,
        context={"keys": "alt+f4"},
    )
    assert decision.allowed is False
    assert decision.risk_level == RiskLevel.CRITICAL


def test_safe_execution_policy_evaluation_assisted_mode():
    # Low & Medium risk allowed without approval in ASSISTED mode
    decision = SafeExecutionPolicy.evaluate("mouse_click", mode=ExecutionMode.ASSISTED)
    assert decision.allowed is True
    assert decision.requires_approval is False

    # High risk requires approval
    decision = SafeExecutionPolicy.evaluate("launch_app", mode=ExecutionMode.ASSISTED)
    assert decision.allowed is True
    assert decision.requires_approval is True


def test_safe_execution_policy_evaluation_autonomous_mode():
    # Autonomous allows everything except strictly blocked
    decision = SafeExecutionPolicy.evaluate("launch_app", mode=ExecutionMode.AUTONOMOUS)
    assert decision.allowed is True
    assert decision.requires_approval is False


@pytest.mark.asyncio
async def test_permission_manager_safe_mode_low_risk_auto_check():
    pm = PermissionManager(mode=ExecutionMode.SAFE)
    # Low risk desktop action should auto-pass check_permission
    check = pm.check_permission(
        action="get_windows",
        permission_type=PermissionType.DESKTOP_AUTOMATION,
        workflow_id="wf-1",
        task_id="t-1",
    )
    is_approved = await check if hasattr(check, "__await__") else bool(check)
    assert is_approved is True


@pytest.mark.asyncio
async def test_permission_manager_safe_mode_high_risk_requires_approval():
    pm = PermissionManager(mode=ExecutionMode.SAFE)
    # High risk action creates a pending request and awaits approval
    check = pm.check_permission(
        action="launch_app",
        permission_type=PermissionType.DESKTOP_AUTOMATION,
        workflow_id="wf-1",
        task_id="t-1",
        timeout_seconds=0.1,
    )

    # Initially pending / not approved immediately
    assert bool(check) is False

    # If approved, validate_permission should be True
    pending = pm.get_pending_requests(workflow_id="wf-1")
    assert len(pending) == 1
    pm.approve_permission(pending[0].request_id)
    assert bool(check) is True


@pytest.mark.asyncio
async def test_permission_manager_blocks_restricted_action():
    pm = PermissionManager(mode=ExecutionMode.SAFE)
    # Attempt to press restricted Alt+F4
    check = pm.check_permission(
        action="keyboard_hotkey",
        permission_type=PermissionType.DESKTOP_AUTOMATION,
        workflow_id="wf-1",
        task_id="t-1",
        context={"keys": "alt+f4"},
    )
    is_approved = await check if hasattr(check, "__await__") else bool(check)
    assert is_approved is False


@pytest.mark.asyncio
async def test_permission_manager_execution_limits():
    pm = PermissionManager(mode=ExecutionMode.SAFE, max_actions_per_task=2)

    # 1st action: OK
    res1 = pm.check_permission(
        action="mouse_move",
        permission_type=PermissionType.DESKTOP_AUTOMATION,
        workflow_id="wf-1",
        task_id="task-limit-1",
    )
    assert (await res1 if hasattr(res1, "__await__") else bool(res1)) is True

    # 2nd action: OK
    res2 = pm.check_permission(
        action="mouse_move",
        permission_type=PermissionType.DESKTOP_AUTOMATION,
        workflow_id="wf-1",
        task_id="task-limit-1",
    )
    assert (await res2 if hasattr(res2, "__await__") else bool(res2)) is True

    # 3rd action: Limit exceeded -> Blocked
    res3 = pm.check_permission(
        action="mouse_move",
        permission_type=PermissionType.DESKTOP_AUTOMATION,
        workflow_id="wf-1",
        task_id="task-limit-1",
    )
    assert (await res3 if hasattr(res3, "__await__") else bool(res3)) is False


@pytest.mark.asyncio
async def test_browser_controller_safe_mode_navigation_blocked_scheme():
    pm = PermissionManager(mode=ExecutionMode.SAFE)
    controller = BrowserController(permission_manager=pm)

    with pytest.raises(PermissionDeniedException) as exc_info:
        await controller.navigate(
            url="file:///etc/passwd", workflow_id="wf-1", task_id="t-1"
        )

    assert "denied for browser action 'navigate'" in str(exc_info.value)
