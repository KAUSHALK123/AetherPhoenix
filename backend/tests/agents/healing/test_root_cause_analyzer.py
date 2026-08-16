from uuid import uuid4

import pytest
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.agents.healing.error_parser import ErrorCategory, ParsedError
from app.agents.healing.root_cause_analyzer import (
    RootCauseAnalysis,
    RootCauseAnalyzer,
    RootCauseCategory,
)


@pytest.fixture
def dummy_state():
    return SharedWorkflowState(metadata=WorkflowMetadata(goal="Test Root Cause"))


def create_task(workflow_id) -> Task:
    return Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Dummy Task",
        description="Testing task",
        required_tool="browser_tool",
        category=TaskCategory.OTHER,
        expected_output="dummy output",
        status=TaskStatus.FAILED,
    )


def test_root_cause_permission_denied(dummy_state):
    analyzer = RootCauseAnalyzer()
    task = create_task(dummy_state.metadata.workflow_id)
    parsed = ParsedError(
        category=ErrorCategory.PERMISSIONS,
        normalized_code="PERMISSION_DENIED",
        raw_message="Access denied",
        is_transient=False,
    )

    rc: RootCauseAnalysis = analyzer.analyze(parsed, task, dummy_state)
    assert rc.category == RootCauseCategory.PERMISSION
    assert rc.is_recoverable is False
    assert rc.recommended_strategy == "REQUEST_PERMISSION_AGAIN"


def test_root_cause_tool_unavailable(dummy_state):
    analyzer = RootCauseAnalyzer()
    task = create_task(dummy_state.metadata.workflow_id)
    parsed = ParsedError(
        category=ErrorCategory.TOOL,
        normalized_code="TOOL_UNAVAILABLE",
        raw_message="Tool missing",
        is_transient=False,
    )

    rc: RootCauseAnalysis = analyzer.analyze(parsed, task, dummy_state)
    assert rc.category == RootCauseCategory.TOOL
    assert rc.is_recoverable is True
    assert rc.recommended_strategy == "ALTERNATIVE_TOOL"


def test_root_cause_network_timeout(dummy_state):
    analyzer = RootCauseAnalyzer()
    task = create_task(dummy_state.metadata.workflow_id)
    parsed = ParsedError(
        category=ErrorCategory.NETWORK,
        normalized_code="NETWORK_TIMEOUT",
        raw_message="Connection timed out",
        is_transient=True,
    )

    rc: RootCauseAnalysis = analyzer.analyze(parsed, task, dummy_state)
    assert rc.category == RootCauseCategory.NETWORK
    assert rc.is_recoverable is True
    assert rc.recommended_strategy == "RETRY"


def test_root_cause_destructive_safety_override(dummy_state):
    analyzer = RootCauseAnalyzer()
    task = create_task(dummy_state.metadata.workflow_id)
    task.risk_level = "HIGH"
    parsed = ParsedError(
        category=ErrorCategory.UNKNOWN,
        normalized_code="EXECUTION_ERROR",
        raw_message="Unknown destructive operation failure",
        is_transient=False,
    )

    rc: RootCauseAnalysis = analyzer.analyze(parsed, task, dummy_state)
    assert rc.is_recoverable is False
    assert rc.recommended_strategy == "ESCALATE_USER"
"""Unit and integration tests for Root Cause Analyzer and Healing Agent."""

from uuid import uuid4

import pytest
from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import (
    ExecutionResult,
    FailureType,
    TaskError,
    TaskFailureReport,
)
from shared.contracts.healing import RootCauseCategory, RootCauseResult
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowMetadata

from app.agents.healing.agent import HealingAgent
from app.agents.healing.root_cause_analyzer import RootCauseAnalyzer


@pytest.fixture
def analyzer() -> RootCauseAnalyzer:
    return RootCauseAnalyzer()


@pytest.fixture
def healing_agent(analyzer: RootCauseAnalyzer) -> HealingAgent:
    return HealingAgent(analyzer=analyzer)


def create_sample_task(
    task_name: str = "Test Task",
    required_tool: str = "document_generator",
    expected_output: str = "output.pptx",
    dependencies: list = None,
    category: TaskCategory = TaskCategory.PPT_GENERATION,
    description: str = "Test task description",
) -> Task:
    return Task(
        task_id=uuid4(),
        workflow_id=uuid4(),
        task_name=task_name,
        description=description,
        category=category,
        required_tool=required_tool,
        expected_output=expected_output,
        dependencies=dependencies or [],
    )


# 1. Missing output directory
def test_missing_output_directory(analyzer: RootCauseAnalyzer):
    task = create_sample_task(
        task_name="Generate PPT Presentation",
        expected_output="C:/nonexistent_dir_12345/presentation.pptx",
    )
    msg = (
        "FileNotFoundError: [Errno 2] No such file or directory: "
        "'C:/nonexistent_dir_12345/presentation.pptx'"
    )
    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        failure_type=FailureType.TOOL_ERROR,
        message=msg,
        retryability=False,
        execution_context={"output_path": "C:/nonexistent_dir_12345/presentation.pptx"},
    )

    result = analyzer.analyze(report=report, task=task)

    assert result.category == RootCauseCategory.INFRASTRUCTURE
    assert result.likely_root_cause == "OUTPUT_DIRECTORY_MISSING"
    assert result.confidence_score >= 0.90
    assert result.is_confident is True
    assert len(result.evidence.missing_paths) > 0


# 2. Tool unavailable
def test_tool_unavailable(analyzer: RootCauseAnalyzer):
    task = create_sample_task(required_tool="custom_tool")
    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        failure_type=FailureType.TOOL_UNAVAILABLE,
        message="Tool 'custom_tool' is unavailable or not registered in runtime.",
        retryability=False,
    )
    tool_info = {"name": "custom_tool", "state": "UNAVAILABLE", "health": "UNHEALTHY"}

    result = analyzer.analyze(report=report, task=task, tool_info=tool_info)

    assert result.category == RootCauseCategory.TOOL
    assert result.likely_root_cause == "TOOL_UNAVAILABLE"
    assert result.confidence_score >= 0.90
    assert result.is_confident is True


# 3. Timeout failure
def test_timeout_failure(analyzer: RootCauseAnalyzer):
    task = create_sample_task()
    msg = (
        "Task exceeded configured timeout of 300 seconds (took 305.20s). "
        "Playwright timeout."
    )
    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        failure_type=FailureType.TIMEOUT,
        message=msg,
        retryability=True,
    )

    result = analyzer.analyze(report=report, task=task)

    assert result.category == RootCauseCategory.RUNTIME
    assert result.likely_root_cause == "EXECUTION_TIMEOUT"
    assert result.confidence_score >= 0.85
    assert result.is_confident is True


# 4. Permission denial
def test_permission_denial(analyzer: RootCauseAnalyzer):
    task = create_sample_task()
    msg = "Permission denied: User rejected consent for file modification."
    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        failure_type=FailureType.PERMISSION_DENIED,
        message=msg,
        retryability=False,
    )

    result = analyzer.analyze(report=report, task=task)

    assert result.category == RootCauseCategory.PERMISSION
    assert result.likely_root_cause == "PERMISSION_DENIED"
    assert result.confidence_score >= 0.90
    assert result.is_confident is True


# 5. Failed dependency
def test_failed_dependency(analyzer: RootCauseAnalyzer):
    parent_id = uuid4()
    parent_task = Task(
        task_id=parent_id,
        workflow_id=uuid4(),
        task_name="Parent Task",
        description="Parent task description",
        category=TaskCategory.WEB_RESEARCH,
        required_tool="web_research",
        expected_output="research_data.json",
        status=TaskStatus.FAILED,
    )
    task = create_sample_task(dependencies=[parent_id])

    state = SharedWorkflowState(metadata=WorkflowMetadata(goal="Test Workflow"))
    state.tasks[parent_id] = parent_task
    state.tasks[task.task_id] = task

    dep_msg = (
        f"Required parent dependency '{parent_task.task_name}' ({parent_id}) failed."
    )
    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        failure_type=FailureType.DEPENDENCY_FAILED,
        message=dep_msg,
        retryability=False,
    )

    result = analyzer.analyze(report=report, task=task, state=state)

    assert result.category == RootCauseCategory.WORKFLOW
    assert result.likely_root_cause == "FAILED_DEPENDENCY"
    assert result.confidence_score >= 0.90
    assert result.is_confident is True


# 6. Invalid artifact (0-byte file)
def test_invalid_artifact(tmp_path, analyzer: RootCauseAnalyzer):
    empty_file = tmp_path / "empty_output.pdf"
    empty_file.write_text("")  # 0 bytes

    task = create_sample_task()
    artifact = Artifact(
        workflow_id=task.workflow_id,
        task_id=task.task_id,
        name="Test PDF",
        artifact_type=ArtifactType.PDF,
        filepath=str(empty_file),
    )
    exec_result = ExecutionResult(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        success=False,
        artifacts=[artifact],
        error=TaskError(
            error_code="ARTIFACT_VALIDATION_FAILED",
            error_message="Artifact file is empty (0 bytes).",
        ),
    )

    result = analyzer.analyze(task=task, result=exec_result)

    assert result.category == RootCauseCategory.INFRASTRUCTURE
    assert result.likely_root_cause == "INVALID_ARTIFACT"
    assert result.confidence_score >= 0.90
    assert result.is_confident is True


# 7. Network failure
def test_network_failure(analyzer: RootCauseAnalyzer):
    task = create_sample_task(
        required_tool="web_research",
        category=TaskCategory.WEB_RESEARCH,
    )
    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        failure_type=FailureType.TOOL_ERROR,
        message="httpx.ConnectError: Connection refused: name or service not known",
        retryability=True,
    )

    result = analyzer.analyze(report=report, task=task)

    assert result.category == RootCauseCategory.NETWORK
    assert result.likely_root_cause == "NETWORK_UNAVAILABLE"
    assert result.confidence_score >= 0.85
    assert result.is_confident is True


# 8. Unknown root cause (insufficient evidence)
def test_unknown_root_cause(analyzer: RootCauseAnalyzer):
    task = create_sample_task()
    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        failure_type=FailureType.WORKER_FAILURE,
        message="Generic execution failed.",
        retryability=True,
    )

    result = analyzer.analyze(report=report, task=task)

    assert result.category == RootCauseCategory.UNKNOWN
    assert result.likely_root_cause == "UNKNOWN_ROOT_CAUSE"
    assert result.confidence_score < 0.50
    assert result.is_confident is False
    assert len(result.alternative_causes) > 0


# 9. Low-confidence diagnosis & alternative causes representation
def test_low_confidence_diagnosis(analyzer: RootCauseAnalyzer):
    task = create_sample_task()
    result = analyzer.analyze(
        failure_type=FailureType.UNEXPECTED_EXCEPTION,
        error_message="Internal error code 0x80004005",
        task=task,
    )

    assert result.confidence_score < 0.50
    assert result.is_confident is False
    assert result.category == RootCauseCategory.UNKNOWN
    assert len(result.alternative_causes) >= 2
    for alt in result.alternative_causes:
        assert alt.confidence_score < 0.50
        assert alt.explanation != ""


# 10. Healing Core integration test
@pytest.mark.asyncio
async def test_healing_agent_integration(healing_agent: HealingAgent):
    task = create_sample_task(
        task_name="Generate Presentation",
        expected_output="C:/invalid_path_xyz9/presentation.pptx",
    )
    err_msg = (
        "FileNotFoundError: No such file or directory: "
        "'C:/invalid_path_xyz9/presentation.pptx'"
    )
    report = TaskFailureReport(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        failure_type=FailureType.TOOL_ERROR,
        message=err_msg,
        retryability=False,
    )

    analysis_result = await healing_agent.analyze_failure(report=report, task=task)

    assert isinstance(analysis_result, RootCauseResult)
    assert analysis_result.task_id == task.task_id
    assert analysis_result.workflow_id == task.workflow_id
    assert analysis_result.category == RootCauseCategory.INFRASTRUCTURE
    assert analysis_result.likely_root_cause == "OUTPUT_DIRECTORY_MISSING"

    # Also test BaseAgent execute contract interface
    exec_analysis = await healing_agent.execute(task, report)
    assert isinstance(exec_analysis, RootCauseResult)
    assert exec_analysis.likely_root_cause == "OUTPUT_DIRECTORY_MISSING"
