import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from shared.contracts.permission import RiskLevel

from .models import ExecutionMode, PermissionType

RISK_ORDER: Dict[RiskLevel, int] = {
    RiskLevel.SAFE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


def risk_rank(level: Any) -> int:
    """Return ordinal severity rank (0..4) for a RiskLevel or string."""
    if isinstance(level, RiskLevel):
        return RISK_ORDER[level]
    raw = str(getattr(level, "value", level) or "LOW").strip().upper()
    try:
        return RISK_ORDER[RiskLevel(raw)]
    except ValueError:
        return RISK_ORDER[RiskLevel.HIGH]


def max_risk(a: Any, b: Any) -> RiskLevel:
    """Return the higher of two RiskLevel values."""
    ra = risk_rank(a)
    rb = risk_rank(b)
    target = max(ra, rb)
    for lvl, rank in RISK_ORDER.items():
        if rank == target:
            return lvl
    return RiskLevel.HIGH


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

DESTRUCTIVE_COMMAND_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r", re.IGNORECASE),
    re.compile(r"\bdel\s+/[fqs]\b", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),
    re.compile(r"\bmkfs(?:\.[a-z0-9]+)?\b", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\bdrop\s+(?:database|table)\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r"\bchmod\s+-?[rR]?\s*777\s+/", re.IGNORECASE),
)

RESTRICTED_SYSTEM_PATHS: tuple[str, ...] = (
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "/.ssh/",
    "/root/.ssh",
    "c:/windows/system32",
    "c:/windows/syswow64",
    "c:/windows/system",
)

SENSITIVE_REDACT_KEYS: Set[str] = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "auth_header",
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
        # Canonical tool baseline risks
        "web_research": RiskLevel.LOW,
        "web_research_tool": RiskLevel.LOW,
        "web_scraping": RiskLevel.LOW,
        "web_scraping_tool": RiskLevel.LOW,
        "web_scraper": RiskLevel.LOW,
        "cache_cleaner": RiskLevel.LOW,
        "pdf_generator": RiskLevel.MEDIUM,
        "pdf_tool": RiskLevel.MEDIUM,
        "ppt_generator": RiskLevel.MEDIUM,
        "ppt_tool": RiskLevel.MEDIUM,
        "document_generator": RiskLevel.MEDIUM,
        "content_tool": RiskLevel.MEDIUM,
        "screenshot_engine": RiskLevel.LOW,
        "ocr": RiskLevel.LOW,
        "browser": RiskLevel.MEDIUM,
        "browser_tool": RiskLevel.MEDIUM,
        "browser_automation": RiskLevel.MEDIUM,
        "file_explorer": RiskLevel.MEDIUM,
        "file_system": RiskLevel.MEDIUM,
        "file_manager_tool": RiskLevel.MEDIUM,
        "git_tool": RiskLevel.MEDIUM,
        "api_tool": RiskLevel.MEDIUM,
        "desktop_tool": RiskLevel.HIGH,
        "desktop_automation": RiskLevel.HIGH,
        "terminal_tool": RiskLevel.CRITICAL,
        "terminal": RiskLevel.CRITICAL,
        "powershell": RiskLevel.CRITICAL,
        "powershell_tool": RiskLevel.CRITICAL,
        "powershell_executor": RiskLevel.CRITICAL,
        "admin_tool": RiskLevel.CRITICAL,
    }

    # Action limits (e.g. max actions per session/task in SAFE mode)
    DEFAULT_MAX_ACTIONS_PER_TASK = 100
    DEFAULT_ACTION_TIMEOUT_SECONDS = 30.0

    @classmethod
    def sanitize_context(
        cls,
        params: Optional[Dict[str, Any]],
        action: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract and normalize security-relevant execution parameters without secrets."""
        sanitized: Dict[str, Any] = {}
        sources = []
        if isinstance(params, dict):
            sources.append(params)
        if isinstance(extra, dict):
            sources.append(extra)

        def _bound_str(val: Any, max_len: int = 1000) -> str:
            text = str(val).strip()
            return text[:max_len] if len(text) > max_len else text

        key_aliases = {
            "command": ("command", "cmd", "shell_command"),
            "script": ("script", "code", "powershell_script"),
            "url": ("url", "target_url", "endpoint", "href"),
            "keys": ("keys", "hotkey", "key_combination", "shortcut"),
            "path": (
                "path",
                "file_path",
                "target_path",
                "destination",
                "source_path",
                "output_path",
                "filepath",
            ),
        }

        for src in sources:
            for canonical, aliases in key_aliases.items():
                if canonical in sanitized:
                    continue
                for alias in aliases:
                    if alias in src and src[alias] is not None:
                        val = src[alias]
                        if canonical == "keys" and isinstance(val, (list, tuple)):
                            sanitized[canonical] = "+".join(
                                _bound_str(item, 64) for item in val
                            )
                        elif canonical == "command" and isinstance(val, (list, tuple)):
                            sanitized[canonical] = " ".join(
                                _bound_str(item, 256) for item in val
                            )
                        else:
                            sanitized[canonical] = _bound_str(val)
                        break

            for meta_key in (
                "action",
                "operation",
                "tool",
                "risk_level",
                "workflow_id",
                "task_id",
            ):
                if (
                    meta_key not in sanitized
                    and meta_key in src
                    and src[meta_key] is not None
                ):
                    sanitized[meta_key] = _bound_str(src[meta_key], 256)

            for raw_k, raw_v in src.items():
                low_k = str(raw_k).lower()
                if any(secret in low_k for secret in SENSITIVE_REDACT_KEYS):
                    sanitized[str(raw_k)] = "[REDACTED]"
                elif (
                    isinstance(raw_v, (str, int, float, bool))
                    and str(raw_k) not in sanitized
                    and low_k not in ("content", "body", "html")
                ):
                    sanitized[str(raw_k)] = _bound_str(raw_v)

        if action and "action" not in sanitized:
            sanitized["action"] = _bound_str(action, 256)

        return sanitized

    @classmethod
    def _find_critical_violation(
        cls,
        action: str,
        ctx: Dict[str, Any],
    ) -> Optional[str]:
        """Return a violation reason if parameters or action violate unconditional safety policy."""
        norm_action = action.lower().replace("desktopaction: ", "").replace(" ", "_")

        # 1. Restricted hotkeys
        if "hotkey" in norm_action or "keys" in ctx or "hotkey" in ctx:
            raw_keys = ctx.get("keys") if "keys" in ctx else ctx.get("hotkey", "")
            if isinstance(raw_keys, (list, tuple)):
                keys = "+".join(str(k).strip().lower() for k in raw_keys)
            else:
                keys = re.sub(r"\s+", "", str(raw_keys or "").lower())
            for restricted in RESTRICTED_HOTKEYS:
                if restricted in keys:
                    return f"Restricted hotkey '{keys}' is blocked by Safe Mode."

        # 2. Restricted URLs (normalize with urlparse + data: prefix support)
        raw_url = str(ctx.get("url") or ctx.get("target_url") or "").strip().lower()
        if raw_url:
            try:
                parsed = urllib.parse.urlparse(raw_url)
                scheme_slash = f"{parsed.scheme}://" if parsed.scheme else ""
                scheme_colon = f"{parsed.scheme}:" if parsed.scheme else ""
            except Exception:
                scheme_slash = ""
                scheme_colon = ""
            for restricted_scheme in RESTRICTED_URL_SCHEMES:
                norm_restricted = restricted_scheme.lower()
                bare_scheme = norm_restricted.rstrip("/")
                if (
                    raw_url.startswith(norm_restricted)
                    or raw_url.startswith(bare_scheme)
                    or scheme_slash.startswith(norm_restricted)
                    or scheme_colon == bare_scheme
                ):
                    return f"Restricted URL scheme '{raw_url}' is blocked by Safe Mode."

        # 3. Destructive commands/scripts (whitespace normalized)
        raw_cmd = ctx.get("command") or ctx.get("cmd") or ctx.get("script") or ""
        cmd_for_eval = re.sub(r"\s+", " ", str(raw_cmd or action or "")).strip().lower()
        if raw_cmd or any(
            tok in norm_action for tok in ("terminal", "powershell", "shell", "command")
        ):
            for token in DESTRUCTIVE_COMMAND_TOKENS:
                if token in cmd_for_eval:
                    return (
                        f"Destructive command pattern '{token}' is blocked "
                        "unconditionally by Safe Mode."
                    )
            for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
                if pattern.search(cmd_for_eval):
                    return (
                        f"Destructive command pattern '{pattern.pattern}' is blocked "
                        "unconditionally by Safe Mode."
                    )

        # 4. Restricted sensitive system paths
        for path_key in (
            "path",
            "file_path",
            "target_path",
            "destination",
            "output_path",
            "filepath",
        ):
            if path_key in ctx and ctx[path_key]:
                norm_path = str(ctx[path_key]).replace("\\", "/").strip().lower()
                for sys_path in RESTRICTED_SYSTEM_PATHS:
                    if sys_path in norm_path:
                        return (
                            f"Restricted system path '{ctx[path_key]}' is blocked "
                            "unconditionally by Safe Mode."
                        )

        return None

    @classmethod
    def classify_risk(
        cls,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RiskLevel:
        """Classifies the risk level of an automation action."""
        ctx = cls.sanitize_context(context, action=action)
        norm_action = action.lower().replace("desktopaction: ", "").replace(" ", "_")

        # Hard security parameter/action violations are always CRITICAL
        if cls._find_critical_violation(action, ctx) is not None:
            return RiskLevel.CRITICAL

        declared = ctx.get("risk_level")
        base_risk: Optional[RiskLevel] = None

        # Lookup in standard map
        if norm_action in cls.ACTION_RISK_MAP:
            base_risk = cls.ACTION_RISK_MAP[norm_action]
        else:
            # Fuzzy lookup
            for key, risk in cls.ACTION_RISK_MAP.items():
                if key in norm_action or norm_action in key:
                    base_risk = risk
                    break

        if base_risk is None:
            # Fail closed: default to HIGH risk for unknown actions
            base_risk = RiskLevel.HIGH

        if declared:
            return max_risk(base_risk, declared)
        return base_risk

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
        raw_ctx = dict(context or {})
        norm_ctx = cls.sanitize_context(raw_ctx, action=action)
        mode_str = mode.value if hasattr(mode, "value") else str(mode).upper()
        risk = cls.classify_risk(action, norm_ctx)

        # Inherent parameter/policy violations are blocked unconditionally in ALL modes
        violation_reason = cls._find_critical_violation(action, norm_ctx)
        if violation_reason is not None:
            return PolicyDecision(
                allowed=False,
                requires_approval=True,
                risk_level=RiskLevel.CRITICAL,
                reason=violation_reason,
                action=action,
                metadata=raw_ctx,
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
                    metadata=raw_ctx,
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
                    metadata=raw_ctx,
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
                    metadata=raw_ctx,
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
                    metadata=raw_ctx,
                )

        elif mode_str == ExecutionMode.AUTONOMOUS.value:
            # CRITICAL operations never auto-bypass approval even in Autonomous Mode
            if risk == RiskLevel.CRITICAL:
                return PolicyDecision(
                    allowed=True,
                    requires_approval=True,
                    risk_level=risk,
                    reason=(
                        f"Critical-risk operation '{action}' requires explicit approval "
                        "even in Autonomous Mode."
                    ),
                    action=action,
                    metadata=raw_ctx,
                )
            return PolicyDecision(
                allowed=True,
                requires_approval=False,
                risk_level=risk,
                reason=f"Operation '{action}' permitted in Autonomous Mode.",
                action=action,
                metadata=raw_ctx,
            )

        # Unknown mode: Fail closed
        return PolicyDecision(
            allowed=False,
            requires_approval=True,
            risk_level=RiskLevel.CRITICAL,
            reason=f"Unknown mode '{mode_str}', action '{action}' blocked.",
            action=action,
            metadata=raw_ctx,
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


def build_task_permission_context(
    task: Any,
    payload: Optional[Dict[str, Any]] = None,
    tool_name: Optional[str] = None,
    workflow_id: Optional[Any] = None,
) -> tuple[str, Dict[str, Any]]:
    """Extract sanitized permission action name and execution context from a task."""
    raw_inputs: Dict[str, Any] = {}
    task_inputs = getattr(task, "inputs", None)
    if isinstance(task_inputs, dict):
        raw_inputs.update(task_inputs)
    if isinstance(payload, dict):
        raw_inputs.update(payload)

    for nested_key in ("params", "parameters", "arguments", "args"):
        nested = raw_inputs.get(nested_key)
        if isinstance(nested, dict):
            for k, v in nested.items():
                raw_inputs.setdefault(k, v)

    resolved_tool = str(
        tool_name or getattr(task, "required_tool", None) or "default_tool"
    )
    action_name = str(
        raw_inputs.get("action") or raw_inputs.get("operation") or resolved_tool
    )
    active_wf = workflow_id or getattr(task, "workflow_id", None)
    extra = {
        "task_id": str(getattr(task, "task_id", "")),
        "workflow_id": str(active_wf) if active_wf is not None else "",
        "tool": resolved_tool,
        "risk_level": str(getattr(task, "risk_level", "LOW") or "LOW"),
    }
    ctx = SafeExecutionPolicy.sanitize_context(
        raw_inputs, action=action_name, extra=extra
    )
    return action_name, ctx


def infer_task_permissions(
    tool: Any = None,
    task: Any = None,
    context: Optional[Dict[str, Any]] = None,
) -> list[str]:
    """Combine declared tool/task permissions with parameter-implied permissions."""
    perms: list[str] = []
    for candidate in (
        getattr(tool, "required_permissions", None) or [],
        getattr(task, "permissions", None) or [],
    ):
        for p in candidate:
            p_str = str(getattr(p, "value", p)).strip().upper()
            if p_str and p_str not in perms:
                perms.append(p_str)

    ctx = context or {}
    if not perms:
        if "command" in ctx or "script" in ctx:
            perms.append(PermissionType.TERMINAL.value)
        elif "url" in ctx:
            perms.append(PermissionType.BROWSER_ACCESS.value)
        elif "keys" in ctx:
            perms.append(PermissionType.DESKTOP_AUTOMATION.value)
        elif "path" in ctx:
            perms.append(PermissionType.FILE_SYSTEM.value)

    if not perms and task is not None:
        cat_val = str(
            getattr(
                getattr(task, "category", None), "value", getattr(task, "category", "")
            )
        ).upper()
        category_perm_map = {
            "FILE_SYSTEM": PermissionType.FILE_SYSTEM.value,
            "BROWSER": PermissionType.BROWSER_ACCESS.value,
            "TERMINAL": PermissionType.TERMINAL.value,
            "SHELL": PermissionType.TERMINAL.value,
            "POWERSHELL": PermissionType.POWERSHELL.value,
            "DESKTOP": PermissionType.DESKTOP_AUTOMATION.value,
            "AUTOMATION": PermissionType.DESKTOP_AUTOMATION.value,
        }
        if cat_val in category_perm_map:
            perms.append(category_perm_map[cat_val])

    if not perms:
        tool_id = (
            str(
                (ctx.get("tool") if isinstance(ctx, dict) else None)
                or getattr(task, "required_tool", "")
                or ""
            )
            .strip()
            .lower()
        )
        if any(k in tool_id for k in ("powershell",)):
            perms.append(PermissionType.POWERSHELL.value)
        elif any(k in tool_id for k in ("terminal", "shell", "cmd")):
            perms.append(PermissionType.TERMINAL.value)
        elif any(k in tool_id for k in ("desktop",)):
            perms.append(PermissionType.DESKTOP_AUTOMATION.value)
        elif any(k in tool_id for k in ("browser",)):
            perms.append(PermissionType.BROWSER_ACCESS.value)
        elif any(
            k in tool_id for k in ("file_explorer", "file_system", "file_manager")
        ):
            perms.append(PermissionType.FILE_SYSTEM.value)
        elif any(k in tool_id for k in ("admin", "registry")):
            perms.append(PermissionType.ADMINISTRATOR.value)

    return perms


def evaluate_task_risk_and_permissions(
    task: Any,
    tool: Any = None,
    inputs_override: Optional[Dict[str, Any]] = None,
    mode: ExecutionMode | str = ExecutionMode.SAFE,
) -> tuple[RiskLevel, set[str], PolicyDecision, Dict[str, Any]]:
    """Compute effective risk, required permission set, policy decision, and sanitized context."""
    action_name, ctx = build_task_permission_context(
        task=task,
        payload=inputs_override,
        tool_name=getattr(task, "required_tool", None),
        workflow_id=getattr(task, "workflow_id", None),
    )
    decision = SafeExecutionPolicy.evaluate(action=action_name, mode=mode, context=ctx)
    effective_risk = max_risk(getattr(task, "risk_level", "LOW"), decision.risk_level)
    perms = set(infer_task_permissions(tool=tool, task=task, context=ctx))
    return effective_risk, perms, decision, ctx
