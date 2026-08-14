import re
from typing import Any, Dict, Optional

from shared.contracts.execution import FailureType, TaskFailureReport
from shared.contracts.recovery_plan import ErrorParserOutput


class ErrorParser:
    """
    Error Parser component of the Healing Agent.
    Consumes raw failure reports and extracts structured error details.
    """

    def parse(
        self,
        failure_report: TaskFailureReport,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> ErrorParserOutput:
        """
        Parses a TaskFailureReport into structured ErrorParserOutput.
        """
        message = failure_report.message or ""
        context = failure_report.execution_context or {}
        if additional_context:
            context.update(additional_context)

        parsed_details: Dict[str, Any] = {
            "original_failure_type": failure_report.failure_type.value,
            "raw_message": message,
        }
        if context:
            parsed_details.update(context)

        error_code = "UNKNOWN_ERROR"
        failure_type = failure_report.failure_type

        # Extract path if missing directory/file
        missing_dir_match = re.search(
            r"(?:directory|path|folder)\s+['\"]?([^'\"\s]+)['\"]?\s+"
            r"(?:does not exist|missing|not found)",
            message,
            re.IGNORECASE,
        ) or re.search(
            r"FileNotFoundError:.*['\"]([^'\"]+)['\"]",
            message,
            re.IGNORECASE,
        )
        if missing_dir_match:
            parsed_details["missing_path"] = missing_dir_match.group(1)
            error_code = "DIRECTORY_NOT_FOUND"

        # Extract tool name if tool error
        tool_match = re.search(
            r"tool\s+['\"]?(\w+)['\"]?",
            message,
            re.IGNORECASE,
        )
        if tool_match:
            parsed_details["target_tool"] = tool_match.group(1)

        if failure_type == FailureType.OUTPUT_MISSING:
            error_code = "OUTPUT_MISSING"
        elif failure_type == FailureType.TIMEOUT:
            error_code = "TIMEOUT_EXCEEDED"
        elif failure_type == FailureType.PERMISSION_DENIED:
            error_code = "PERMISSION_DENIED"
        elif failure_type == FailureType.TOOL_ERROR:
            error_code = "TOOL_EXECUTION_ERROR"
        elif failure_type == FailureType.ARTIFACT_VALIDATION_FAILED:
            error_code = "ARTIFACT_INVALID"
        elif failure_type == FailureType.DEPENDENCY_FAILED:
            error_code = "DEPENDENCY_FAILURE"

        return ErrorParserOutput(
            failure_id=failure_report.failure_id,
            task_id=failure_report.task_id,
            workflow_id=failure_report.workflow_id,
            failure_type=failure_type,
            raw_error_message=message,
            error_code=error_code,
            parsed_details=parsed_details,
            is_retryable=failure_report.retryability,
        )
