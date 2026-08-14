from typing import Any, Dict, Optional
from uuid import uuid4

from shared.contracts.execution import FailureType
from shared.contracts.recovery_plan import ErrorParserOutput, RootCauseAnalysis


class RootCauseAnalyzer:
    """
    Root Cause Analyzer component of the Healing Agent.
    Consumes ErrorParserOutput to diagnose the underlying root cause of a failure.
    """

    def analyze(
        self,
        parsed_error: ErrorParserOutput,
        task_context: Optional[Dict[str, Any]] = None,
    ) -> RootCauseAnalysis:
        """
        Diagnoses root cause from parsed error output and task context.
        """
        context = dict(parsed_error.parsed_details)
        if task_context:
            context.update(task_context)

        category = "UNKNOWN"
        summary = f"Failure diagnosed from message: {parsed_error.raw_error_message}"
        factors = []
        confidence = 0.9

        msg_lower = parsed_error.raw_error_message.lower()

        if (
            "missing_path" in context
            or "directory" in msg_lower
            or parsed_error.failure_type == FailureType.OUTPUT_MISSING
        ):
            category = "MISSING_DIRECTORY"
            missing_path = context.get("missing_path", "expected output path")
            summary = (
                f"Output directory or destination path does not exist: {missing_path}"
            )
            factors = [
                f"Path {missing_path} was not created prior to step execution",
                "FileSystem output check failed",
            ]
            confidence = 0.95
        elif (
            parsed_error.failure_type == FailureType.PERMISSION_DENIED
            or "permission" in msg_lower
            or "access denied" in msg_lower
        ):
            category = "PERMISSION_DENIED"
            summary = "Execution failed due to restricted OS or security permissions"
            factors = [
                "Action requires elevated permission",
                "Permission Manager denied or ungranted status",
            ]
            confidence = 0.95
        elif parsed_error.failure_type == FailureType.TIMEOUT or "timeout" in msg_lower:
            category = "TIMEOUT"
            summary = "Task execution exceeded allocated execution timeout threshold"
            factors = [
                "Process hung or slow response from underlying tool",
                "Timeout threshold reached",
            ]
            confidence = 0.9
        elif (
            parsed_error.failure_type == FailureType.ARTIFACT_VALIDATION_FAILED
            or "invalid artifact" in msg_lower
            or "corrupt" in msg_lower
        ):
            category = "ARTIFACT_INVALID"
            summary = "Generated artifact failed schema or structural validation checks"
            factors = [
                "Generated output file incomplete or empty",
                "Artifact content mismatch",
            ]
            confidence = 0.9
        elif (
            parsed_error.failure_type == FailureType.DEPENDENCY_FAILED
            or "dependency" in msg_lower
        ):
            category = "DEPENDENCY_FAILURE"
            summary = "Prerequisite task dependency failed or returned invalid outputs"
            factors = ["Parent task in dependency graph did not complete successfully"]
            confidence = 0.85
        elif parsed_error.failure_type == FailureType.TOOL_ERROR or "tool" in msg_lower:
            category = "TOOL_FAILURE"
            target_tool = context.get("target_tool", "requested tool")
            summary = f"Tool execution failed for {target_tool}"
            factors = [
                "Tool runtime exception or transient tool failure",
                "Tool internal error",
            ]
            confidence = 0.85
        elif not parsed_error.is_retryable:
            category = "UNRECOVERABLE"
            summary = "Failure flagged as non-retryable with no viable recovery options"
            factors = ["Explicit non-retryable failure flag set"]
            confidence = 1.0

        return RootCauseAnalysis(
            analysis_id=uuid4(),
            failure_id=parsed_error.failure_id,
            task_id=parsed_error.task_id,
            workflow_id=parsed_error.workflow_id,
            root_cause_summary=summary,
            category=category,
            confidence_score=confidence,
            underlying_factors=factors,
            context=context,
        )
