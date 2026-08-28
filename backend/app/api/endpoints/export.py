from uuid import UUID

from fastapi import APIRouter, HTTPException
from shared.contracts.export import ExportFormat, ExportRequest, ExportResult

from app.tools.export.engine import ExportEngine, ExportError

router = APIRouter()
export_engine = ExportEngine()


@router.post("", response_model=ExportResult)
async def export_artifact(request: ExportRequest) -> ExportResult:
    """
    Unified export endpoint for converting workflow artifacts and task results
    into supported formats (PDF, PPTX, Markdown, DOCX, HTML, Images, CSV, JSON, TXT).
    """
    try:
        return await export_engine.export(request)
    except ExportError as ee:
        raise HTTPException(status_code=400, detail=str(ee))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/{artifact_id}", response_model=ExportResult)
async def export_artifact_by_id(
    artifact_id: UUID,
    target_format: ExportFormat = ExportFormat.PDF,
    workflow_id: UUID | None = None,
    output_path: str | None = None,
) -> ExportResult:
    """
    Exports a specific registered artifact by ID to the target format.
    """
    if not workflow_id:
        # Resolve workflow_id from artifact metadata
        art = await export_engine.artifact_storage_service.get_artifact(artifact_id)
        if not art:
            raise HTTPException(
                status_code=404, detail=f"Artifact {artifact_id} not found."
            )
        workflow_id = art.workflow_id

    req = ExportRequest(
        workflow_id=workflow_id,
        source_artifact_id=artifact_id,
        target_format=target_format,
        output_path=output_path,
    )

    try:
        return await export_engine.export(req)
    except ExportError as ee:
        raise HTTPException(status_code=400, detail=str(ee))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
