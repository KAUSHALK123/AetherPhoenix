import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from shared.contracts.artifact import Artifact, ArtifactType

from app.agents.worker.agent import WorkerAgent
from app.services.artifact_storage import (
    ArtifactStorageService,
    LocalFileSystemArtifactStorageProvider,
)
from app.tools.registry import ToolRegistry


@pytest.fixture
def temp_dir():
    """Provides a temporary directory for test artifact storage."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def provider(temp_dir):
    """Provides a LocalFileSystemArtifactStorageProvider backed by temp_dir."""
    return LocalFileSystemArtifactStorageProvider(base_dir=temp_dir)


@pytest.fixture
def service(provider):
    """Provides an ArtifactStorageService instance."""
    return ArtifactStorageService(provider=provider)


@pytest.mark.asyncio
async def test_artifact_creation_and_registration(service, temp_dir):
    """Verifies creating, persisting, and retrieving artifact metadata and content."""
    wf_id = uuid4()
    task_id = uuid4()
    art = Artifact(
        workflow_id=wf_id,
        task_id=task_id,
        name="test_report.pdf",
        filepath="dummy/path",
        artifact_type=ArtifactType.PDF,
    )

    content = b"%PDF-1.4 sample pdf content bytes"
    saved = await service.register_artifact(artifact=art, content=content)

    assert saved.artifact_id == art.artifact_id
    assert saved.workflow_id == wf_id
    assert saved.task_id == task_id
    assert saved.size_bytes == len(content)
    assert saved.checksum == Artifact.compute_checksum(content)
    assert Path(saved.filepath).exists()

    # Retrieve metadata
    meta = await service.get_artifact(art.artifact_id)
    assert meta is not None
    assert meta.name == "test_report.pdf"

    # Retrieve content bytes
    retrieved_content = await service.get_artifact_content(art.artifact_id)
    assert retrieved_content == content


@pytest.mark.asyncio
async def test_save_artifact_from_source_path(service, temp_dir):
    """Verifies persisting artifact from an existing source file path."""
    source_file = temp_dir / "source_doc.txt"
    source_file.write_text("Hello World Artifact Content", encoding="utf-8")

    art = Artifact(
        workflow_id=uuid4(),
        task_id=uuid4(),
        name="source_doc.txt",
        filepath=str(source_file),
        artifact_type=ArtifactType.REPORTS,
    )

    saved = await service.register_artifact(artifact=art, source_path=source_file)
    assert saved.size_bytes > 0
    assert saved.checksum is not None

    retrieved = await service.get_artifact_content(art.artifact_id)
    assert retrieved == b"Hello World Artifact Content"


@pytest.mark.asyncio
async def test_retrieve_invalid_artifact(service):
    """Verifies safe behavior when querying non-existent artifact IDs."""
    fake_id = uuid4()
    meta = await service.get_artifact(fake_id)
    assert meta is None

    content = await service.get_artifact_content(fake_id)
    assert content is None


@pytest.mark.asyncio
async def test_artifact_listing_and_filtering(service):
    """Verifies listing artifacts by workflow, task, and type."""
    wf_1 = uuid4()
    wf_2 = uuid4()
    t_1 = uuid4()
    t_2 = uuid4()

    art1 = Artifact(
        workflow_id=wf_1,
        task_id=t_1,
        name="screenshot.png",
        filepath="dummy",
        artifact_type=ArtifactType.SCREENSHOT,
    )
    art2 = Artifact(
        workflow_id=wf_1,
        task_id=t_2,
        name="report.pdf",
        filepath="dummy",
        artifact_type=ArtifactType.PDF,
    )
    art3 = Artifact(
        workflow_id=wf_2,
        task_id=t_1,
        name="chart.png",
        filepath="dummy",
        artifact_type=ArtifactType.SCREENSHOT,
    )

    await service.register_artifact(art1, content=b"img1")
    await service.register_artifact(art2, content=b"pdf1")
    await service.register_artifact(art3, content=b"img2")

    # Filter by workflow_id
    wf1_list = await service.list_artifacts(workflow_id=wf_1)
    assert len(wf1_list) == 2

    # Filter by task_id
    t1_list = await service.list_artifacts(task_id=t_1)
    assert len(t1_list) == 2

    # Filter by artifact_type
    screenshots = await service.list_artifacts(artifact_type=ArtifactType.SCREENSHOT)
    assert len(screenshots) == 2


@pytest.mark.asyncio
async def test_artifact_deletion_and_lifecycle(service):
    """Verifies deletion rules and protection enforcement."""
    art_unprotected = Artifact(
        workflow_id=uuid4(),
        task_id=uuid4(),
        name="temp.txt",
        filepath="dummy",
        artifact_type=ArtifactType.DATA,
    )
    art_protected = Artifact(
        workflow_id=uuid4(),
        task_id=uuid4(),
        name="protected.pdf",
        filepath="dummy",
        artifact_type=ArtifactType.PDF,
        metadata={"protected": True},
    )

    saved1 = await service.register_artifact(art_unprotected, content=b"delete me")
    saved2 = await service.register_artifact(art_protected, content=b"protect me")

    # Delete unprotected
    deleted1 = await service.delete_artifact(saved1.artifact_id)
    assert deleted1 is True
    assert await service.get_artifact(saved1.artifact_id) is None

    # Delete protected without force (should raise ValueError)
    with pytest.raises(ValueError, match="protected by lifecycle rules"):
        await service.delete_artifact(saved2.artifact_id, force=False)

    # Delete protected with force=True
    deleted2 = await service.delete_artifact(saved2.artifact_id, force=True)
    assert deleted2 is True
    assert await service.get_artifact(saved2.artifact_id) is None


@pytest.mark.asyncio
async def test_duplicate_artifact_registration(service):
    """Verifies registering updated metadata/content for an existing artifact ID."""
    art = Artifact(
        workflow_id=uuid4(),
        task_id=uuid4(),
        name="file_v1.txt",
        filepath="dummy",
        artifact_type=ArtifactType.CODE,
    )

    await service.register_artifact(art, content=b"v1 content")
    v1_meta = await service.get_artifact(art.artifact_id)
    assert v1_meta.size_bytes == 10

    # Re-register with updated content
    await service.register_artifact(art, content=b"v2 updated content")
    v2_meta = await service.get_artifact(art.artifact_id)
    assert v2_meta.size_bytes == 18
    assert await service.get_artifact_content(art.artifact_id) == b"v2 updated content"


@pytest.mark.asyncio
async def test_missing_source_path_failure(service):
    """Verifies exception handling when source_path does not exist."""
    art = Artifact(
        workflow_id=uuid4(),
        name="non_existent.txt",
        filepath="dummy",
        artifact_type=ArtifactType.DATA,
    )

    with pytest.raises(FileNotFoundError):
        await service.register_artifact(
            artifact=art, source_path=Path("non/existent/path/file.txt")
        )


@pytest.mark.asyncio
async def test_worker_agent_artifact_integration(service):
    """Verifies WorkerAgent.register_artifact method and artifact storage execution."""
    registry = ToolRegistry()
    worker = WorkerAgent(tool_registry=registry, artifact_storage_service=service)

    art = Artifact(
        workflow_id=uuid4(),
        task_id=uuid4(),
        name="worker_generated_doc.pdf",
        filepath="dummy",
        artifact_type=ArtifactType.PDF,
    )

    registered = await worker.register_artifact(
        artifact=art, content=b"%PDF worker generated content"
    )
    assert registered.artifact_id == art.artifact_id

    stored = await service.get_artifact(art.artifact_id)
    assert stored is not None
    assert stored.name == "worker_generated_doc.pdf"
