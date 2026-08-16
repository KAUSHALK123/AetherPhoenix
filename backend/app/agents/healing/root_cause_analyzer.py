"""Root Cause Analyzer Service.

Examines normalized execution failures, task metadata, execution context,
logs, tool health, and workflow dependencies to identify the most likely
underlying root cause of a task failure.
"""

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from shared.contracts.execution import (
    ExecutionResult,
    FailureType,
    TaskFailureReport,
)
from shared.contracts.healing import (
    AlternativeCause,
    DiagnosticEvidence,
    RootCauseCategory,
    RootCauseResult,
)
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    """
    Analyzes execution failures and provides structured diagnostic results
    and confidence scores to the Recovery Planner.
    """

    # Error regex pattern definitions
    PATH_ERROR_PATTERNS = [
        re.compile(r"file\s*not\s*found", re.IGNORECASE),
        re.compile(r"no\s*such\s*file\s*or\s*directory", re.IGNORECASE),
        re.compile(r"directory\s*not\s*found", re.IGNORECASE),
        re.compile(r"path\s*does\s*not\s*exist", re.IGNORECASE),
        re.compile(r"cannot\s*find\s*the\s*path", re.IGNORECASE),
    ]

    NETWORK_ERROR_PATTERNS = [
        re.compile(r"connection\s*refused", re.IGNORECASE),
        re.compile(r"network\s*is\s*unreachable", re.IGNORECASE),
        re.compile(r"dns\s*resolution\s*failed", re.IGNORECASE),
        re.compile(r"name\s*or\s*service\s*not\s*known", re.IGNORECASE),
        re.compile(r"connecterror", re.IGNORECASE),
        re.compile(r"socketerror", re.IGNORECASE),
        re.compile(r"err_internet_disconnected", re.IGNORECASE),
        re.compile(r"host\s*unreachable", re.IGNORECASE),
    ]

    TIMEOUT_PATTERNS = [
        re.compile(r"timeout", re.IGNORECASE),
        re.compile(r"timed\s*out", re.IGNORECASE),
        re.compile(r"exceeded\s*configured\s*timeout", re.IGNORECASE),
        re.compile(r"playwright\s*timeout", re.IGNORECASE),
        re.compile(r"navigation\s*timeout", re.IGNORECASE),
    ]

    PERMISSION_PATTERNS = [
        re.compile(r"permission\s*denied", re.IGNORECASE),
        re.compile(r"access\s*denied", re.IGNORECASE),
        re.compile(r"unauthorized", re.IGNORECASE),
        re.compile(r"user\s*rejected", re.IGNORECASE),
        re.compile(r"forbidden", re.IGNORECASE),
        re.compile(r"401\s*unauthorized", re.IGNORECASE),
        re.compile(r"403\s*forbidden", re.IGNORECASE),
    ]

    TOOL_PATTERNS = [
        re.compile(r"tool\s*not\s*found", re.IGNORECASE),
        re.compile(r"tool\s*disabled", re.IGNORECASE),
        re.compile(r"tool\s*unavailable", re.IGNORECASE),
        re.compile(r"capability\s*not\s*supported", re.IGNORECASE),
    ]

    def __init__(self, confidence_threshold: float = 0.5) -> None:
        self.confidence_threshold = confidence_threshold

    def analyze(
        self,
        report: Optional[TaskFailureReport] = None,
        task: Optional[Task] = None,
        result: Optional[ExecutionResult] = None,
        state: Optional[SharedWorkflowState] = None,
        tool_info: Optional[Dict[str, Any]] = None,
        logs: Optional[List[str]] = None,
        failure_type: Optional[FailureType | str] = None,
        error_message: Optional[str] = None,
    ) -> RootCauseResult:
        """
        Main analysis entrypoint. Performs structured diagnosis.

        Returns a RootCauseResult with root cause, confidence score, evidence,
        and alternatives.
        """
        # Resolve IDs
        task_id = (
            report.task_id
            if report
            else (task.task_id if task else (result.task_id if result else uuid4()))
        )
        workflow_id = (
            report.workflow_id
            if report
            else (
                task.workflow_id
                if task
                else (result.workflow_id if result else uuid4())
            )
        )

        # Extract combined failure message & failure type
        msg_parts = []
        if report and report.message:
            msg_parts.append(report.message)
        if error_message:
            msg_parts.append(error_message)
        if result and result.error and result.error.error_message:
            msg_parts.append(result.error.error_message)
        combined_message = " | ".join(msg_parts) if msg_parts else ""

        f_type = (
            report.failure_type
            if report
            else (
                FailureType(failure_type)
                if isinstance(failure_type, str)
                and failure_type in FailureType.__members__
                else (
                    failure_type
                    if isinstance(failure_type, FailureType)
                    else FailureType.UNEXPECTED_EXCEPTION
                )
            )
        )

        # Combine all available logs
        all_logs: List[str] = []
        if logs:
            all_logs.extend(logs)
        if result and result.logs:
            all_logs.extend(result.logs)

        # Initialize evidence container
        evidence = DiagnosticEvidence(
            observed_failure_type=str(f_type.value) if f_type else None,
            observed_error_message=combined_message or None,
            inspected_logs_count=len(all_logs),
        )

        # 1. Dependency Analysis
        dep_cause = self._inspect_dependencies(task, state, evidence)

        # 2. Filesystem & Path Analysis
        fs_cause = self._inspect_filesystem_and_paths(
            combined_message, task, result, evidence
        )

        # 3. Tool Health & Availability Analysis
        tool_cause = self._inspect_tool_information(
            task, result, tool_info, combined_message, f_type, evidence
        )

        # 4. Pattern & Log Analysis (Timeout, Network, Permission)
        pattern_cause = self._inspect_patterns_and_logs(
            combined_message, f_type, all_logs, evidence
        )

        # 5. Synthesize primary root cause and confidence score
        (
            likely_cause,
            category,
            confidence,
            explanation,
            alternatives,
        ) = self._synthesize_diagnosis(
            dep_cause=dep_cause,
            fs_cause=fs_cause,
            tool_cause=tool_cause,
            pattern_cause=pattern_cause,
            f_type=f_type,
            combined_message=combined_message,
            evidence=evidence,
        )

        is_confident = confidence >= self.confidence_threshold

        return RootCauseResult(
            task_id=task_id,
            workflow_id=workflow_id,
            likely_root_cause=likely_cause,
            category=category,
            confidence_score=round(confidence, 2),
            is_confident=is_confident,
            diagnostic_explanation=explanation,
            evidence=evidence,
            alternative_causes=alternatives,
            analyzed_at=datetime.now(timezone.utc),
        )

    def _inspect_dependencies(
        self,
        task: Optional[Task],
        state: Optional[SharedWorkflowState],
        evidence: DiagnosticEvidence,
    ) -> Optional[Tuple[str, RootCauseCategory, float, str]]:
        """Inspects parent tasks to detect dependency failures."""
        if not task or not state:
            return None

        for dep_id in task.dependencies:
            dep_task = state.tasks.get(dep_id)
            if dep_task:
                evidence.dependency_status[str(dep_id)] = {
                    "name": dep_task.task_name,
                    "status": str(dep_task.status),
                }
                if dep_task.status == TaskStatus.FAILED:
                    evidence.matched_patterns.append("FAILED_PARENT_DEPENDENCY")
                    return (
                        "FAILED_DEPENDENCY",
                        RootCauseCategory.WORKFLOW,
                        0.95,
                        (
                            f"Parent dependency task '{dep_task.task_name}' "
                            f"({dep_id}) failed before execution."
                        ),
                    )
                elif dep_task.status == TaskStatus.CANCELLED:
                    evidence.matched_patterns.append("CANCELLED_PARENT_DEPENDENCY")
                    return (
                        "CANCELLED_DEPENDENCY",
                        RootCauseCategory.WORKFLOW,
                        0.90,
                        (
                            f"Parent dependency task '{dep_task.task_name}' "
                            f"({dep_id}) was cancelled."
                        ),
                    )
            else:
                evidence.dependency_status[str(dep_id)] = {"status": "NOT_FOUND"}
                evidence.matched_patterns.append("MISSING_DEPENDENCY_TASK")
                return (
                    "MISSING_DEPENDENCY",
                    RootCauseCategory.WORKFLOW,
                    0.85,
                    f"Dependency '{dep_id}' was not found in workflow state.",
                )

        return None

    def _inspect_filesystem_and_paths(
        self,
        message: str,
        task: Optional[Task],
        result: Optional[ExecutionResult],
        evidence: DiagnosticEvidence,
    ) -> Optional[Tuple[str, RootCauseCategory, float, str]]:
        """Inspects file/directory paths involved in task input/output."""
        # Check artifact validity first
        if result and result.artifacts:
            for artifact in result.artifacts:
                if artifact.filepath:
                    if not os.path.exists(artifact.filepath):
                        evidence.missing_paths.append(artifact.filepath)
                        evidence.matched_patterns.append("MISSING_ARTIFACT_FILE")
                        return (
                            "INVALID_ARTIFACT",
                            RootCauseCategory.INFRASTRUCTURE,
                            0.95,
                            f"Artifact file '{artifact.filepath}' missing on disk.",
                        )
                    try:
                        if os.path.getsize(artifact.filepath) == 0:
                            evidence.matched_patterns.append("EMPTY_ARTIFACT_FILE")
                            return (
                                "INVALID_ARTIFACT",
                                RootCauseCategory.INFRASTRUCTURE,
                                0.90,
                                f"Artifact '{artifact.filepath}' is empty (0 bytes).",
                            )
                    except OSError:
                        pass

        # Extract file paths from task parameters or error message
        extracted_paths: List[str] = []

        # Extract paths from message (e.g. quotes or standard path strings)
        path_regex = (
            r"(?:[a-zA-Z]:[\\/][^\s\"'<>]|/[^\s\"'<>]+|\b[\w\.-]+[\\/][\w\.-]+)"
        )
        path_matches = re.findall(path_regex, message)
        extracted_paths.extend(path_matches)

        # Extract from task input dict
        task_input = getattr(task, "task_input", {}) if task else {}
        if isinstance(task_input, dict):
            for v in task_input.values():
                if isinstance(v, str) and ("\\" in v or "/" in v or "." in v):
                    extracted_paths.append(v)

        # Extract from task expected_output
        has_path = (
            task
            and task.expected_output
            and ("\\" in task.expected_output or "/" in task.expected_output)
        )
        if has_path:
            extracted_paths.append(task.expected_output)

        is_path_error = any(p.search(message) for p in self.PATH_ERROR_PATTERNS)

        for raw_path in extracted_paths:
            path_obj = Path(raw_path)
            # Try inspecting parent directory for file targets
            parent_dir = path_obj.parent if path_obj.suffix else path_obj
            if parent_dir and str(parent_dir) not in (".", ""):
                if not parent_dir.exists():
                    missing_str = str(parent_dir)
                    if missing_str not in evidence.missing_paths:
                        evidence.missing_paths.append(missing_str)
                    evidence.matched_patterns.append("OUTPUT_DIRECTORY_MISSING")
                    return (
                        "OUTPUT_DIRECTORY_MISSING",
                        RootCauseCategory.INFRASTRUCTURE,
                        0.95,
                        f"Target output directory '{missing_str}' missing on disk.",
                    )

        if is_path_error:
            evidence.matched_patterns.append("PATH_NOT_FOUND")
            return (
                "FILE_OR_DIRECTORY_NOT_FOUND",
                RootCauseCategory.INFRASTRUCTURE,
                0.85,
                "Referenced file or directory was not found on the local filesystem.",
            )

        return None

    def _inspect_tool_information(
        self,
        task: Optional[Task],
        result: Optional[ExecutionResult],
        tool_info: Optional[Dict[str, Any]],
        message: str,
        f_type: FailureType,
        evidence: DiagnosticEvidence,
    ) -> Optional[Tuple[str, RootCauseCategory, float, str]]:
        """Inspects required tool configuration, health, and availability."""
        req_tool = task.required_tool if task else None

        if tool_info:
            evidence.tool_status = tool_info
            tool_state = str(tool_info.get("state", "")).upper()
            tool_health = str(tool_info.get("health", "")).upper()

            if tool_state in ("DISABLED", "UNAVAILABLE", "NOT_FOUND"):
                evidence.matched_patterns.append("TOOL_DISABLED_OR_UNAVAILABLE")
                return (
                    "TOOL_UNAVAILABLE",
                    RootCauseCategory.TOOL,
                    0.95,
                    f"Required tool '{req_tool}' is in state '{tool_state}'.",
                )
            if tool_health in ("UNHEALTHY", "DEGRADED"):
                evidence.matched_patterns.append("TOOL_UNHEALTHY")
                return (
                    "TOOL_UNHEALTHY",
                    RootCauseCategory.TOOL,
                    0.90,
                    f"Required tool '{req_tool}' health status is '{tool_health}'.",
                )

        if f_type == FailureType.TOOL_UNAVAILABLE or any(
            p.search(message) for p in self.TOOL_PATTERNS
        ):
            evidence.matched_patterns.append("TOOL_UNAVAILABLE")
            tool_name = req_tool or "specified tool"
            return (
                "TOOL_UNAVAILABLE",
                RootCauseCategory.TOOL,
                0.90,
                f"Required tool '{tool_name}' is unavailable or not registered.",
            )

        return None

    def _inspect_patterns_and_logs(
        self,
        message: str,
        f_type: FailureType,
        logs: List[str],
        evidence: DiagnosticEvidence,
    ) -> Optional[Tuple[str, RootCauseCategory, float, str]]:
        """Scans combined message and execution logs for error signatures."""
        log_block = message + "\n" + "\n".join(logs)

        # Check Permission
        if f_type == FailureType.PERMISSION_DENIED or any(
            p.search(log_block) for p in self.PERMISSION_PATTERNS
        ):
            evidence.matched_patterns.append("PERMISSION_DENIED")
            return (
                "PERMISSION_DENIED",
                RootCauseCategory.PERMISSION,
                0.90,
                "Missing authorization or user permission denial.",
            )

        # Check Timeout
        if f_type == FailureType.TIMEOUT or any(
            p.search(log_block) for p in self.TIMEOUT_PATTERNS
        ):
            evidence.matched_patterns.append("EXECUTION_TIMEOUT")
            return (
                "EXECUTION_TIMEOUT",
                RootCauseCategory.RUNTIME,
                0.85,
                "Task execution duration exceeded configured timeout limit.",
            )

        # Check Network
        if any(p.search(log_block) for p in self.NETWORK_ERROR_PATTERNS):
            evidence.matched_patterns.append("NETWORK_UNAVAILABLE")
            return (
                "NETWORK_UNAVAILABLE",
                RootCauseCategory.NETWORK,
                0.85,
                "Network connection failed or remote host was unreachable.",
            )

        return None

    def _synthesize_diagnosis(
        self,
        dep_cause: Optional[Tuple[str, RootCauseCategory, float, str]],
        fs_cause: Optional[Tuple[str, RootCauseCategory, float, str]],
        tool_cause: Optional[Tuple[str, RootCauseCategory, float, str]],
        pattern_cause: Optional[Tuple[str, RootCauseCategory, float, str]],
        f_type: FailureType,
        combined_message: str,
        evidence: DiagnosticEvidence,
    ) -> Tuple[str, RootCauseCategory, float, str, List[AlternativeCause]]:
        """
        Ranks candidate root causes and computes final confidence score.
        """
        candidates: List[Tuple[str, RootCauseCategory, float, str]] = []

        if dep_cause:
            candidates.append(dep_cause)
        if fs_cause:
            candidates.append(fs_cause)
        if tool_cause:
            candidates.append(tool_cause)
        if pattern_cause:
            candidates.append(pattern_cause)

        # Sort candidates by confidence descending
        candidates.sort(key=lambda x: x[2], reverse=True)

        if candidates:
            primary = candidates[0]
            alternatives = [
                AlternativeCause(
                    cause_code=alt[0],
                    category=alt[1],
                    confidence_score=round(alt[2] * 0.8, 2),
                    explanation=alt[3],
                )
                for alt in candidates[1:]
            ]
            return primary[0], primary[1], primary[2], primary[3], alternatives

        # If no specific candidate matched, handle low-confidence / unknown case safely
        alternatives = [
            AlternativeCause(
                cause_code="NETWORK_FAILURE",
                category=RootCauseCategory.NETWORK,
                confidence_score=0.30,
                explanation="Network or remote service connectivity failure.",
            ),
            AlternativeCause(
                cause_code="TOOL_ERROR",
                category=RootCauseCategory.TOOL,
                confidence_score=0.25,
                explanation="Internal tool execution error or unexpected exception.",
            ),
            AlternativeCause(
                cause_code="PERMISSION_RESTRICTION",
                category=RootCauseCategory.PERMISSION,
                confidence_score=0.20,
                explanation="System or resource permission restriction.",
            ),
        ]

        evidence.context_signals["insufficient_evidence"] = True

        err_detail = combined_message or f_type.value
        return (
            "UNKNOWN_ROOT_CAUSE",
            RootCauseCategory.UNKNOWN,
            0.30,
            (
                "Insufficient empirical evidence to determine root cause. "
                f"Observed error: '{err_detail}'."
            ),
            alternatives,
        )
