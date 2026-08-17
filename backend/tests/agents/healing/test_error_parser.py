import subprocess
import uuid
from uuid import uuid4

import pytest
from shared.contracts.execution import (
    ExecutionResult,
    FailureType,
    TaskError,
    TaskFailureReport,
)
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.agent import HealingAgent, HealingRequest
from app.agents.healing.error_parser import ErrorCategory, ErrorParser, ParsedError
from app.agents.healing.models import (
    ErrorSeverity,
    ErrorSource,
)
from app.core.events.bus import EventBus
from app.core.exceptions import (
    PermissionDeniedException,
    ToolExecutionException,
    ToolNotFoundException,
)


def test_error_parser_permission_failure():
    parser = ErrorParser()
    report = TaskFailureReport(
        task_id=uuid4(),
        workflow_id=uuid4(),
        failure_type=FailureType.PERMISSION_DENIED,
        message="User rejected file system permission",
        retryability=False,
    )

    parsed: ParsedError = parser.parse(report)
    assert parsed.category == ErrorCategory.PERMISSIONS
    assert parsed.normalized_code == "PERMISSION_DENIED"
    assert parsed.is_transient is False


def test_error_parser_browser_timeout():
    parser = ErrorParser()
    err = TaskError(
        error_code="BROWSER_TIMEOUT",
        error_message="Playwright page navigation timed out after 30000ms",
        is_recoverable=True,
    )
    result = ExecutionResult(
        task_id=uuid4(),
        workflow_id=uuid4(),
        success=False,
        error=err,
    )

    parsed: ParsedError = parser.parse(result)
    assert parsed.category == ErrorCategory.BROWSER
    assert parsed.normalized_code == "BROWSER_TIMEOUT"
    assert parsed.is_transient is True


def test_error_parser_tool_unavailable():
    parser = ErrorParser()
    err = TaskError(
        error_code="TOOL_NOT_FOUND",
        error_message="Tool 'unsupported_tool' not registered",
        is_recoverable=False,
    )

    parsed: ParsedError = parser.parse(err)
    assert parsed.category == ErrorCategory.TOOL
    assert parsed.normalized_code == "TOOL_UNAVAILABLE"
    assert parsed.is_transient is False


def test_error_parser_exception_filesystem():
    parser = ErrorParser()
    exc = FileNotFoundError("No such file or directory: /tmp/data.json")

    parsed: ParsedError = parser.parse(exc)
    assert parsed.category == ErrorCategory.FILESYSTEM
    assert parsed.normalized_code == "FILESYSTEM_ERROR"


def test_error_parser_network_error():
    parser = ErrorParser()
    raw_str = "Network connection refused by host"

    parsed: ParsedError = parser.parse(raw_str)
    assert parsed.category == ErrorCategory.NETWORK
    assert parsed.normalized_code == "NETWORK_ERROR"
    assert parsed.is_transient is True


@pytest.fixture
def parser():
    return ErrorParser()


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def healing_agent(event_bus, parser):
    return HealingAgent(event_bus=event_bus, error_parser=parser)


def test_parse_timeout_errors(parser):
    # 1. Playwright / Browser timeout string
    raw_browser = "Playwright TimeoutError: Page navigation timed out after 30000ms"
    norm_browser = parser.parse(raw_browser)
    assert norm_browser.category == ErrorCategory.TIMEOUT
    assert norm_browser.source == ErrorSource.BROWSER
    assert norm_browser.severity == ErrorSeverity.MEDIUM
    assert norm_browser.is_retryable is True
    assert norm_browser.original_error == raw_browser

    # 2. Python TimeoutError exception
    raw_exc = TimeoutError("Operation timed out")
    norm_exc = parser.parse(raw_exc)
    assert norm_exc.category == ErrorCategory.TIMEOUT
    assert norm_exc.source == ErrorSource.SYSTEM
    assert norm_exc.is_retryable is True

    # 3. TaskFailureReport with TIMEOUT failure type
    report = TaskFailureReport(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        failure_type=FailureType.TIMEOUT,
        message="HTTP request timed out connecting to API",
        retryability=True,
        execution_context={"url": "https://api.example.com"},
    )
    norm_report = parser.parse(report)
    assert norm_report.category == ErrorCategory.TIMEOUT
    assert norm_report.source == ErrorSource.NETWORK
    assert norm_report.is_retryable is True
    assert norm_report.context["url"] == "https://api.example.com"


def test_parse_permission_errors(parser):
    # 1. PermissionDeniedException
    exc = PermissionDeniedException("User rejected PowerShell command execution")
    norm = parser.parse(exc)
    assert norm.category == ErrorCategory.PERMISSION_DENIED
    assert norm.source == ErrorSource.PERMISSION
    assert norm.severity == ErrorSeverity.HIGH
    assert norm.is_retryable is False
    assert norm.original_error == exc

    # 2. Dictionary with HTTP 403 Forbidden
    dict_err = {
        "error": "Forbidden",
        "message": "Access denied by permission policy",
        "status_code": 403,
    }
    norm_dict = parser.parse(dict_err)
    assert norm_dict.category == ErrorCategory.PERMISSION_DENIED
    assert norm_dict.source == ErrorSource.PERMISSION
    assert norm_dict.is_retryable is False
    assert norm_dict.context["status_code"] == 403


def test_parse_file_not_found_errors(parser):
    # 1. FileNotFoundError exception
    exc = FileNotFoundError("No such file or directory: 'output/report.pdf'")
    norm = parser.parse(exc)
    assert norm.category == ErrorCategory.FILE_NOT_FOUND
    assert norm.source == ErrorSource.FILESYSTEM
    assert norm.severity == ErrorSeverity.MEDIUM
    assert norm.is_retryable is False
    assert "report.pdf" in norm.message

    # 2. String file missing
    msg = "FileNotFoundError: Path does not exist /data/inputs.json"
    norm_str = parser.parse(msg)
    assert norm_str.category == ErrorCategory.FILE_NOT_FOUND
    assert norm_str.source == ErrorSource.FILESYSTEM
    assert norm_str.is_retryable is False


def test_parse_tool_unavailable_errors(parser):
    # 1. ToolNotFoundException
    exc = ToolNotFoundException("Required tool 'OCRTool' is not registered")
    norm = parser.parse(exc)
    assert norm.category == ErrorCategory.TOOL_UNAVAILABLE
    assert norm.source == ErrorSource.TOOL
    assert norm.severity == ErrorSeverity.HIGH
    assert norm.is_retryable is False

    # 2. TaskFailureReport with TOOL_UNAVAILABLE
    report = TaskFailureReport(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        failure_type=FailureType.TOOL_UNAVAILABLE,
        message="Tool unavailable in plugin registry",
        retryability=False,
    )
    norm_report = parser.parse(report)
    assert norm_report.category == ErrorCategory.TOOL_UNAVAILABLE
    assert norm_report.source == ErrorSource.TOOL
    assert norm_report.is_retryable is False


def test_parse_network_failures(parser):
    # 1. Connection error string
    msg = "Connection refused while attempting DNS lookup for host"
    norm = parser.parse(msg)
    assert norm.category == ErrorCategory.NETWORK_ERROR
    assert norm.source == ErrorSource.NETWORK
    assert norm.is_retryable is True

    # 2. HTTP 503 error
    dict_err = {
        "message": "HTTP 503 Service Unavailable backend error",
        "code": "HTTP_ERROR",
    }
    norm_http = parser.parse(dict_err)
    assert norm_http.category == ErrorCategory.NETWORK_ERROR
    assert norm_http.source == ErrorSource.NETWORK
    assert norm_http.is_retryable is True


def test_parse_invalid_artifact_errors(parser):
    # 1. TaskFailureReport with ARTIFACT_VALIDATION_FAILED
    report = TaskFailureReport(
        task_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        failure_type=FailureType.ARTIFACT_VALIDATION_FAILED,
        message="Generated PDF file is missing expected section markers",
        retryability=True,
    )
    norm = parser.parse(report)
    assert norm.category == ErrorCategory.INVALID_ARTIFACT
    assert norm.source == ErrorSource.WORKER
    assert norm.is_retryable is True


def test_parse_worker_and_execution_exceptions(parser):
    # 1. ToolExecutionException
    exc = ToolExecutionException("PowerShell script exited with non-zero status")
    norm = parser.parse(exc)
    assert norm.category == ErrorCategory.EXECUTION_ERROR
    assert norm.source == ErrorSource.POWERSHELL
    assert norm.is_retryable is True

    # 2. Subprocess CalledProcessError
    called_proc_err = subprocess.CalledProcessError(
        returncode=1,
        cmd="powershell.exe -Command Get-Process",
        output="Script execution failed",
    )
    norm_proc = parser.parse(called_proc_err)
    assert norm_proc.category == ErrorCategory.EXECUTION_ERROR
    assert norm_proc.source == ErrorSource.POWERSHELL
    assert norm_proc.context["exit_code"] == 1


def test_parse_unknown_exception(parser):
    class CustomUnmappedError(Exception):
        pass

    raw_exc = CustomUnmappedError("Unclassified internal anomaly")
    norm = parser.parse(raw_exc)
    assert norm.category == ErrorCategory.UNKNOWN
    assert norm.source == ErrorSource.UNKNOWN
    assert norm.severity == ErrorSeverity.HIGH
    assert norm.is_retryable is False
    assert norm.original_error == raw_exc


def test_parse_malformed_inputs(parser):
    # 1. None input
    norm_none = parser.parse(None)
    assert norm_none.category == ErrorCategory.UNKNOWN
    assert norm_none.source == ErrorSource.UNKNOWN
    assert norm_none.is_retryable is False
    assert norm_none.original_error is None

    # 2. Empty dictionary
    norm_dict = parser.parse({})
    assert norm_dict.category == ErrorCategory.UNKNOWN
    assert norm_dict.source == ErrorSource.UNKNOWN
    assert norm_dict.is_retryable is False

    # 3. Primitive integer input
    norm_int = parser.parse(12345)
    assert norm_int.category == ErrorCategory.UNKNOWN
    assert norm_int.source == ErrorSource.UNKNOWN
    assert norm_int.is_retryable is False
    assert norm_int.message == "12345"


def test_original_error_preservation(parser):
    dict_payload = {
        "error_code": "CUSTOM_ERR",
        "message": "Payload info intact",
        "debug_id": 99,
    }
    norm = parser.parse(dict_payload)
    assert norm.original_error == dict_payload
    assert norm.original_error["debug_id"] == 99


@pytest.mark.asyncio
async def test_healing_agent_integration(healing_agent):
    workflow_id = uuid.uuid4()
    task_id = uuid.uuid4()

    metadata = WorkflowMetadata(
        workflow_id=workflow_id,
        goal="Test Healing Integration",
        status=WorkflowStatus.RUNNING,
    )
    state = SharedWorkflowState(metadata=metadata)
    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="Scrape site",
        description="Scrape content from website",
        required_tool="browser",
        expected_output="HTML content",
        category=TaskCategory.WEB_SCRAPING,
        status=TaskStatus.RUNNING,
    )
    state.tasks[task_id] = task

    raw_error = "Playwright TimeoutError: Page navigation timed out after 30000ms"
    request = HealingRequest(
        task_id=task_id,
        workflow_id=workflow_id,
        raw_error=raw_error,
        attempt_number=1,
    )

    result = await healing_agent.execute(request=request, state=state)

    assert result.success is True
    assert result.root_cause == ErrorCategory.TIMEOUT.value
    assert result.recovery_strategy == "RETRY"
    assert len(result.replacement_tasks) == 1
    assert task.status == TaskStatus.WAITING
    assert task.retry_count == 1
