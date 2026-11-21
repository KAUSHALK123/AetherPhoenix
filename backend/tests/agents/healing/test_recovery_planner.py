from uuid import uuid4

import pytest
from shared.contracts.execution import FailureType, TaskFailureReport
from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.recovery_plan import (
    ErrorParserOutput,
    RecoveryAction,
    RecoveryPlan,
    RootCauseAnalysis,
)

from app.agents.healing.agent import HealingAgent
from app.agents.healing.error_parser import ErrorParser
from app.agents.healing.recovery_planner import (
    RecoveryPlanner,
)
from app.agents.healing.root_cause_analyzer import (
    RootCauseAnalyzer,
)
from app.agents.healing.validator import validate_recovery_plan


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
        message="Tool execution failed for browser_tool: tool unavailable",
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
    """
    Verify plan validator rejects invalid recovery plans.
    """
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
    assert any("dangerous command pattern" in err for err in errors)


def test_healing_integration_non_executing(base_ids):
    """
    Verify Healing Core consumes root cause output and produces validated plan.
    """
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


def test_recovery_planner_low_confidence_boundary_030(base_ids):
    """
    Unit test for B1: Confidence <= 0.30 boundary produces NO_VIABLE_RECOVERY.
    """
    error_parser = ErrorParser()
    planner = RecoveryPlanner()

    failure_report = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.TOOL_UNAVAILABLE,
        message="Unrecognized error with low diagnostic confidence",
        retryability=True,
    )
    parsed_error = error_parser.parse(failure_report)

    # Test confidence exactly 0.30
    rc_030 = RootCauseAnalysis(
        analysis_id=uuid4(),
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        category="TOOL",
        root_cause_summary="Generic uncertain tool fault",
        diagnostic_explanation="Explanation with low confidence",
        confidence_score=0.30,
        is_recoverable=True,
    )

    plan = planner.plan(parsed_error, rc_030)
    assert plan.strategy_name == "NO_VIABLE_RECOVERY"
    assert plan.is_viable is False
    assert len(plan.actions) == 0

    # Also verify confidence 0.25 <= 0.30 produces NO_VIABLE_RECOVERY
    rc_025 = RootCauseAnalysis(
        analysis_id=uuid4(),
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        category="TOOL",
        root_cause_summary="Generic uncertain tool fault",
        diagnostic_explanation="Explanation with low confidence",
        confidence_score=0.25,
        is_recoverable=True,
    )
    plan_025 = planner.plan(parsed_error, rc_025)
    assert plan_025.strategy_name == "NO_VIABLE_RECOVERY"
    assert plan_025.is_viable is False


def test_missing_resource_protected_path_rejected_by_plan_validation(base_ids):
    """
    B2 Safety test: Missing Resource recovery for protected locations
    (e.g., C:\\Windows\\System32\\... or /etc/...) must be rejected by plan validation.
    """
    from pathlib import Path
    error_parser = ErrorParser()
    planner = RecoveryPlanner()

    protected_paths = [
        "C:\\Windows\\System32\\forbidden_phoenix_test",
        "C:\\Windows\\SysWOW64\\forbidden_phoenix_test",
        "/etc/passwd_missing_dir",
        "/.ssh/authorized_keys_dir",
    ]

    for p in protected_paths:
        path_obj = Path(p)
        assert not path_obj.exists(), f"Precondition failed: {p} must not exist"

        failure_report = TaskFailureReport(
            failure_id=base_ids["failure_id"],
            task_id=base_ids["task_id"],
            workflow_id=base_ids["workflow_id"],
            failure_type=FailureType.OUTPUT_MISSING,
            message=f"Output directory missing: {p}",
            retryability=True,
            execution_context={"missing_path": p, "target_tool": "document_generator"},
        )
        parsed_error = error_parser.parse(failure_report)

        rc_infra = RootCauseAnalysis(
            analysis_id=uuid4(),
            failure_id=base_ids["failure_id"],
            task_id=base_ids["task_id"],
            workflow_id=base_ids["workflow_id"],
            category="MISSING_DIRECTORY",
            root_cause_summary="Directory missing on filesystem",
            diagnostic_explanation="Target directory does not exist",
            confidence_score=0.90,
            is_recoverable=True,
        )

        plan = planner.plan(parsed_error, rc_infra)
        assert plan.is_viable is False, f"Expected {p} to be rejected as non-viable"
        assert plan.validation_status == "INVALID"
        assert len(plan.validation_errors) > 0
        assert any("SafeExecutionPolicy" in err or "Restricted system path" in err for err in plan.validation_errors)

        # Confirm path was NEVER created on disk
        assert not path_obj.exists(), f"Violation: Protected path {p} was created on disk!"


@pytest.mark.asyncio
async def test_missing_resource_outside_workspace_rejected_and_never_created(base_ids):
    """
    B2 Safety test: FileSystemExecutor and SelfHealingLoop enforce workspace boundary.
    Any path outside workspace is rejected and never created on disk.
    """
    from pathlib import Path
    from app.agents.healing.self_healing_loop import SelfHealingLoop
    from app.tools.filesystem.executor import FileSystemExecutor
    from app.tools.filesystem.models import CreateDirectoryRequest
    from shared.contracts.task import Task, TaskStatus, TaskPriority, TaskCategory
    from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata, WorkflowStatus

    outside_dir = Path("D:/forbidden_outside_workspace_phoenix_dir_xyz")
    assert not outside_dir.exists(), "Precondition failed: outside directory already exists"

    # 1. Direct tool executor level enforcement
    fs_executor = FileSystemExecutor()
    with pytest.raises(ValueError, match="outside the permitted workspace directory"):
        await fs_executor.create_directory(CreateDirectoryRequest(path=str(outside_dir), create_parents=True))
    assert not outside_dir.exists(), "Violation: directory outside workspace was created on disk!"

    # 2. SelfHealingLoop end-to-end enforcement with protected path
    sys32_dir = Path("C:/Windows/System32/phoenix_never_create_sys32_test")
    assert not sys32_dir.exists(), "Precondition failed: sys32 directory already exists"

    loop = SelfHealingLoop()
    task = Task(
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        task_name="protected_path_task",
        description="Task attempting to heal protected system32 path",
        category=TaskCategory.FILE_SYSTEM,
        required_tool="document_generator",
        inputs={"path": str(sys32_dir)},
        expected_output="output.pdf",
        status=TaskStatus.RUNNING,
    )
    sws = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=base_ids["workflow_id"],
            user_id="audit_user",
            session_id="audit_session",
            name="audit_workflow",
            goal="Test protected directory rejection",
        ),
        status=WorkflowStatus.RUNNING,
    )
    fr = TaskFailureReport(
        failure_id=base_ids["failure_id"],
        task_id=base_ids["task_id"],
        workflow_id=base_ids["workflow_id"],
        failure_type=FailureType.OUTPUT_MISSING,
        message=f"Output directory missing: {sys32_dir}",
        retryability=True,
        execution_context={"missing_path": str(sys32_dir), "target_tool": "document_generator"},
    )

    result = await loop.process_failure(task, fr, sws)
    assert result.success is False, "Expected self healing to fail on protected path"
    assert not sys32_dir.exists(), "Violation: Protected path was created on disk!"


