from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.recovery_plan import (
    RecoveryAction,
    RecoveryPlan,
)

from app.agents.healing.validator import validate_recovery_plan

RISK_HIERARCHY = {
    RiskLevel.SAFE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


class RecoveryStrategy(str, Enum):
    """Legacy recovery strategy labels retained for public API compatibility."""

    RETRY = "RETRY"
    RESTART_TOOL = "RESTART_TOOL"
    WAIT = "WAIT"
    ALTERNATIVE_TOOL = "ALTERNATIVE_TOOL"
    ALTERNATIVE_WEBSITE = "ALTERNATIVE_WEBSITE"
    ALTERNATIVE_API = "ALTERNATIVE_API"
    REQUEST_PERMISSION_AGAIN = "REQUEST_PERMISSION_AGAIN"
    ESCALATE_USER = "ESCALATE_USER"
    CANCEL_WORKFLOW = "CANCEL_WORKFLOW"


def _determine_highest_risk(risk_levels: List[RiskLevel]) -> RiskLevel:
    if not risk_levels:
        return RiskLevel.SAFE
    return max(risk_levels, key=lambda risk: RISK_HIERARCHY.get(risk, 0))


class RecoveryPlanner:
    """
    Recovery Planner module for Healing Agent.
    Generates structured recovery strategies based on failure data and root
    cause diagnosis.
    Note: The Recovery Planner ONLY plans and validates strategies.
    It DOES NOT execute them.
    """

    def plan(
        self,
        parsed_error: Any = None,
        root_cause: Any = None,
        task_context: Optional[Dict[str, Any]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> RecoveryPlan:
        """
        Generates an ordered, validated RecoveryPlan based on parsed error
        and root cause analysis.
        """
        is_legacy = False
        root_cause_obj = None
        task_obj = None

        if parsed_error is not None and (
            hasattr(parsed_error, "likely_root_cause") or 
            hasattr(parsed_error, "root_cause_summary") or 
            hasattr(parsed_error, "recommended_strategy")
        ):
            is_legacy = True
            root_cause_obj = parsed_error
            task_obj = root_cause
        elif parsed_error is None and root_cause is not None and (
            hasattr(root_cause, "likely_root_cause") or 
            hasattr(root_cause, "root_cause_summary") or 
            hasattr(root_cause, "recommended_strategy")
        ):
            is_legacy = True
            root_cause_obj = root_cause
            task_obj = kwargs.get("task")

        if is_legacy:
            is_retryable = getattr(root_cause_obj, "is_recoverable", True)
            target_tool = (
                getattr(task_obj, "required_tool", None)
                if task_obj
                else None
            )
            parsed_details = {"target_tool": target_tool}
            failure_id = getattr(
                root_cause_obj,
                "failure_id",
                getattr(root_cause_obj, "analysis_id", uuid4()),
            )
            task_id = getattr(root_cause_obj, "task_id", uuid4())
            workflow_id = getattr(root_cause_obj, "workflow_id", uuid4())

            class CompatParsedError:
                def __init__(
                    self,
                    is_retryable: bool,
                    parsed_details: dict,
                    failure_id: Any,
                    task_id: Any,
                    workflow_id: Any,
                ) -> None:
                    self.is_retryable = is_retryable
                    self.parsed_details = parsed_details
                    self.failure_id = failure_id
                    self.task_id = task_id
                    self.workflow_id = workflow_id

            parsed_error = CompatParsedError(
                is_retryable,
                parsed_details,
                failure_id,
                task_id,
                workflow_id,
            )
            root_cause = root_cause_obj
            task_context = {}

        context = dict(parsed_error.parsed_details)
        if root_cause.context:
            context.update(root_cause.context)
        if task_context:
            context.update(task_context)

        # Check for unviable recovery conditions
        if (
            (
                not parsed_error.is_retryable
                and root_cause.category
                not in ("MISSING_DIRECTORY", "PERMISSION_DENIED")
            )
            or root_cause.category == "UNRECOVERABLE"
            or root_cause.confidence_score < 0.3
        ):
            unviable_plan = RecoveryPlan(
                plan_id=uuid4(),
                failure_id=parsed_error.failure_id,
                task_id=parsed_error.task_id,
                workflow_id=parsed_error.workflow_id,
                strategy_name="NO_VIABLE_RECOVERY",
                root_cause=root_cause.root_cause_summary,
                actions=[],
                overall_risk_level=RiskLevel.SAFE,
                is_viable=False,
                max_retries=1,
                task_context=context,
            )
            validate_recovery_plan(unviable_plan)
            return unviable_plan

        # Generate strategy actions based on diagnosis
        actions: List[RecoveryAction] = []
        strategy_name = "GENERIC_RETRY_STRATEGY"
        max_retries = 3

        if root_cause.category == "MISSING_DIRECTORY":
            strategy_name = "MISSING_DIRECTORY_RECOVERY"
            target_path = context.get(
                "missing_path", context.get("output_path", "expected_directory")
            )
            target_tool = context.get("target_tool", "document_generator")

            actions = [
                RecoveryAction(
                    action_type="VERIFY_DIRECTORY",
                    description=(
                        f"Verify existence and access permissions: {target_path}"
                    ),
                    target_tool="file_system",
                    required_capabilities=["file_system_read"],
                    required_permissions=[PermissionType.FILE_SYSTEM],
                    risk_level=RiskLevel.SAFE,
                    preconditions=["Target directory path identified"],
                    success_criteria=["Path status inspected successfully"],
                    failure_criteria=["Path inspection error"],
                    action_parameters={"path": target_path},
                ),
                RecoveryAction(
                    action_type="CREATE_DIRECTORY",
                    description=(
                        f"Create missing directory structure at path: {target_path}"
                    ),
                    target_tool="file_system",
                    required_capabilities=["file_system_write"],
                    required_permissions=[PermissionType.FILE_SYSTEM_WRITE],
                    risk_level=RiskLevel.LOW,
                    preconditions=[
                        "Parent path exists or writable",
                        "File system write permission granted",
                    ],
                    success_criteria=["Directory created successfully"],
                    failure_criteria=["Directory creation failed or permission denied"],
                    action_parameters={"path": target_path, "create_parents": True},
                ),
                RecoveryAction(
                    action_type="RETRY_TASK",
                    description=f"Re-run execution task using tool: {target_tool}",
                    target_tool=target_tool,
                    required_capabilities=["task_execution"],
                    required_permissions=[],
                    risk_level=RiskLevel.LOW,
                    preconditions=["Target output directory verified to exist"],
                    success_criteria=[
                        "Task re-execution completed with zero exit code"
                    ],
                    failure_criteria=["Task re-execution threw exception"],
                    action_parameters={"tool_name": target_tool},
                ),
                RecoveryAction(
                    action_type="VALIDATE_ARTIFACT",
                    description=(
                        "Validate generated output artifact structure and presence"
                    ),
                    target_tool=target_tool,
                    required_capabilities=["artifact_validation"],
                    required_permissions=[],
                    risk_level=RiskLevel.SAFE,
                    preconditions=["Task re-execution completed"],
                    success_criteria=[
                        "Output artifact exists and passes validation checks"
                    ],
                    failure_criteria=["Output artifact missing or empty"],
                    action_parameters={"path": target_path},
                ),
            ]

        elif root_cause.category == "PERMISSION_DENIED":
            strategy_name = "PERMISSION_ELEVATION_RECOVERY"
            requested_perm = context.get("required_permission")
            if isinstance(requested_perm, str):
                try:
                    requested_perm = PermissionType(requested_perm)
                except ValueError:
                    requested_perm = None
            if not isinstance(requested_perm, PermissionType):
                matched_perm = None
                for pt in PermissionType:
                    if pt.value.lower() in parsed_error.raw_error_message.lower():
                        matched_perm = pt
                        break
                requested_perm = (
                    matched_perm if matched_perm else PermissionType.FILE_SYSTEM_WRITE
                )

            perm_risk = (
                RiskLevel.HIGH
                if requested_perm
                in (
                    PermissionType.ADMINISTRATOR,
                    PermissionType.REGISTRY,
                    PermissionType.TERMINAL,
                )
                else RiskLevel.MEDIUM
            )

            actions = [
                RecoveryAction(
                    action_type="REQUEST_PERMISSION",
                    description=(
                        f"Submit request for permission: {requested_perm.value}"
                    ),
                    target_tool="permission_manager",
                    required_capabilities=["permission_request"],
                    required_permissions=[requested_perm],
                    risk_level=perm_risk,
                    preconditions=["Permission request rationale formulated"],
                    success_criteria=["Permission granted by Permission Manager"],
                    failure_criteria=["Permission request rejected"],
                    action_parameters={
                        "permission_type": requested_perm.value,
                        "reason": (
                            "Recovery planner requested permission for failed task"
                        ),
                    },
                ),
                RecoveryAction(
                    action_type="RETRY_TASK",
                    description="Re-run failed task after permission approval",
                    target_tool=context.get("target_tool"),
                    required_capabilities=["task_execution"],
                    required_permissions=[requested_perm],
                    risk_level=RiskLevel.LOW,
                    preconditions=[
                        f"Permission {requested_perm.value} status is GRANTED"
                    ],
                    success_criteria=["Task completed without permission errors"],
                    failure_criteria=["Task failed despite permission grant"],
                    action_parameters={},
                ),
            ]

        elif root_cause.category == "TIMEOUT":
            strategy_name = "TIMEOUT_BACKOFF_RECOVERY"
            target_tool = context.get("target_tool", "browser")

            actions = [
                RecoveryAction(
                    action_type="ADJUST_TIMEOUT_PARAMS",
                    description=(
                        "Increase task timeout threshold and clear transient resources"
                    ),
                    target_tool=target_tool,
                    required_capabilities=["configuration"],
                    required_permissions=[],
                    risk_level=RiskLevel.LOW,
                    preconditions=["Task supports dynamic timeout override"],
                    success_criteria=["Timeout parameter increased by factor of 2"],
                    failure_criteria=["Timeout configuration invalid"],
                    action_parameters={"timeout_multiplier": 2.0},
                ),
                RecoveryAction(
                    action_type="RETRY_TASK",
                    description=(
                        f"Re-run task with extended timeout using tool {target_tool}"
                    ),
                    target_tool=target_tool,
                    required_capabilities=["task_execution"],
                    required_permissions=[],
                    risk_level=RiskLevel.MEDIUM,
                    preconditions=["Extended timeout applied"],
                    success_criteria=["Task completed within extended window"],
                    failure_criteria=["Task timed out again after extended window"],
                    action_parameters={"timeout_seconds": 60},
                ),
            ]

        elif root_cause.category == "ARTIFACT_INVALID":
            strategy_name = "ARTIFACT_REGENERATION_RECOVERY"
            artifact_path = context.get("artifact_path", "output_artifact")

            actions = [
                RecoveryAction(
                    action_type="CLEAN_INVALID_ARTIFACT",
                    description=(
                        f"Clean up corrupted/invalid artifact file at: {artifact_path}"
                    ),
                    target_tool="file_system",
                    required_capabilities=["file_system_write"],
                    required_permissions=[PermissionType.FILE_SYSTEM_WRITE],
                    risk_level=RiskLevel.LOW,
                    preconditions=["Artifact file exists and marked invalid"],
                    success_criteria=["Invalid file removed or reset"],
                    failure_criteria=["File removal error"],
                    action_parameters={"path": artifact_path},
                ),
                RecoveryAction(
                    action_type="RETRY_TASK",
                    description="Re-run generation task with clean output parameters",
                    target_tool=context.get("target_tool"),
                    required_capabilities=["task_execution"],
                    required_permissions=[],
                    risk_level=RiskLevel.LOW,
                    preconditions=["Previous corrupted artifact cleared"],
                    success_criteria=["Generation task finished successfully"],
                    failure_criteria=["Generation task threw exception"],
                    action_parameters={},
                ),
                RecoveryAction(
                    action_type="VALIDATE_ARTIFACT",
                    description=(
                        "Validate structural integrity of newly generated artifact"
                    ),
                    target_tool="validator",
                    required_capabilities=["artifact_validation"],
                    required_permissions=[],
                    risk_level=RiskLevel.SAFE,
                    preconditions=["New artifact file generated"],
                    success_criteria=["Artifact schema and content valid"],
                    failure_criteria=["New artifact failed validation"],
                    action_parameters={"path": artifact_path},
                ),
            ]

        elif root_cause.category == "DEPENDENCY_FAILURE":
            strategy_name = "DEPENDENCY_RECOVERY"
            dep_task_id = context.get("dependency_task_id", "prerequisite_task")

            actions = [
                RecoveryAction(
                    action_type="RECOVER_DEPENDENCY",
                    description=(
                        f"Attempt recovery of prerequisite task: {dep_task_id}"
                    ),
                    target_tool="orchestrator",
                    required_capabilities=["task_orchestration"],
                    required_permissions=[],
                    risk_level=RiskLevel.MEDIUM,
                    preconditions=["Prerequisite task ID identified"],
                    success_criteria=["Prerequisite task state resolved to COMPLETED"],
                    failure_criteria=["Prerequisite task recovery failed"],
                    action_parameters={"dependency_task_id": str(dep_task_id)},
                ),
                RecoveryAction(
                    action_type="RETRY_TASK",
                    description="Re-run dependent task after prerequisite resolution",
                    target_tool=context.get("target_tool"),
                    required_capabilities=["task_execution"],
                    required_permissions=[],
                    risk_level=RiskLevel.LOW,
                    preconditions=["Dependency state verified COMPLETED"],
                    success_criteria=["Task execution completed successfully"],
                    failure_criteria=["Task execution failed"],
                    action_parameters={},
                ),
            ]

        else:  # TOOL_FAILURE or UNKNOWN
            strategy_name = "TOOL_RETRY_RECOVERY"
            target_tool = context.get("target_tool", "default_tool")

            actions = [
                RecoveryAction(
                    action_type="VERIFY_TOOL_HEALTH",
                    description=(
                        f"Check tool availability and state for tool: {target_tool}"
                    ),
                    target_tool="tool_registry",
                    required_capabilities=["tool_status_check"],
                    required_permissions=[],
                    risk_level=RiskLevel.SAFE,
                    preconditions=["Tool registered in registry"],
                    success_criteria=["Tool state verified healthy"],
                    failure_criteria=["Tool marked unserviceable"],
                    action_parameters={"tool_name": target_tool},
                ),
                RecoveryAction(
                    action_type="RETRY_TASK",
                    description=(
                        f"Re-run task using tool: {target_tool} with backoff delay"
                    ),
                    target_tool=target_tool,
                    required_capabilities=["task_execution"],
                    required_permissions=[],
                    risk_level=RiskLevel.LOW,
                    preconditions=["Tool health verified"],
                    success_criteria=["Task completed without tool errors"],
                    failure_criteria=["Tool error repeated on retry"],
                    action_parameters={"backoff_delay_seconds": 2},
                ),
            ]

        # Aggregate required permissions, tools, capabilities, and risk level
        all_perms: List[PermissionType] = []
        all_tools: List[str] = []
        all_caps: List[str] = []
        risk_levels: List[RiskLevel] = []

        for act in actions:
            for p in act.required_permissions:
                if p not in all_perms:
                    all_perms.append(p)
            if act.target_tool and act.target_tool not in all_tools:
                all_tools.append(act.target_tool)
            for c in act.required_capabilities:
                if c not in all_caps:
                    all_caps.append(c)
            risk_levels.append(act.risk_level)

        overall_risk = _determine_highest_risk(risk_levels)

        plan = RecoveryPlan(
            plan_id=uuid4(),
            failure_id=parsed_error.failure_id,
            task_id=parsed_error.task_id,
            workflow_id=parsed_error.workflow_id,
            strategy_name=strategy_name,
            root_cause=root_cause.root_cause_summary,
            actions=actions,
            overall_risk_level=overall_risk,
            required_permissions=all_perms,
            required_tools=all_tools,
            required_capabilities=all_caps,
            max_retries=max_retries,
            is_viable=True,
            task_context=context,
        )

        validate_recovery_plan(plan)
        return plan
