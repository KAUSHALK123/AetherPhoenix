import zipfile
from uuid import uuid4

import pytest
from shared.contracts.execution import ExecutionResult
from shared.contracts.task import Task, TaskCategory, TaskType

from app.engine.validator import OutputValidationService


@pytest.fixture
def validator():
    return OutputValidationService()


def test_validate_pptx_valid(tmp_path, validator):
    import pptx

    pptx_path = tmp_path / "valid.pptx"
    prs = pptx.Presentation()
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    title.text = "Hello Research Evaluation"
    prs.save(str(pptx_path))

    is_valid, issues = validator.validate_pptx_structure(pptx_path)
    assert is_valid is True
    assert len(issues) == 0


def test_validate_pptx_empty_file(tmp_path, validator):
    empty_pptx = tmp_path / "empty.pptx"
    empty_pptx.write_bytes(b"")

    is_valid, issues = validator.validate_pptx_structure(empty_pptx)
    assert is_valid is False
    assert any("empty" in i.lower() for i in issues)


def test_validate_pptx_corrupted_zip(tmp_path, validator):
    corrupt_pptx = tmp_path / "corrupt.pptx"
    corrupt_pptx.write_bytes(b"PK\x03\x04corrupted_header_data_not_a_real_zip")

    is_valid, issues = validator.validate_pptx_structure(corrupt_pptx)
    assert is_valid is False
    assert any(
        "not a valid zip container" in i.lower() or "failed to inspect zip" in i.lower()
        for i in issues
    )


def test_validate_pptx_missing_openxml_parts(tmp_path, validator):
    partial_pptx = tmp_path / "partial.pptx"
    with zipfile.ZipFile(partial_pptx, "w") as zf:
        zf.writestr("some_file.txt", "not a presentation")

    is_valid, issues = validator.validate_pptx_structure(partial_pptx)
    assert is_valid is False
    assert any("[content_types].xml" in i.lower() for i in issues)


def test_validate_pdf_valid(tmp_path, validator):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "valid.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Sample valid PDF text content for testing.")
    c.save()

    is_valid, issues = validator.validate_pdf_structure(pdf_path)
    assert is_valid is True
    assert len(issues) == 0


def test_validate_pdf_empty(tmp_path, validator):
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")

    is_valid, issues = validator.validate_pdf_structure(empty_pdf)
    assert is_valid is False
    assert any("empty" in i.lower() for i in issues)


def test_validate_pdf_invalid_header(tmp_path, validator):
    bad_pdf = tmp_path / "bad_header.pdf"
    bad_pdf.write_bytes(b"NOT_A_PDF_STREAM_HEADER")

    is_valid, issues = validator.validate_pdf_structure(bad_pdf)
    assert is_valid is False
    assert any("header" in i.lower() for i in issues)


def test_output_validation_service_catches_corrupted_deliverable(tmp_path, validator):
    bad_pptx = tmp_path / "deck.pptx"
    bad_pptx.write_bytes(b"bad zip content")

    task_id = uuid4()
    workflow_id = uuid4()
    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="Generate Deck",
        description="Generate PPTX deck",
        required_tool="presentation_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="deck.pptx",
        task_type=TaskType.LEAF,
        artifact_location=str(bad_pptx),
    )
    result = ExecutionResult(
        task_id=task_id,
        workflow_id=workflow_id,
        success=True,
        output={"presentation_path": str(bad_pptx)},
    )

    is_valid, checks, issues = validator.validate(task, result)
    assert is_valid is False
    assert any("corrupted deliverable" in i.lower() for i in issues)
