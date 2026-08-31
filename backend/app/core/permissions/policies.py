from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from shared.contracts.permission import RiskLevel

from .models import ExecutionMode, PermissionType

# Define which permissions are inherently risky and always require approval,
# even in ASSISTED mode.
RISKY_PERMISSIONS: Set[PermissionType] = {
    PermissionType.FILE_DELETE,
    PermissionType.TERMINAL_EXECUTE,
    PermissionType.POWERSHELL_EXECUTE,
    PermissionType.REGISTRY_EDIT,
    PermissionType.ADMIN_PRIVILEGE,
}

# Restricted / blocked desktop keys and hotkeys in Safe Mode
RESTRICTED_HOTKEYS: Set[str] = {
    "alt+f4",
    "ctrl+alt+del",
    "win+l",
    "win+r",
    "ctrl+shift+esc",
    "format",
}

# Restricted URL schemes and blocked endpoints
RESTRICTED_URL_SCHEMES: Set[str] = {
    "file://",
    "gopher://",
    "data://",
    "javascript:",
}

# Destructive command patterns blocked unconditionally in all execution modes
DESTRUCTIVE_COMMAND_TOKENS: Set[str] = {
    "rm -rf",
    "format ",
    "format-volume",
    "del /f",
    "remove-item",
    "clear-disk",
    "drop database",
    "reg delete",
    "stop-computer",
    "restart-computer",
    "set-executionpolicy",
}


@dataclass
class PolicyDecision:
    """Represents the outcome of a safe execution evaluation."""

    allowed: bool
    requires_approval: bool
    risk_level: RiskLevel
    reason: str
    action: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SafeExecutionPolicy:
    """
    Comprehensive policy engine enforcing Safe Execution Mode rules,
    action classification, risk assessment, and parameter restrictions.
    """

    # Action to baseline RiskLevel mapping
    ACTION_RISK_MAP: Dict[str, RiskLevel] = {
        # Browser low risk
        "browser_start_session": RiskLevel.LOW,
        "browser_close_session": RiskLevel.LOW,
        "browser_extract_content": RiskLevel.LOW,
        "browser_capture_screenshot": RiskLevel.LOW,
        "extract_content": RiskLevel.LOW,
        "capture_screenshot": RiskLevel.LOW,
        # Browser medium / high risk
        "browser_navigate": RiskLevel.MEDIUM,
        "navigate": RiskLevel.MEDIUM,
        "browser_interact": RiskLevel.MEDIUM,
        "interact": RiskLevel.MEDIUM,
        # Desktop read-only / low risk
        "get_windows": RiskLevel.LOW,
        "get_active_window": RiskLevel.LOW,
        "get_desktop_state": RiskLevel.LOW,
        "mouse_get_position": RiskLevel.LOW,
        "desktop_screenshot": RiskLevel.LOW,
        # Desktop interactive medium risk
        "start_session": RiskLevel.LOW,
        "end_session": RiskLevel.LOW,
        "mouse_move": RiskLevel.LOW,
        "mouse_click": RiskLevel.MEDIUM,
        "mouse_double_click": RiskLevel.MEDIUM,
        "mouse_right_click": RiskLevel.MEDIUM,
        "mouse_drag": RiskLevel.MEDIUM,
        "mouse_scroll": RiskLevel.LOW,
        "keyboard_press": RiskLevel.MEDIUM,
        "keyboard_type": RiskLevel.MEDIUM,
        "keyboard_write": RiskLevel.MEDIUM,
        "keyboard_hotkey": RiskLevel.HIGH,
        "launch_app": RiskLevel.HIGH,
        "terminate_app": RiskLevel.HIGH,
        "focus_window": RiskLevel.LOW,
        "resize_window": RiskLevel.LOW,
        "move_window": RiskLevel.LOW,
        "minimize_window": RiskLevel.LOW,
        "maximize_window": RiskLevel.LOW,
        "restore_window": RiskLevel.LOW,
        "close_window": RiskLevel.HIGH,
        # Powershell / Terminal / File
        "terminal_execute": RiskLevel.CRITICAL,
        "powershell_execute": RiskLevel.CRITICAL,
        "file_delete": RiskLevel.HIGH,
        "file_write": RiskLevel.MEDIUM,
        "file_read": RiskLevel.LOW,
        # Memory low risk actions
        "memory_create": RiskLevel.LOW,
        "memory_read": RiskLevel.LOW,
        "memory_update": RiskLevel.LOW,
        "memory_delete": RiskLevel.LOW,
    }

    # Action limits (e.g. max actions per session/task in SAFE mode)
    DEFAULT_MAX_ACTIONS_PER_TASK = 100
    DEFAULT_ACTION_TIMEOUT_SECONDS = 30.0

    @classmethod
    def classify_risk(
        cls,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RiskLevel:
        """Classifies the risk level of an automation action."""
        ctx = context or {}
        norm_action = action.lower().replace("desktopaction: ", "").replace(" ", "_")

        # Check for restricted hotkeys
        if "hotkey" in norm_action or "keys" in ctx:
            keys = str(ctx.get("keys", "")).lower()
            for restricted in RESTRICTED_HOTKEYS:
                if restricted in keys:
                    return RiskLevel.CRITICAL

        # Check for restricted URLs
        if "url" in ctx:
            raw_url = str(ctx.get("url", "")).strip().lower()
            try:
                import urllib.parse

                parsed = urllib.parse.urlparse(raw_url)
                scheme = (parsed.scheme + "://") if parsed.scheme else raw_url
            except Exception:
                scheme = raw_url
            for restricted_scheme in RESTRICTED_URL_SCHEMES:
                if raw_url.startswith(restricted_scheme) or scheme.startswith(
                    restricted_scheme
                ):
                    return RiskLevel.CRITICAL

        # Check for risky commands
        if "command" in ctx or "script" in ctx:
            cmd = str(ctx.get("command") or ctx.get("script") or "").lower()
            for token in DESTRUCTIVE_COMMAND_TOKENS:
                if token in cmd:
                    return RiskLevel.CRITICAL

        # Lookup in standard map
        if norm_action in cls.ACTION_RISK_MAP:
            return cls.ACTION_RISK_MAP[norm_action]

        # Fuzzy lookup
        for key, risk in cls.ACTION_RISK_MAP.items():
            if key in norm_action or norm_action in key:
                return risk

        # Fail closed: default to HIGH risk for unknown actions
        return RiskLevel.HIGH

    @classmethod
    def evaluate(
        cls,
        action: str,
        mode: ExecutionMode | str = ExecutionMode.SAFE,
        context: Optional[Dict[str, Any]] = None,
        permission_type: Optional[PermissionType] = None,
    ) -> PolicyDecision:
        """
        Evaluates an automation action against safe execution policies.
        Returns a PolicyDecision for the action.
        """
        ctx = context or {}
        mode_str = mode.value if hasattr(mode, "value") else str(mode).upper()
        risk = cls.classify_risk(action, ctx)

        # Inherent security violations are blocked unconditionally
        if risk == RiskLevel.CRITICAL:
            keys = str(ctx.get("keys", "")).lower()
            if any(restricted in keys for restricted in RESTRICTED_HOTKEYS):
                return PolicyDecision(
                    allowed=False,
                    requires_approval=True,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"Restricted hotkey '{keys}' is blocked by Safe Mode.",
                    action=action,
                    metadata=ctx,
                )

            url = str(ctx.get("url", "")).strip().lower()
            for scheme in RESTRICTED_URL_SCHEMES:
                if url.startswith(scheme):
                    return PolicyDecision(
                        allowed=False,
                        requires_approval=True,
                        risk_level=RiskLevel.CRITICAL,
                        reason=(
                            f"Restricted URL scheme '{url}' is blocked by Safe Mode."
                        ),
                        action=action,
                        metadata=ctx,
                    )

            # Destructive commands blocked unconditionally across all execution modes
            cmd = str(ctx.get("command") or ctx.get("script") or action or "").lower()
            for token in DESTRUCTIVE_COMMAND_TOKENS:
                if token in cmd:
                    return PolicyDecision(
                        allowed=False,
                        requires_approval=True,
                        risk_level=RiskLevel.CRITICAL,
                        reason=(
                            f"Destructive command pattern '{token}' is blocked "
                            "unconditionally by Safe Mode."
                        ),
                        action=action,
                        metadata=ctx,
                    )

        # Mode-based decisions
        if mode_str == ExecutionMode.SAFE.value:
            if risk in (RiskLevel.SAFE, RiskLevel.LOW):
                return PolicyDecision(
                    allowed=True,
                    requires_approval=False,
                    risk_level=risk,
                    reason=f"Low-risk operation '{action}' permitted in Safe Mode.",
                    action=action,
                    metadata=ctx,
                )
            else:
                return PolicyDecision(
                    allowed=True,
                    requires_approval=True,
                    risk_level=risk,
                    reason=(
                        f"Action '{action}' is {risk.value} risk "
                        "and requires approval in Safe Mode."
                    ),
                    action=action,
                    metadata=ctx,
                )

        elif mode_str == ExecutionMode.ASSISTED.value:
            if risk in (RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM):
                return PolicyDecision(
                    allowed=True,
                    requires_approval=False,
                    risk_level=risk,
                    reason=(
                        f"Operation '{action}' ({risk.value} risk) "
                        "is allowed in Assisted Mode."
                    ),
                    action=action,
                    metadata=ctx,
                )
            else:
                return PolicyDecision(
                    allowed=True,
                    requires_approval=True,
                    risk_level=risk,
                    reason=(
                        f"High risk operation '{action}' "
                        "requires approval in Assisted Mode."
                    ),
                    action=action,
                    metadata=ctx,
                )

        elif mode_str == ExecutionMode.AUTONOMOUS.value:
            return PolicyDecision(
                allowed=True,
                requires_approval=False,
                risk_level=risk,
                reason=f"Operation '{action}' permitted in Autonomous Mode.",
                action=action,
                metadata=ctx,
            )

        # Unknown mode: Fail closed
        return PolicyDecision(
            allowed=False,
            requires_approval=True,
            risk_level=RiskLevel.CRITICAL,
            reason=f"Unknown mode '{mode_str}', action '{action}' blocked.",
            action=action,
            metadata=ctx,
        )


class PermissionPolicy:
    @staticmethod
    def requires_approval(permission_type: PermissionType, mode: str) -> bool:
        """Legacy permission policy method maintaining backward compatibility."""
        if mode == "SAFE":
            return True

        if mode == "ASSISTED":
            return permission_type in RISKY_PERMISSIONS

        if mode == "AUTONOMOUS":
            return False

        return True
