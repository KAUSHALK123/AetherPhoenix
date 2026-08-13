import os
import tempfile
from uuid import uuid4

import pytest
from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import ExecutionResult, TaskError
from shared.contracts.task import Task, TaskCategory

from app.engine.validator import OutputValidationService


@pytest.fixture
def validator():
    return OutputValidationService()


@pytest.fixture
def base_task():
    return Task(
        workflow_id=uuid4(),
        task_name="Verify PPT Output",
        description="Verify PPT output task",
        required_tool="dummy",
        category=TaskCategory.OTHER,
        expected_output="dummy.pptx",
    )


@pytest.fixture
def base_result(base_task):
    return ExecutionResult(
        task_id=base_task.task_id,
        workflow_id=base_task.workflow_id,
        success=True,
        output={"status": "completed"},
    )


def test_validation_success(validator, base_task, base_result):
    is_valid, checks, issues = validator.validate(base_task, base_result)
    assert is_valid is True
    assert checks["execution_success"] is True
    assert checks["artifacts_valid"] is True
    assert checks["output_valid"] is True
    assert checks["no_failure_criteria_triggered"] is True
    assert len(issues) == 0


def test_validation_execution_failure(validator, base_task, base_result):
    base_result.success = False
    base_result.error = TaskError(error_code="ERR", error_message="Task crashed")

    is_valid, checks, issues = validator.validate(base_task, base_result)
    assert is_valid is False
    assert checks["execution_success"] is False
    assert len(issues) == 1
    assert "Task crashed" in issues[0]


def test_validation_missing_declared_artifact(validator, base_task, base_result):
    base_task.artifact_location = "nonexistent_file.pptx"

    is_valid, checks, issues = validator.validate(base_task, base_result)
    assert is_valid is False
    assert checks["artifacts_valid"] is False
    assert any("Declared task artifact not found" in issue for issue in issues)


def test_validation_present_declared_artifact(validator, base_task, base_result):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"PowerPoint content")
        temp_file_path = temp_file.name

    try:
        base_task.artifact_location = temp_file_path
        is_valid, checks, issues = validator.validate(base_task, base_result)
        assert is_valid is True
        assert checks["artifacts_valid"] is True
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def test_validation_missing_result_artifact(validator, base_task, base_result):
    base_result.artifacts = [
        Artifact(
            workflow_id=base_task.workflow_id,
            name="presentation.pptx",
            filepath="nonexistent_result.pptx",
            artifact_type=ArtifactType.PPT,
        )
    ]

    is_valid, checks, issues = validator.validate(base_task, base_result)
    assert is_valid is False
    assert checks["artifacts_valid"] is False
    assert any("Result artifact file not found" in issue for issue in issues)


def test_validation_success_criteria_missing_key(validator, base_task, base_result):
    base_task.success_criteria = ["contains: report_url"]

    is_valid, checks, issues = validator.validate(base_task, base_result)
    assert is_valid is False
    assert checks["output_valid"] is False
    assert any("missing required key 'report_url'" in issue for issue in issues)


def test_validation_success_criteria_key_present(validator, base_task, base_result):
    base_task.success_criteria = ["contains: report_url"]
    base_result.output = {"report_url": "http://example.com/report"}

    is_valid, checks, issues = validator.validate(base_task, base_result)
    assert is_valid is True
    assert checks["output_valid"] is True


def test_validation_failure_criteria_triggered(validator, base_task, base_result):
    base_task.failure_criteria = ["access denied"]
    base_result.output = {"error": "Authentication failed, access denied."}

    is_valid, checks, issues = validator.validate(base_task, base_result)
    assert is_valid is False
    assert checks["no_failure_criteria_triggered"] is False
    assert any(
        "Failure criteria triggered: 'access denied'" in issue for issue in issues
    )
