from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from shared.contracts.artifact import Artifact, ArtifactType

from app.main import app
from app.services.artifact_storage import get_artifact_storage_service

client = TestClient(app)
storage_service = get_artifact_storage_service()


@pytest.mark.asyncio
async def test_artifacts_download_endpoint(tmp_path):
    # Register dummy PPTX file
    pptx_file = tmp_path / "test_presentation.pptx"
    pptx_file.write_bytes(b"PK\x03\x04Dummy PPTX binary header content")

    art = Artifact(
        workflow_id=uuid4(),
        task_id=uuid4(),
        name="test_presentation.pptx",
        filepath=str(pptx_file),
        artifact_type=ArtifactType.PPT,
        size_bytes=pptx_file.stat().st_size,
        checksum="dummy_checksum",
        metadata={"slide_count": 5},
    )

    saved = await storage_service.register_artifact(art)

    response = client.get(f"/api/v1/artifacts/{saved.artifact_id}/download")
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert response.content == b"PK\x03\x04Dummy PPTX binary header content"
