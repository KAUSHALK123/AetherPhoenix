from uuid import uuid4

import pytest
from PIL import Image
from shared.contracts.artifact import ArtifactType
from shared.contracts.export import ExportFormat, ExportRequest, ExportResult
from shared.contracts.task import Task, TaskCategory

from app.services.artifact_storage import (
    ArtifactStorageService,
    LocalFileSystemArtifactStorageProvider,
)
from app.tools.export.adapter import ExportToolAdapter
from app.tools.export.engine import ExportEngine, ExportError
from app.tools.export.tool import register_export_tool
from app.tools.registry import ToolRegistry


@pytest.fixture
def tmp_workspace(tmp_path):
    storage_dir = tmp_path / "artifacts"
    storage_dir.mkdir(parents=True, exist_ok=True)
    provider = LocalFileSystemArtifactStorageProvider(base_dir=storage_dir)
    service = ArtifactStorageService(provider=provider)
    return storage_dir, service


@pytest.fixture
def export_engine(tmp_workspace):
    _, provider = tmp_workspace
    return ExportEngine(artifact_storage_service=provider)


@pytest.fixture
def export_adapter(export_engine, tmp_workspace):
    _, provider = tmp_workspace
    return ExportToolAdapter(engine=export_engine, artifact_storage_service=provider)


def test_export_contracts():
    wf_id = uuid4()
    req = ExportRequest(
        workflow_id=wf_id,
        target_format=ExportFormat.PDF,
        source_filepath="test.txt",
        title="Test Export",
    )
    assert req.workflow_id == wf_id
    assert req.target_format == ExportFormat.PDF

    res = ExportResult(
        workflow_id=wf_id,
        name="test.pdf",
        filepath="/tmp/test.pdf",
        download_url="/api/v1/artifacts/123/download",
        format=ExportFormat.PDF,
        size_bytes=100,
        checksum="abcd1234",
    )
    assert res.status == "SUCCESS"
    assert res.format == ExportFormat.PDF


@pytest.mark.asyncio
async def test_export_engine_markdown_to_pdf(export_engine, tmp_path):
    wf_id = uuid4()
    src_file = tmp_path / "sample.md"
    src_file.write_text("# Heading\n\nThis is a sample text.", encoding="utf-8")

    out_file = tmp_path / "sample.pdf"

    req = ExportRequest(
        workflow_id=wf_id,
        source_filepath=str(src_file),
        target_format=ExportFormat.PDF,
        output_path=str(out_file),
        title="Sample Document",
    )

    res = await export_engine.export(req)

    assert res.status == "SUCCESS"
    assert res.format == ExportFormat.PDF
    assert res.size_bytes > 0
    assert out_file.exists()
    assert res.workflow_id == wf_id
    assert res.download_url.startswith("/api/v1/artifacts/")


@pytest.mark.asyncio
async def test_export_engine_markdown_to_html(export_engine, tmp_path):
    wf_id = uuid4()
    src_file = tmp_path / "report.md"
    src_file.write_text("# Report Title\n\nSome body paragraph.", encoding="utf-8")

    out_file = tmp_path / "report.html"

    req = ExportRequest(
        workflow_id=wf_id,
        source_filepath=str(src_file),
        target_format=ExportFormat.HTML,
        output_path=str(out_file),
    )

    res = await export_engine.export(req)

    assert res.status == "SUCCESS"
    assert res.format == ExportFormat.HTML
    assert out_file.exists()
    html_content = out_file.read_text(encoding="utf-8")
    assert "Report Title" in html_content


@pytest.mark.asyncio
async def test_export_engine_image_conversion(export_engine, tmp_path):
    wf_id = uuid4()
    src_img = tmp_path / "source.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(src_img, format="PNG")

    out_img = tmp_path / "output.jpg"

    req = ExportRequest(
        workflow_id=wf_id,
        source_filepath=str(src_img),
        target_format=ExportFormat.JPEG,
        output_path=str(out_img),
    )

    res = await export_engine.export(req)

    assert res.status == "SUCCESS"
    assert res.format == ExportFormat.JPEG
    assert out_img.exists()
    assert res.size_bytes > 0


@pytest.mark.asyncio
async def test_export_engine_json_to_csv(export_engine, tmp_path):
    wf_id = uuid4()
    src_json = tmp_path / "data.json"
    src_json.write_text('{"name": "Alice", "role": "Engineer"}', encoding="utf-8")

    out_csv = tmp_path / "data.csv"

    req = ExportRequest(
        workflow_id=wf_id,
        source_filepath=str(src_json),
        target_format=ExportFormat.CSV,
        output_path=str(out_csv),
    )

    res = await export_engine.export(req)

    assert res.status == "SUCCESS"
    assert res.format == ExportFormat.CSV
    assert out_csv.exists()


@pytest.mark.asyncio
async def test_export_engine_missing_source(export_engine):
    wf_id = uuid4()
    req = ExportRequest(
        workflow_id=wf_id,
        source_filepath="/non/existent/path/file.txt",
        target_format=ExportFormat.PDF,
    )

    with pytest.raises(ExportError, match="Source artifact or file not found"):
        await export_engine.export(req)


@pytest.mark.asyncio
async def test_export_adapter_execution(export_adapter, tmp_path):
    wf_id = uuid4()
    src_file = tmp_path / "notes.txt"
    src_file.write_text("Hello AetherPhoenix Export System!", encoding="utf-8")

    out_pdf = tmp_path / "notes.pdf"

    task = Task(
        workflow_id=wf_id,
        task_name="Export Task",
        description="Convert notes to PDF",
        required_tool="export",
        category=TaskCategory.OTHER,
        expected_output="PDF File",
        inputs={
            "source_filepath": str(src_file),
            "target_format": "pdf",
            "output_path": str(out_pdf),
        },
    )

    result = await export_adapter.execute(task)

    assert result.success is True
    assert len(result.artifacts) == 1
    art = result.artifacts[0]
    assert art.artifact_type == ArtifactType.PDF
    assert art.workflow_id == wf_id
    assert out_pdf.exists()


@pytest.mark.asyncio
async def test_export_adapter_failure(export_adapter):
    wf_id = uuid4()
    task = Task(
        workflow_id=wf_id,
        task_name="Export Invalid Task",
        description="Try to export non-existent file",
        required_tool="export",
        category=TaskCategory.OTHER,
        expected_output="PDF File",
        inputs={
            "source_filepath": "/invalid/missing/file.txt",
            "target_format": "pdf",
        },
    )

    result = await export_adapter.execute(task)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "EXPORT_FAILED"


def test_register_export_tool():
    reg = ToolRegistry()
    registered = register_export_tool(reg)

    assert registered.name == "export"
    assert reg.get("export") is not None
