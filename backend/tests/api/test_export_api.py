from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from shared.contracts.artifact import Artifact
from shared.contracts.export import ExportFormat, ExportResult

from app.main import app
from app.tools.export.engine import ExportError

client = TestClient(app)


@pytest.mark.asyncio
@patch("app.api.endpoints.export.export_engine")
async def test_export_artifact_success(mock_engine):
    """Verify posting a valid ExportRequest converts the artifact successfully."""
    workflow_id = uuid4()
    artifact_id = uuid4()

    # Setup expected outcome
    expected_result = ExportResult(
        workflow_id=workflow_id,
        name="Converted PDF",
        filepath="/path/to/output.pdf",
        download_url="/downloads/output.pdf",
        format=ExportFormat.PDF,
        size_bytes=1024,
        checksum="abcd123",
        source_artifact_id=artifact_id,
    )
    mock_engine.export = AsyncMock(return_value=expected_result)

    response = client.post(
        "/api/v1/export",
        json={
            "workflow_id": str(workflow_id),
            "target_format": "pdf",
            "source_artifact_id": str(artifact_id),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == str(workflow_id)
    assert data["format"] == "pdf"
    assert data["download_url"] == "/downloads/output.pdf"
    mock_engine.export.assert_called_once()


@pytest.mark.asyncio
@patch("app.api.endpoints.export.export_engine")
async def test_export_artifact_client_error(mock_engine):
    """Verify HTTPException 400 is raised if ExportEngine raises ExportError."""
    workflow_id = uuid4()
    mock_engine.export = AsyncMock(side_effect=ExportError("Unsupported export format"))

    response = client.post(
        "/api/v1/export",
        json={
            "workflow_id": str(workflow_id),
            "target_format": "docx",
        },
    )

    assert response.status_code == 400
    assert "Unsupported export format" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.api.endpoints.export.export_engine")
async def test_export_artifact_server_error(mock_engine):
    """Verify HTTPException 500 is raised if ExportEngine raises general exception."""
    workflow_id = uuid4()
    mock_engine.export = AsyncMock(side_effect=RuntimeError("Disk write failed"))

    response = client.post(
        "/api/v1/export",
        json={
            "workflow_id": str(workflow_id),
            "target_format": "html",
        },
    )

    assert response.status_code == 500
    assert "Export failed: Disk write failed" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.api.endpoints.export.export_engine")
async def test_export_artifact_by_id_success(mock_engine):
    """Verify export_artifact_by_id resolves workflow ID and executes export."""
    workflow_id = uuid4()
    artifact_id = uuid4()

    # Mock artifact storage service lookup
    mock_artifact = MagicMock(spec=Artifact)
    mock_artifact.workflow_id = workflow_id
    mock_engine.artifact_storage_service.get_artifact = AsyncMock(
        return_value=mock_artifact
    )

    expected_result = ExportResult(
        workflow_id=workflow_id,
        name="Converted CSV",
        filepath="/path/to/output.csv",
        download_url="/downloads/output.csv",
        format=ExportFormat.CSV,
        size_bytes=512,
        checksum="xyz789",
        source_artifact_id=artifact_id,
    )
    mock_engine.export = AsyncMock(return_value=expected_result)

    # Call endpoint without workflow_id query param
    response = client.post(
        f"/api/v1/export/{artifact_id}?target_format=csv",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "csv"
    assert data["download_url"] == "/downloads/output.csv"

    # Assert get_artifact was checked to resolve workflow ID
    mock_engine.artifact_storage_service.get_artifact.assert_called_once_with(
        artifact_id
    )
    mock_engine.export.assert_called_once()


@pytest.mark.asyncio
@patch("app.api.endpoints.export.export_engine")
async def test_export_artifact_by_id_not_found(mock_engine):
    """Verify HTTPException 404 is raised if artifact ID is not found in registry."""
    artifact_id = uuid4()
    mock_engine.artifact_storage_service.get_artifact = AsyncMock(return_value=None)

    response = client.post(
        f"/api/v1/export/{artifact_id}?target_format=pptx",
    )

    assert response.status_code == 404
    assert f"Artifact {artifact_id} not found." in response.json()["detail"]
