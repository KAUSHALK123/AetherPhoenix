from uuid import uuid4

import pytest
from backend.app.agents.healing.agent import HealingAgent
from backend.app.agents.healing.error_parser import ErrorParser
from backend.app.agents.healing.recovery_planner import RecoveryPlanner
from backend.app.agents.healing.root_cause_analyzer import RootCauseAnalyzer
from backend.app.agents.healing.validator import validate_recovery_plan
from shared.contracts.execution import FailureType, TaskFailureReport
from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.recovery_plan import (
    ErrorParserOutput,
    RecoveryAction,
    RecoveryPlan,
    RootCauseAnalysis,
)


@pytest.fixture
def base_ids():
    return {
        "task_id": uuid4(),
        "workflow_id": uuid4(),
        "failure_id": uuid4(),
    }


def test_missing_directory_recovery(base_ids):
    """Verify recovery plan generation for missing output directory."""
    failure_report = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.OUTPUT_MISSING,
        message="PPT output directory missing: /tmp/output/presentation",
        retryability=True,
        execution_context={"target_tool": "ppt_generator"},
    )

    error_parser = ErrorParser()
    root_cause_analyzer = RootCauseAnalyzer()
    planner = RecoveryPlanner()

    parsed_error = error_parser.parse(failure_report)
    root_cause = root_cause_analyzer.analyze(parsed_error)
    plan = planner.plan(parsed_error, root_cause)

    assert plan.is_viable is True
    assert plan.strategy_name == "MISSING_DIRECTORY_RECOVERY"
    assert len(plan.actions) == 4

    action_types = [act.action_type for act in plan.actions]
    assert action_types == [
        "VERIFY_DIRECTORY",
        "CREATE_DIRECTORY",
        "RETRY_TASK",
        "VALIDATE_ARTIFACT",
    ]

    # Verify action contracts
    create_dir_act = plan.actions[1]
    assert PermissionType.FILE_SYSTEM_WRITE in create_dir_act.required_permissions
    assert create_dir_act.risk_level == RiskLevel.LOW
    assert len(create_dir_act.preconditions) > 0
    assert len(create_dir_act.success_criteria) > 0
    assert len(create_dir_act.failure_criteria) > 0

    assert plan.validation_status == "VALID"
    assert PermissionType.FILE_SYSTEM_WRITE in plan.required_permissions


def test_retryable_tool_failure(base_ids):
    """Verify recovery plan for retryable tool error."""
    failure_report = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.TOOL_ERROR,
        message="Tool execution failed for browser_tool: network error",
        retryability=True,
        execution_context={"target_tool": "browser_tool"},
    )

    agent = HealingAgent()
    plan = agent.plan_recovery(failure_report)

    assert plan.is_viable is True
    assert plan.strategy_name == "TOOL_RETRY_RECOVERY"
    assert len(plan.actions) == 2
    assert plan.actions[0].action_type == "VERIFY_TOOL_HEALTH"
    assert plan.actions[1].action_type == "RETRY_TASK"
    assert plan.validation_status == "VALID"


def test_timeout_recovery(base_ids):
    """Verify recovery plan for task timeout."""
    failure_report = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.TIMEOUT,
        message="Task execution timeout exceeded after 30 seconds",
        retryability=True,
        execution_context={"target_tool": "web_scraper"},
    )

    agent = HealingAgent()
    plan = agent.plan_recovery(failure_report)

    assert plan.is_viable is True
    assert plan.strategy_name == "TIMEOUT_BACKOFF_RECOVERY"
    assert plan.actions[0].action_type == "ADJUST_TIMEOUT_PARAMS"
    assert plan.actions[1].action_type == "RETRY_TASK"
    assert plan.overall_risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)
    assert plan.validation_status == "VALID"


def test_permission_related_failure(base_ids):
    """Verify recovery plan for permission denied error."""
    failure_report = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.PERMISSION_DENIED,
        message="Permission denied: TERMINAL access restricted",
        retryability=True,
        execution_context={"required_permission": "TERMINAL"},
    )

    agent = HealingAgent()
    plan = agent.plan_recovery(failure_report)

    assert plan.is_viable is True
    assert plan.strategy_name == "PERMISSION_ELEVATION_RECOVERY"
    assert plan.actions[0].action_type == "REQUEST_PERMISSION"
    assert PermissionType.TERMINAL in plan.required_permissions
    assert plan.overall_risk_level == RiskLevel.HIGH
    assert plan.validation_status == "VALID"


def test_invalid_artifact_recovery(base_ids):
    """Verify recovery plan for invalid artifact failure."""
    failure_report = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.ARTIFACT_VALIDATION_FAILED,
        message="Invalid artifact: generated PDF file corrupted or empty",
        retryability=True,
        execution_context={
            "artifact_path": "/tmp/output.pdf",
            "target_tool": "pdf_generator",
        },
    )

    agent = HealingAgent()
    plan = agent.plan_recovery(failure_report)

    assert plan.is_viable is True
    assert plan.strategy_name == "ARTIFACT_REGENERATION_RECOVERY"
    assert [a.action_type for a in plan.actions] == [
        "CLEAN_INVALID_ARTIFACT",
        "RETRY_TASK",
        "VALIDATE_ARTIFACT",
    ]
    assert plan.validation_status == "VALID"


def test_failed_dependency_recovery(base_ids):
    """Verify recovery plan for failed dependency."""
    failure_report = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.DEPENDENCY_FAILED,
        message="Prerequisite task dependency failed",
        retryability=True,
        execution_context={"dependency_task_id": str(uuid4())},
    )

    agent = HealingAgent()
    plan = agent.plan_recovery(failure_report)

    assert plan.is_viable is True
    assert plan.strategy_name == "DEPENDENCY_RECOVERY"
    assert plan.actions[0].action_type == "RECOVER_DEPENDENCY"
    assert plan.validation_status == "VALID"


def test_no_viable_recovery(base_ids):
    """Verify handling when failure is unrecoverable or non-retryable."""
    failure_report = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.UNEXPECTED_EXCEPTION,
        message="Fatal unrecoverable error",
        retryability=False,
    )

    agent = HealingAgent()
    plan = agent.plan_recovery(failure_report)

    assert plan.is_viable is False
    assert plan.strategy_name == "NO_VIABLE_RECOVERY"
    assert len(plan.actions) == 0
    assert plan.validation_status == "VALID"


def test_high_risk_recovery(base_ids):
    """Verify high-risk recovery actions properly elevate overall risk level."""
    parsed_error = ErrorParserOutput(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.PERMISSION_DENIED,
        raw_error_message="Administrator permission required",
    )
    root_cause = RootCauseAnalysis(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        root_cause_summary="Requires administrator privileges",
        category="PERMISSION_DENIED",
    )

    planner = RecoveryPlanner()
    plan = planner.plan(
        parsed_error,
        root_cause,
        task_context={"required_permission": PermissionType.ADMINISTRATOR},
    )

    assert plan.overall_risk_level == RiskLevel.HIGH
    assert PermissionType.ADMINISTRATOR in plan.required_permissions


def test_invalid_recovery_plan_validation(base_ids):
    """Verify plan validator rejects invalid recovery plans (missing criteria or dangerous commands)."""
    # Test plan with invalid retries
    invalid_plan = RecoveryPlan(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        strategy_name="INVALID_PLAN",
        root_cause="Test failure",
        max_retries=10,  # exceeds max allowed 5
        actions=[
            RecoveryAction(
                action_type="BAD_ACTION",
                description="Action missing criteria",
                preconditions=[],  # missing
                success_criteria=[],  # missing
                failure_criteria=[],  # missing
            )
        ],
    )

    is_valid, errors = validate_recovery_plan(invalid_plan)
    assert is_valid is False
    assert invalid_plan.validation_status == "INVALID"
    assert len(errors) >= 4  # max_retries + 3 missing criteria checks

    # Test plan with dangerous command pattern in parameter
    dangerous_plan = RecoveryPlan(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        strategy_name="DANGEROUS_PLAN",
        root_cause="Test failure",
        max_retries=3,
        actions=[
            RecoveryAction(
                action_type="SHELL_EXEC",
                description="Dangerous command execution",
                preconditions=["Valid precondition"],
                success_criteria=["Valid success"],
                failure_criteria=["Valid failure"],
                action_parameters={"cmd": "rm -rf /"},
            )
        ],
    )

    is_valid, errors = validate_recovery_plan(dangerous_plan)
    assert is_valid is False
    assert dangerous_plan.validation_status == "INVALID"
    assert any("unrestricted/dangerous command pattern" in err for err in errors)


def test_healing_integration_non_executing(base_ids):
    """Verify Healing Core consumes root cause output and produces validated plan without executing actions."""
    failure_report = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.OUTPUT_MISSING,
        message="PPT output directory missing: /var/output",
        retryability=True,
    )

    healing_agent = HealingAgent()
    healing_result, recovery_plan = healing_agent.handle_failure(failure_report)

    # Healing result contains high level status
    assert healing_result.success is True
    assert healing_result.recovery_strategy == "MISSING_DIRECTORY_RECOVERY"
    assert healing_result.task_id == base_ids["task_id"]
    assert (
        healing_result.replacement_tasks == []
    )  # No direct execution / workflow mutation

    # Recovery plan contains full structured details
    assert recovery_plan.validation_status == "VALID"
    assert len(recovery_plan.actions) > 0
