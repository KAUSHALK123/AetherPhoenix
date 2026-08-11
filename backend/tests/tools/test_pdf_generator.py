import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from shared.contracts.pdf import (
    CodeBlockElement,
    HeadingElement,
    ListElement,
    ParagraphElement,
    PDFDocumentInput,
    TableElement,
)
from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.tool import ToolHealth, ToolState

from app.core.exceptions import InputValidationException, PermissionDeniedException
from app.core.permissions import PermissionManager
from app.tools.pdf.generator import PDFGenerator
from app.tools.pdf.tool import PDFToolAdapter, register_pdf_tool
from app.tools.registry import ToolRegistry


class TestPDFGenerator:
    """Test suite for PDFGenerator core module."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_basic_pdf_generation(self, temp_dir):
        generator = PDFGenerator()
        output_file = temp_dir / "basic_report.pdf"

        input_data = PDFDocumentInput(
            title="Quarterly Research Report",
            subtitle="Q3 Market Analysis",
            author="AetherPhoenix Assistant",
            elements=[
                HeadingElement(text="Executive Summary", level=1),
                ParagraphElement(
                    text="This report outlines performance metrics and trends for Q3."
                ),
            ],
            output_path=str(output_file),
        )

        result = generator.generate(input_data)

        assert result.status == "SUCCESS"
        assert result.filepath == str(output_file.resolve())
        assert result.file_name == "basic_report.pdf"
        assert result.size_bytes > 0
        assert result.page_count >= 1
        assert len(result.checksum) == 64
        assert output_file.exists()

        # Validate %PDF- header magic bytes
        with open(output_file, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"

    def test_multiple_elements_and_structured_content(self, temp_dir):
        generator = PDFGenerator()
        output_file = temp_dir / "structured_document.pdf"

        input_data = PDFDocumentInput(
            title="Complete Systems Architecture Guide",
            subtitle="Detailed technical specs and components",
            author="Dev Team",
            elements=[
                HeadingElement(text="Overview", level=1),
                ParagraphElement(
                    text="Architecture highlights for multi-agent framework.", bold=True
                ),
                HeadingElement(text="Core Components", level=2),
                ListElement(
                    items=[
                        "Planner Agent",
                        "Workflow Compiler",
                        "Worker Agent",
                        "Supervisor Agent",
                    ],
                    is_numbered=False,
                ),
                HeadingElement(text="Execution Pipeline Steps", level=2),
                ListElement(
                    items=[
                        "Task Reception",
                        "Permission Validation",
                        "Tool Resolution",
                        "Execution Result",
                    ],
                    is_numbered=True,
                ),
                HeadingElement(text="System Performance Metrics", level=2),
                TableElement(
                    headers=["Component", "Latency", "Status"],
                    rows=[
                        ["Task Validator", "<20 ms", "Active"],
                        ["Tool Loader", "<50 ms", "Active"],
                        ["PDF Generator", "<200 ms", "Active"],
                    ],
                ),
                HeadingElement(text="Sample Code Spec", level=2),
                CodeBlockElement(
                    code="def build(d):\n    return PDFGenerator().generate(d)",
                    language="python",
                ),
            ],
            output_path=str(output_file),
        )

        result = generator.generate(input_data)

        assert result.status == "SUCCESS"
        assert result.size_bytes > 1000
        assert result.metadata["element_count"] == 10
        assert output_file.exists()

    def test_empty_content_validation(self, temp_dir):
        generator = PDFGenerator()
        output_file = temp_dir / "empty.pdf"

        input_data = PDFDocumentInput(
            title="",
            elements=[],
            output_path=str(output_file),
        )

        with pytest.raises(InputValidationException) as exc_info:
            generator.generate(input_data)

        assert "at least a title or content elements" in exc_info.value.message

    def test_invalid_output_path(self, temp_dir):
        generator = PDFGenerator()

        # Empty path
        with pytest.raises(InputValidationException) as exc1:
            generator.validate_output_path("")
        assert "cannot be empty" in exc1.value.message

        # Invalid file extension
        with pytest.raises(InputValidationException) as exc2:
            generator.validate_output_path(str(temp_dir / "invalid.txt"))
        assert "'.pdf' extension" in exc2.value.message

        # Path traversal / outside allowed directories
        allowed_dir = temp_dir / "allowed"
        allowed_dir.mkdir()
        restricted_generator = PDFGenerator(allowed_base_dirs=[allowed_dir])

        with pytest.raises(InputValidationException) as exc3:
            restricted_generator.validate_output_path(str(temp_dir / "outside.pdf"))
        assert "outside approved directories" in exc3.value.message

    @pytest.mark.asyncio
    async def test_permission_denial(self, temp_dir):
        permission_manager = PermissionManager(auto_approve_low_risk=False)
        generator = PDFGenerator(permission_manager=permission_manager)
        workflow_id = uuid4()
        output_file = temp_dir / "permission_test.pdf"

        # Request permission but keep it PENDING (not granted)
        await permission_manager.request_permission(
            workflow_id=workflow_id,
            permission_type=PermissionType.FILE_SYSTEM,
            reason="Generate PDF report",
            risk_level=RiskLevel.HIGH,
        )

        input_data = PDFDocumentInput(
            title="Permission Test Doc",
            elements=[ParagraphElement(text="Testing permission denial.")],
            output_path=str(output_file),
            workflow_id=workflow_id,
        )

        with pytest.raises(PermissionDeniedException):
            generator.generate(input_data)

        assert not output_file.exists()

    @pytest.mark.asyncio
    async def test_permission_granted_flow(self, temp_dir):
        permission_manager = PermissionManager(auto_approve_low_risk=False)
        generator = PDFGenerator(permission_manager=permission_manager)
        workflow_id = uuid4()
        output_file = temp_dir / "permission_granted.pdf"

        req = await permission_manager.request_permission(
            workflow_id=workflow_id,
            permission_type=PermissionType.FILE_SYSTEM,
            reason="Generate PDF report",
            risk_level=RiskLevel.MEDIUM,
        )
        await permission_manager.grant_permission(req.permission_id)

        input_data = PDFDocumentInput(
            title="Permission Granted Doc",
            elements=[ParagraphElement(text="Permission granted successfully.")],
            output_path=str(output_file),
            workflow_id=workflow_id,
        )

        result = generator.generate(input_data)
        assert result.status == "SUCCESS"
        assert output_file.exists()

    def test_tool_registry_integration(self):
        registry = ToolRegistry()
        pdf_tool = register_pdf_tool(registry)

        assert pdf_tool.name == "pdf_generator"
        assert pdf_tool.status == ToolState.READY
        assert pdf_tool.health == ToolHealth.HEALTHY
        assert PermissionType.FILE_SYSTEM.value in pdf_tool.required_permissions

        fetched_tool = registry.get("pdf_generator")
        assert fetched_tool is not None
        assert fetched_tool.name == "pdf_generator"

    def test_pdf_tool_adapter_execution(self, temp_dir):
        output_file = temp_dir / "adapter_test.pdf"
        adapter = PDFToolAdapter()

        payload = {
            "title": "Adapter Execution Test",
            "subtitle": "Testing dict payload",
            "elements": [
                {"element_type": "paragraph", "text": "Testing via adapter execution."}
            ],
            "output_path": str(output_file),
        }

        result = adapter.execute(payload)
        assert result.status == "SUCCESS"
        assert output_file.exists()
