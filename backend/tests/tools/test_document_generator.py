import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from shared.contracts.document import (
    DocumentElement,
    DocumentElementType,
    DocumentFormat,
    StructuredDocumentInput,
)
from shared.contracts.tool import ToolHealth, ToolState

from app.core.exceptions import InputValidationException, PermissionDeniedException
from app.core.permissions import PermissionManager, PermissionType
from app.tools.document.generator import DocumentGenerator
from app.tools.document.tool import DocumentToolAdapter, register_document_tool
from app.tools.registry import ToolRegistry


class TestDocumentGenerator:
    """Test suite for DocumentGenerator core module."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_basic_markdown_document_generation(self, temp_dir):
        generator = DocumentGenerator()
        output_file = temp_dir / "basic_report.md"

        input_data = StructuredDocumentInput(
            title="Quarterly Operations Report",
            subtitle="Q3 Performance Metrics",
            author="AetherPhoenix Assistant",
            format=DocumentFormat.MARKDOWN,
            elements=[
                DocumentElement(
                    element_type=DocumentElementType.HEADING,
                    text="Executive Summary",
                    level=1,
                ),
                DocumentElement(
                    element_type=DocumentElementType.PARAGRAPH,
                    text="All systems performed within optimal parameters.",
                    bold=True,
                ),
            ],
            output_path=str(output_file),
        )

        result = generator.generate(input_data)

        assert result.status == "SUCCESS"
        assert result.filepath == str(output_file.resolve())
        assert result.file_name == "basic_report.md"
        assert result.file_size_bytes > 0
        assert result.word_count > 0
        assert result.line_count > 0
        assert len(result.checksum_sha256) == 64
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert "# Quarterly Operations Report" in content
        assert "*Q3 Performance Metrics*" in content
        assert "**Author:** AetherPhoenix Assistant" in content
        assert "# Executive Summary" in content

    def test_all_supported_formats(self, temp_dir):
        generator = DocumentGenerator()

        # Text (.txt)
        txt_file = temp_dir / "report.txt"
        txt_input = StructuredDocumentInput(
            title="System Audit Report",
            content="Summary of server logs.",
            format=DocumentFormat.TEXT,
            elements=[
                DocumentElement(
                    element_type=DocumentElementType.LIST,
                    items=["Server A: OK", "Server B: OK"],
                )
            ],
            output_path=str(txt_file),
        )
        txt_res = generator.generate(txt_input)
        assert txt_res.status == "SUCCESS"
        assert txt_file.exists()
        assert "SYSTEM AUDIT REPORT" in txt_file.read_text(encoding="utf-8")

        # HTML (.html)
        html_file = temp_dir / "report.html"
        html_input = StructuredDocumentInput(
            title="Web Summary",
            content="HTML output preview.",
            format=DocumentFormat.HTML,
            elements=[
                DocumentElement(
                    element_type=DocumentElementType.PARAGRAPH, text="Paragraph item."
                )
            ],
            output_path=str(html_file),
        )
        html_res = generator.generate(html_input)
        assert html_res.status == "SUCCESS"
        assert html_file.exists()
        assert "<!DOCTYPE html>" in html_file.read_text(encoding="utf-8")

        # JSON (.json)
        json_file = temp_dir / "report.json"
        json_input = StructuredDocumentInput(
            title="Data Export",
            content="JSON document body",
            format=DocumentFormat.JSON,
            output_path=str(json_file),
        )
        json_res = generator.generate(json_input)
        assert json_res.status == "SUCCESS"
        assert json_file.exists()
        assert '"title": "Data Export"' in json_file.read_text(encoding="utf-8")

        # CSV (.csv)
        csv_file = temp_dir / "report.csv"
        csv_input = StructuredDocumentInput(
            title="Metrics Table",
            format=DocumentFormat.CSV,
            elements=[
                DocumentElement(
                    element_type=DocumentElementType.TABLE,
                    headers=["Service", "Latency", "Status"],
                    rows=[
                        ["API Gateway", "12ms", "Healthy"],
                        ["Database", "4ms", "Healthy"],
                    ],
                )
            ],
            output_path=str(csv_file),
        )
        csv_res = generator.generate(csv_input)
        assert csv_res.status == "SUCCESS"
        assert csv_file.exists()
        assert "Service,Latency,Status" in csv_file.read_text(encoding="utf-8")

    def test_empty_content_validation(self, temp_dir):
        generator = DocumentGenerator()
        output_file = temp_dir / "empty.md"

        input_data = StructuredDocumentInput(
            title="",
            content="",
            elements=[],
            sections=[],
            output_path=str(output_file),
        )

        with pytest.raises(InputValidationException) as exc_info:
            generator.generate(input_data)

        assert "at least a title or non-empty content" in exc_info.value.message

    def test_invalid_output_path(self, temp_dir):
        generator = DocumentGenerator()

        # Empty path
        with pytest.raises(InputValidationException) as exc1:
            generator.validate_output_path("", DocumentFormat.MARKDOWN)
        assert "cannot be empty" in exc1.value.message

        # Null byte in path
        with pytest.raises(InputValidationException) as exc_null:
            generator.validate_output_path("file\0path.md", DocumentFormat.MARKDOWN)
        assert "null byte" in exc_null.value.message

        # Invalid file extension
        with pytest.raises(InputValidationException) as exc2:
            generator.validate_output_path(
                str(temp_dir / "invalid.pdf"), DocumentFormat.MARKDOWN
            )
        assert "does not match expected format" in exc2.value.message

        # Directory traversal / outside allowed directories
        allowed_dir = temp_dir / "allowed"
        allowed_dir.mkdir()
        restricted_generator = DocumentGenerator(allowed_base_dirs=[allowed_dir])

        with pytest.raises(InputValidationException) as exc3:
            restricted_generator.validate_output_path(
                str(temp_dir / "outside.md"), DocumentFormat.MARKDOWN
            )
        assert "outside approved directories" in exc3.value.message

    def test_existing_file_handling(self, temp_dir):
        generator = DocumentGenerator()
        existing_file = temp_dir / "existing.md"
        existing_file.write_text("Previous Content", encoding="utf-8")

        input_data = StructuredDocumentInput(
            title="New Title",
            content="Updated Content",
            output_path=str(existing_file),
            overwrite=False,
        )

        # Overwrite = False should raise exception
        with pytest.raises(InputValidationException) as exc_info:
            generator.generate(input_data)
        assert "already exists" in exc_info.value.message

        # Overwrite = True should overwrite successfully
        input_data.overwrite = True
        result = generator.generate(input_data)
        assert result.status == "SUCCESS"
        assert "Updated Content" in existing_file.read_text(encoding="utf-8")

    def test_permission_denial(self, temp_dir):
        permission_manager = PermissionManager()
        generator = DocumentGenerator(permission_manager=permission_manager)
        workflow_id = uuid4()
        output_file = temp_dir / "permission_test.md"

        # Request permission but keep it PENDING
        permission_manager.request_permission(
            workflow_id=str(workflow_id),
            task_id="task_1",
            permission_type=PermissionType.FILE_WRITE,
            reason="Generate Document",
        )

        input_data = StructuredDocumentInput(
            title="Permission Test Doc",
            content="Testing permission denial flow.",
            output_path=str(output_file),
            workflow_id=workflow_id,
        )

        with pytest.raises(PermissionDeniedException):
            generator.generate(input_data)

        assert not output_file.exists()

    def test_permission_granted_flow(self, temp_dir):
        permission_manager = PermissionManager()
        generator = DocumentGenerator(permission_manager=permission_manager)
        workflow_id = uuid4()
        output_file = temp_dir / "permission_granted.md"

        req = permission_manager.request_permission(
            workflow_id=str(workflow_id),
            task_id="task_1",
            permission_type=PermissionType.FILE_WRITE,
            reason="Generate Document",
        )
        permission_manager.approve_permission(req.request_id)

        input_data = StructuredDocumentInput(
            title="Permission Granted Doc",
            content="Permission was granted.",
            output_path=str(output_file),
            workflow_id=workflow_id,
        )

        result = generator.generate(input_data)
        assert result.status == "SUCCESS"
        assert output_file.exists()

    def test_tool_registry_integration(self):
        registry = ToolRegistry()
        doc_tool = register_document_tool(registry)

        assert doc_tool.name == "document_generator"
        assert doc_tool.status == ToolState.READY
        assert doc_tool.health == ToolHealth.HEALTHY
        assert "FILE_SYSTEM" in doc_tool.required_permissions

        fetched_tool = registry.get("document_generator")
        assert fetched_tool is not None
        assert fetched_tool.name == "document_generator"

    def test_document_tool_adapter_execution(self, temp_dir):
        output_file = temp_dir / "adapter_doc.md"
        adapter = DocumentToolAdapter()

        payload = {
            "title": "Adapter Execution Test",
            "content": "Testing adapter payload dictionary.",
            "format": "markdown",
            "elements": [
                {
                    "element_type": "heading",
                    "text": "Adapter Section",
                    "level": 2,
                }
            ],
            "output_path": str(output_file),
        }

        result = adapter.execute(payload)
        assert result.status == "SUCCESS"
        assert output_file.exists()
        assert "# Adapter Execution Test" in output_file.read_text(encoding="utf-8")
