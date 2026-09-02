import mimetypes
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from shared.contracts.artifact import Artifact, ArtifactType

from app.services.artifact_storage import get_artifact_storage_service

router = APIRouter()
artifact_storage_service = get_artifact_storage_service()

# Register custom MIME types for office formats if missing
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pptx",
)
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".docx",
)


@router.get("", response_model=list[Artifact])
async def list_artifacts(
    workflow_id: UUID | None = None,
    task_id: UUID | None = None,
    artifact_type: ArtifactType | None = None,
) -> list[Artifact]:
    """Lists registered workflow and task artifacts."""
    return await artifact_storage_service.list_artifacts(
        workflow_id=workflow_id,
        task_id=task_id,
        artifact_type=artifact_type,
    )


@router.get("/{artifact_id}", response_model=Artifact)
async def get_artifact(artifact_id: UUID) -> Artifact:
    """Retrieves artifact metadata by artifact ID."""
    art = await artifact_storage_service.get_artifact(artifact_id)
    if not art:
        raise HTTPException(
            status_code=404, detail=f"Artifact '{artifact_id}' not found."
        )
    return art


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: UUID) -> FileResponse:
    """
    Downloads the actual binary file for a registered artifact by ID.
    Enforces native binary MIME types (e.g. PPTX, PDF, CSV, PNG).
    """
    art = await artifact_storage_service.get_artifact(artifact_id)
    if not art:
        raise HTTPException(
            status_code=404, detail=f"Artifact '{artifact_id}' not found."
        )

    filepath = Path(art.filepath)
    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"File for artifact '{art.name}' does not exist on disk at"
                f" '{filepath}'."
            ),
        )

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(filepath))
    if not mime_type:
        ext = filepath.suffix.lower()
        if ext == ".pptx":
            mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"  # noqa: E501
        elif ext == ".pdf":
            mime_type = "application/pdf"
        elif ext == ".csv":
            mime_type = "text/csv"
        elif ext == ".json":
            mime_type = "application/json"
        else:
            mime_type = "application/octet-stream"

    filename = art.name if art.name and not art.name.startswith("/") else filepath.name
    if not filename.endswith(filepath.suffix):
        filename = f"{filename}{filepath.suffix}"

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
