import copy
import re
from typing import Any, List, Optional, Set, Tuple

from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.recovery_plan import RecoveryPlan

from app.core.permissions.models import ExecutionMode
from app.core.permissions.policies import (
    SafeExecutionPolicy,
    evaluate_task_risk_and_permissions,
    risk_rank,
)

UNRESTRICTED_COMMAND_PATTERNS = [
    r"rm\s+-rf",
    r"del\s+/f\s+/s\s+/q",
    r"format\s+[a-z]:",
    r"drop\s+database",
    r"shutdown",
    r"mkfs",
    r"chmod\s+777\s+/",
]

PRIVILEGED_ESCALATION_PERMS: Set[str] = {
    "ADMINISTRATOR",
    "ADMIN_PRIVILEGE",
    "REGISTRY",
    "REGISTRY_EDIT",
    "TERMINAL",
    "TERMINAL_EXECUTE",
    "POWERSHELL",
    "POWERSHELL_EXECUTE",
}

PROTECTED_TASK_IDENTITY_KEYS: Set[str] = {
    "task_id",
    "workflow_id",
    "attempt_history",
    "current_attempt_id",
}


def simulate_task_patch(original_task: Any, updated_params: dict[str, Any]) -> Any:
    """Return a deep-copied Task with recovery updated_task_params merged safely."""
    patched = original_task.model_copy(deep=True)
    raw_inputs = dict(getattr(patched, "inputs", None) or {})
    param_keys = (
        "command",
        "cmd",
        "shell_command",
        "script",
        "code",
        "url",
        "target_url",
        "keys",
        "hotkey",
        "path",
        "file_path",
        "target_path",
        "destination",
        "action",
        "operation",
    )

    for key, value in updated_params.items():
        if key in PROTECTED_TASK_IDENTITY_KEYS:
            continue
        if key == "inputs" and isinstance(value, dict):
            merged_inputs = copy.deepcopy(raw_inputs)
            merged_inputs.update(copy.deepcopy(value))
            patched.inputs = merged_inputs
            raw_inputs = merged_inputs
        elif key in param_keys:
            raw_inputs[key] = copy.deepcopy(value)
            patched.inputs = raw_inputs
        elif hasattr(patched, key):
            setattr(patched, key, copy.deepcopy(value))
    return patched


def _check_parameters_against_policy(
    params: dict[str, Any],
    action_label: str,
    mode: ExecutionMode | str,
    prefix: str,
) -> List[str]:
    """Validate arbitrary parameter dicts against SafeExecutionPolicy & command regexes."""
    errors: List[str] = []
    for param_key, param_val in params.items():
        if isinstance(param_val, str):
            for pattern in UNRESTRICTED_COMMAND_PATTERNS:
                if re.search(pattern, param_val, re.IGNORECASE):
                    errors.append(
                        f"{prefix} parameter '{param_key}' contains "
                        f"dangerous command pattern: '{param_val}'."
                    )

    sanitized = SafeExecutionPolicy.sanitize_context(params, action=action_label)
    decision = SafeExecutionPolicy.evaluate(
        action=action_label,
        mode=mode,
        context=sanitized,
    )
    if not decision.allowed:
        errors.append(
            f"{prefix} blocked by execution policy ({decision.risk_level.value}): "
            f"{decision.reason} (dangerous command pattern / restricted parameter)"
        )
    elif decision.risk_level == RiskLevel.CRITICAL:
        errors.append(
            f"{prefix} reaches CRITICAL risk for action '{action_label}', "
            "which recovery cannot authorize."
        )
    return errors


def validate_retry_plan_security(
    plan: Any,
    original_task: Optional[Any] = None,
    mode: ExecutionMode | str = ExecutionMode.SAFE,
    original_baseline: Optional[Tuple[RiskLevel, Set[str]]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate monotonic privilege invariance and parameter safety on any recovery plan
    (covers both shared.contracts.recovery_plan.RecoveryPlan and shared.contracts.retry.RecoveryPlan).
    """
    errors: List[str] = []

    if original_baseline is not None:
        orig_risk, orig_perms = original_baseline
    elif original_task is not None:
        orig_risk, orig_perms, _, _ = evaluate_task_risk_and_permissions(
            original_task, mode=mode
        )
    else:
        orig_risk, orig_perms = None, None

    # 1. Validate updated_task_params (used by RetryEngine.execute_retry / execute_recovery)
    updated_params = getattr(plan, "updated_task_params", None)
    if isinstance(updated_params, dict) and updated_params:
        for protected_key in PROTECTED_TASK_IDENTITY_KEYS:
            if protected_key in updated_params:
                errors.append(
                    f"updated_task_params attempts to overwrite protected field '{protected_key}'."
                )

        # Evaluate raw updated_task_params payloads directly
        flat_patch = dict(updated_params)
        if isinstance(updated_params.get("inputs"), dict):
            flat_patch.update(updated_params["inputs"])
        patch_action = str(
            flat_patch.get("action")
            or updated_params.get("required_tool")
            or (getattr(original_task, "required_tool", None) if original_task else None)
            or "retry_patch"
        )
        errors.extend(
            _check_parameters_against_policy(
                flat_patch,
                action_label=patch_action,
                mode=mode,
                prefix="updated_task_params",
            )
        )

        # Compare patched task risk & permissions monotonically against original task
        if original_task is not None and orig_risk is not None and orig_perms is not None:
            patched_task = simulate_task_patch(original_task, updated_params)
            patched_risk, patched_perms, patched_decision, _ = (
                evaluate_task_risk_and_permissions(patched_task, mode=mode)
            )
            if not patched_decision.allowed:
                errors.append(
                    f"Patched task blocked by SafeExecutionPolicy: {patched_decision.reason}"
                )
            if risk_rank(patched_risk) > risk_rank(orig_risk):
                errors.append(
                    f"Monotonic privilege violation: patched task risk '{patched_risk.value}' "
                    f"exceeds original task risk '{orig_risk.value}'."
                )
            extra_perms = patched_perms - orig_perms
            if extra_perms:
                errors.append(
                    f"Monotonic privilege violation: patched task introduces unapproved "
                    f"permissions {sorted(extra_perms)} not in original set {sorted(orig_perms)}."
                )

    # 2. Validate replacement_tasks
    replacement_tasks = getattr(plan, "replacement_tasks", None) or []
    for idx, rep_task in enumerate(replacement_tasks):
        rep_ref = f"ReplacementTask[{idx}] ({getattr(rep_task, 'required_tool', 'unknown')})"
        rep_inputs = getattr(rep_task, "inputs", None) or {}
        rep_action = str(
            (rep_inputs.get("action") if isinstance(rep_inputs, dict) else None)
            or getattr(rep_task, "required_tool", None)
            or "replacement_task"
        )
        if isinstance(rep_inputs, dict):
            errors.extend(
                _check_parameters_against_policy(
                    rep_inputs,
                    action_label=rep_action,
                    mode=mode,
                    prefix=rep_ref,
                )
            )

        rep_risk, rep_perms, rep_decision, _ = evaluate_task_risk_and_permissions(
            rep_task, mode=mode
        )
        if not rep_decision.allowed:
            errors.append(
                f"{rep_ref} blocked by SafeExecutionPolicy: {rep_decision.reason}"
            )
        if rep_risk == RiskLevel.CRITICAL:
            errors.append(
                f"{rep_ref} evaluated at CRITICAL risk, which self-healing cannot execute."
            )

        if original_task is not None and orig_risk is not None and orig_perms is not None:
            if getattr(rep_task, "workflow_id", None) != getattr(
                original_task, "workflow_id", None
            ):
                errors.append(
                    f"{rep_ref} workflow_id mismatch against original task."
                )
            if risk_rank(rep_risk) > risk_rank(orig_risk):
                errors.append(
                    f"{rep_ref} violates monotonic privilege invariance: "
                    f"risk '{rep_risk.value}' exceeds original risk '{orig_risk.value}'."
                )
            extra_rep_perms = rep_perms - orig_perms
            if extra_rep_perms:
                errors.append(
                    f"{rep_ref} introduces unapproved permissions {sorted(extra_rep_perms)} "
                    f"beyond original permissions {sorted(orig_perms)}."
                )

    # Deduplicate errors preserving order
    seen: Set[str] = set()
    unique_errors: List[str] = []
    for err in errors:
        if err not in seen:
            seen.add(err)
            unique_errors.append(err)
    return len(unique_errors) == 0, unique_errors


def validate_recovery_plan(
    plan: RecoveryPlan,
    original_task: Optional[Any] = None,
    mode: ExecutionMode | str = ExecutionMode.SAFE,
    original_baseline: Optional[Tuple[RiskLevel, Set[str]]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validates a RecoveryPlan against structural, security, parameter-policy,
    and monotonic privilege-invariance constraints.
    Returns a tuple of (is_valid: bool, validation_errors: List[str]).
    Also updates plan.validation_status, plan.validation_errors, and plan.is_viable.
    """
    errors: List[str] = []

    if original_baseline is not None:
        orig_risk, orig_perms = original_baseline
    elif original_task is not None:
        orig_risk, orig_perms, _, _ = evaluate_task_risk_and_permissions(
            original_task, mode=mode
        )
    else:
        orig_risk, orig_perms = None, None

    # Bounded retries check
    if plan.max_retries < 1 or plan.max_retries > 5:
        errors.append(
            f"Invalid max_retries: {plan.max_retries}. Must be between 1 and 5."
        )

    strategy_name = str(getattr(plan, "strategy_name", "") or "").upper()

    if plan.is_viable:
        if not plan.actions:
            errors.append(
                "Viable recovery plan must contain at least one recovery action."
            )

        for idx, action in enumerate(plan.actions):
            action_ref = f"Action[{idx}] ({action.action_type})"

            # Check preconditions
            if not action.preconditions:
                errors.append(f"{action_ref} is missing required preconditions.")

            # Check success criteria
            if not action.success_criteria:
                errors.append(f"{action_ref} is missing required success criteria.")

            # Check failure criteria
            if not action.failure_criteria:
                errors.append(f"{action_ref} is missing required failure criteria.")

            # Security check: unrestricted command patterns & SafeExecutionPolicy params
            act_params = dict(action.action_parameters or {})
            act_label = str(action.target_tool or action.action_type or "recovery_action")
            for param_key, param_val in act_params.items():
                if isinstance(param_val, str):
                    for pattern in UNRESTRICTED_COMMAND_PATTERNS:
                        if re.search(pattern, param_val, re.IGNORECASE):
                            errors.append(
                                f"{action_ref} parameter '{param_key}' contains "
                                f"dangerous command pattern: '{param_val}'."
                            )

            sanitized_act_ctx = SafeExecutionPolicy.sanitize_context(
                act_params, action=act_label
            )
            violation = SafeExecutionPolicy._find_critical_violation(
                act_label, sanitized_act_ctx
            )
            if violation is not None:
                errors.append(
                    f"{action_ref} violates SafeExecutionPolicy: {violation} "
                    "(dangerous command pattern)"
                )

            # Validate risk level type & forbid CRITICAL recovery actions
            if not isinstance(action.risk_level, RiskLevel):
                errors.append(
                    f"{action_ref} has invalid risk level: {action.risk_level}."
                )
            elif action.risk_level == RiskLevel.CRITICAL:
                errors.append(
                    f"{action_ref} declares CRITICAL risk, which self-healing cannot authorize."
                )

            if action.target_tool:
                tool_risk = SafeExecutionPolicy.classify_risk(
                    action.target_tool, sanitized_act_ctx
                )
                if tool_risk == RiskLevel.CRITICAL:
                    errors.append(
                        f"{action_ref} targets CRITICAL tool '{action.target_tool}'."
                    )
                elif (
                    orig_risk is not None
                    and action.action_type == "RETRY_TASK"
                    and risk_rank(tool_risk) > risk_rank(orig_risk)
                ):
                    errors.append(
                        f"{action_ref} targets higher-risk tool '{action.target_tool}' "
                        f"({tool_risk.value} > {orig_risk.value})."
                    )

            # Validate permission types & block silent privilege escalation
            for perm in action.required_permissions:
                if not isinstance(perm, PermissionType):
                    errors.append(
                        f"{action_ref} contains invalid permission type: {perm}."
                    )
                elif (
                    orig_perms is not None
                    and strategy_name != "PERMISSION_ELEVATION_RECOVERY"
                ):
                    perm_str = perm.value.upper()
                    if (
                        perm_str in PRIVILEGED_ESCALATION_PERMS
                        and perm_str not in orig_perms
                    ):
                        errors.append(
                            f"{action_ref} attempts privileged escalation to '{perm_str}' "
                            f"beyond original task permissions {sorted(orig_perms)}."
                        )

    # Validate updated_task_params & replacement_tasks monotonically
    _, sec_errors = validate_retry_plan_security(
        plan,
        original_task=original_task,
        mode=mode,
        original_baseline=original_baseline,
    )
    errors.extend(sec_errors)

    # Deduplicate errors while preserving order
    seen_errs: Set[str] = set()
    final_errors: List[str] = []
    for err in errors:
        if err not in seen_errs:
            seen_errs.add(err)
            final_errors.append(err)

    is_valid = len(final_errors) == 0
    plan.validation_status = "VALID" if is_valid else "INVALID"
    plan.validation_errors = final_errors
    if not is_valid:
        plan.is_viable = False

    return is_valid, final_errors
