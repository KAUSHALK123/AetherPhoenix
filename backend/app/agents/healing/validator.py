import re
from typing import List, Tuple

from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.recovery_plan import RecoveryPlan

UNRESTRICTED_COMMAND_PATTERNS = [
    r"rm\s+-rf",
    r"del\s+/f\s+/s\s+/q",
    r"format\s+[a-z]:",
    r"drop\s+database",
    r"shutdown",
    r"mkfs",
    r"chmod\s+777\s+/",
]


def validate_recovery_plan(plan: RecoveryPlan) -> Tuple[bool, List[str]]:
    """
    Validates a RecoveryPlan against structural, security, and safety constraints.
    Returns a tuple of (is_valid: bool, validation_errors: List[str]).
    Also updates plan.validation_status and plan.validation_errors.
    """
    errors: List[str] = []

    # Bounded retries check
    if plan.max_retries < 1 or plan.max_retries > 5:
        errors.append(
            f"Invalid max_retries: {plan.max_retries}. Must be between 1 and 5."
        )

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

            # Security check: Check for unrestricted shell command parameters
            for param_key, param_val in action.action_parameters.items():
                if isinstance(param_val, str):
                    for pattern in UNRESTRICTED_COMMAND_PATTERNS:
                        if re.search(pattern, param_val, re.IGNORECASE):
                            errors.append(
                                f"{action_ref} parameter '{param_key}' contains "
                                f"dangerous command pattern: '{param_val}'."
                            )

            # Validate risk level type
            if not isinstance(action.risk_level, RiskLevel):
                errors.append(
                    f"{action_ref} has invalid risk level: {action.risk_level}."
                )

            # Validate permission types
            for perm in action.required_permissions:
                if not isinstance(perm, PermissionType):
                    errors.append(
                        f"{action_ref} contains invalid permission type: {perm}."
                    )

    is_valid = len(errors) == 0
    plan.validation_status = "VALID" if is_valid else "INVALID"
    plan.validation_errors = errors

    return is_valid, errors
