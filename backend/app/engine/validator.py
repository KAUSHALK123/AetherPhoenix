import os
from typing import Dict, List, Tuple

from shared.contracts.execution import ExecutionResult
from shared.contracts.task import Task


class OutputValidationService:
    """
    Service responsible for validating Worker task execution results
    against success criteria, failure criteria, and artifact expectations.
    """

    def validate(
        self, task: Task, result: ExecutionResult
    ) -> Tuple[bool, Dict[str, bool], List[str]]:
        """
        Validates task execution results and returns:
        - is_valid: bool indicating overall validity
        - checks: dict mapping check names to boolean results
        - issues: list of error/warning strings describing failures
        """
        checks: Dict[str, bool] = {}
        issues: List[str] = []

        # 1. Execution Success Check
        checks["execution_success"] = result.success
        if not result.success:
            is_valid = False
            err_msg = result.error.error_message if result.error else "Unknown"
            issues.append(f"Execution marked unsuccessful. Error: {err_msg}")
            return False, checks, issues

        # 2. Artifact Declarations Verification
        artifact_ok, artifact_issues = self._verify_artifacts(task, result)
        checks["artifacts_valid"] = artifact_ok
        issues.extend(artifact_issues)

        # 3. Output Schema & Data Verification
        output_ok, output_issues = self._verify_output_data(task, result)
        checks["output_valid"] = output_ok
        issues.extend(output_issues)

        # 4. Failure Criteria Verification
        failure_detected, failure_issues = self._check_failure_criteria(task, result)
        checks["no_failure_criteria_triggered"] = not failure_detected
        issues.extend(failure_issues)

        is_valid = (
            checks["execution_success"]
            and checks["artifacts_valid"]
            and checks["output_valid"]
            and checks["no_failure_criteria_triggered"]
        )

        return is_valid, checks, issues

    def _verify_artifacts(
        self, task: Task, result: ExecutionResult
    ) -> Tuple[bool, List[str]]:
        """
        Checks that required files/artifacts exist, are accessible, and are non-empty.
        """
        issues = []
        is_valid = True

        # Check task's designated artifact location
        if task.artifact_location:
            filepath = task.artifact_location
            if not os.path.exists(filepath):
                is_valid = False
                issues.append(
                    f"Declared task artifact not found on filesystem: {filepath}"
                )
            elif os.path.getsize(filepath) == 0:
                is_valid = False
                issues.append(f"Declared task artifact is empty (0 bytes): {filepath}")

        # Check result artifacts
        if result.artifacts:
            for artifact in result.artifacts:
                if not os.path.exists(artifact.filepath):
                    is_valid = False
                    issues.append(
                        f"Result artifact file not found: {artifact.filepath}"
                    )
                elif os.path.getsize(artifact.filepath) == 0:
                    is_valid = False
                    issues.append(
                        f"Result artifact file is empty (0 bytes): {artifact.filepath}"
                    )

        return is_valid, issues

    def _verify_output_data(
        self, task: Task, result: ExecutionResult
    ) -> Tuple[bool, List[str]]:
        """
        Validates the execution output against expected outputs and success criteria.
        """
        issues = []
        is_valid = True

        # Check expected output heuristic
        if task.expected_output:
            if not result.output and not result.artifacts:
                is_valid = False
                issues.append(
                    "Expected output was defined, but no output data "
                    "or artifacts were returned."
                )

        # Check success criteria
        if task.success_criteria:
            for criterion in task.success_criteria:
                criterion_lower = criterion.lower()

                # Check "file: <path>" criterion
                if criterion_lower.startswith("file:"):
                    filepath = criterion[5:].strip()
                    if not os.path.exists(filepath):
                        is_valid = False
                        issues.append(
                            f"Success criteria failed: File does not exist ({filepath})"
                        )

                # Check "contains: <key>" criterion
                elif criterion_lower.startswith("contains:"):
                    expected_key = criterion[9:].strip()
                    if not result.output or expected_key not in result.output:
                        is_valid = False
                        issues.append(
                            f"Success criteria failed: Output missing "
                            f"required key '{expected_key}'"
                        )

                # Default validation: check if result output is populated
                else:
                    if not result.output and not result.artifacts:
                        is_valid = False
                        issues.append(
                            f"Success criteria failed: '{criterion}' "
                            "could not be verified (empty output)"
                        )

        return is_valid, issues

    def _check_failure_criteria(
        self, task: Task, result: ExecutionResult
    ) -> Tuple[bool, List[str]]:
        """
        Checks if any failure criteria have been triggered in output or logs.
        """
        issues = []
        failure_detected = False

        if task.failure_criteria:
            for criterion in task.failure_criteria:
                # Check if criterion exists in output
                if result.output:
                    for key, val in result.output.items():
                        if (
                            criterion.lower() in str(key).lower()
                            or criterion.lower() in str(val).lower()
                        ):
                            failure_detected = True
                            issues.append(
                                f"Failure criteria triggered: "
                                f"'{criterion}' found in output"
                            )
                            break

                # Check if criterion exists in execution logs
                if result.logs:
                    for log in result.logs:
                        if criterion.lower() in log.lower():
                            failure_detected = True
                            issues.append(
                                f"Failure criteria triggered: "
                                f"'{criterion}' found in logs"
                            )
                            break

        return failure_detected, issues
