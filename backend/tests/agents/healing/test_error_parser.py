from uuid import uuid4

from shared.contracts.execution import (
    ExecutionResult,
    FailureType,
    TaskError,
    TaskFailureReport,
)

from app.agents.healing.error_parser import ErrorCategory, ErrorParser, ParsedError


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
