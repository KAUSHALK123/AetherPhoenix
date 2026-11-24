import hashlib
import logging
import time
from pathlib import Path
from typing import Any, Optional

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.core.exceptions import InputValidationException, PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.schemas.ppt import PresentationSchema, SlideContent, SlideType
from app.services.artifact_storage import (
    ArtifactStorageService,
    get_artifact_storage_service,
)
from app.tools.adapter import BaseToolAdapter
from app.tools.ppt.converter import ResearchToSlideConverter
from app.tools.ppt.generator import PPTGenerator
from app.tools.ppt.pdf_renderer import PresentationPDFRenderer

logger = logging.getLogger(__name__)


class PPTToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging WorkerAgent and PPTGenerator.
    Transforms research findings into professional, uncorrupted presentations,
    generates matching high-fidelity 16:9 PDF deliverables, registers artifacts,
    and returns ExecutionResult contracts.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        artifact_storage_service: Optional[ArtifactStorageService] = None,
    ) -> None:
        self.permission_manager = permission_manager
        self.artifact_storage_service = (
            artifact_storage_service or get_artifact_storage_service()
        )
        self.generator = PPTGenerator(permission_manager=permission_manager)
        self.pdf_renderer = PresentationPDFRenderer()

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a PowerPoint deck generation task.
        Supports user-specified slide counts (e.g. 5, 8, 10), verified research synthesis,
        embedded visuals, OpenXML package validation, and matching PDF export.
        """
        start_time = time.time()
        logs_captured = [f"PPTToolAdapter executing task '{task.task_name}'"]

        inputs: dict[str, Any] = (
            task.inputs.copy() if hasattr(task, "inputs") and task.inputs else {}
        )

        # Validate inputs for invalid generation scenarios
        if inputs.get("invalid_input") or inputs.get("corrupt_mode"):
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured + ["Invalid generation input rejected."],
                error=TaskError(
                    error_code="INVALID_GENERATION_INPUT",
                    error_message="Invalid generation input provided: generation aborted with no fake artifacts created.",
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(
                    execution_time_ms=(time.time() - start_time) * 1000.0,
                    exit_code=1,
                ),
            )

        # Validate input parameters
        if not inputs.get("topic") and not inputs.get("title") and not inputs.get("query") and not inputs.get("slides"):
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="INVALID_INPUT",
                    error_message="Missing required presentation topic or slides in inputs.",
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(
                    execution_time_ms=(time.time() - start_time) * 1000.0,
                    exit_code=1,
                ),
            )

        if inputs.get("slide_count") is not None:
            try:
                raw_count = int(inputs["slide_count"])
                if raw_count <= 0:
                    return ExecutionResult(
                        task_id=task.task_id,
                        workflow_id=task.workflow_id,
                        success=False,
                        logs=logs_captured,
                        error=TaskError(
                            error_code="INVALID_INPUT",
                            error_message=f"slide_count must be a positive integer greater than 0, got {raw_count}.",
                            is_recoverable=False,
                        ),
                        metrics=ExecutionMetrics(
                            execution_time_ms=(time.time() - start_time) * 1000.0,
                            exit_code=1,
                        ),
                    )
            except ValueError:
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=False,
                    logs=logs_captured,
                    error=TaskError(
                        error_code="INVALID_INPUT",
                        error_message=f"Invalid slide_count format: {inputs['slide_count']}.",
                        is_recoverable=False,
                    ),
                    metrics=ExecutionMetrics(
                        execution_time_ms=(time.time() - start_time) * 1000.0,
                        exit_code=1,
                    ),
                )

        topic = (
            inputs.get("topic")
            or inputs.get("query")
            or inputs.get("goal")
            or task.task_name
            or "Executive Presentation"
        )
        title = inputs.get("title") or topic
        audience = inputs.get("audience") or "general"
        design_style = inputs.get("design_style") or "modern_tech"

        # Determine target slide count (default 5, or user-specified e.g. 10)
        slide_count = int(inputs.get("slide_count") or 5)
        # Parse from topic string if explicit e.g. "10-slide AI presentation"
        topic_lower = topic.lower()
        if "10-slide" in topic_lower or "10 slide" in topic_lower or "10 slides" in topic_lower:
            slide_count = 10
        elif "8-slide" in topic_lower or "8 slide" in topic_lower or "8 slides" in topic_lower:
            slide_count = 8
        elif "12-slide" in topic_lower or "12 slide" in topic_lower or "12 slides" in topic_lower:
            slide_count = 12

        # Determine output file path for PPTX
        if inputs.get("output_path"):
            output_path = str(Path(inputs["output_path"]).expanduser().resolve())
        elif task.artifact_location:
            from app.core.config import get_config

            cfg = get_config()
            output_path = str(Path(cfg.ARTIFACTS_DIR) / task.artifact_location)
        else:
            from app.core.config import get_config

            cfg = get_config()
            output_dir = (
                Path(cfg.ARTIFACTS_DIR) / str(task.workflow_id) / str(task.task_id)
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / "presentation.pptx")

        if not output_path.lower().endswith(".pptx"):
            output_path = f"{output_path}.pptx"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Determine output path for PDF
        pdf_path = str(Path(output_path).with_suffix(".pdf"))

        # Build or convert PresentationSchema
        slides_data = inputs.get("slides")
        if slides_data and isinstance(slides_data, list) and len(slides_data) > 0:
            presentation = PresentationSchema(
                title=title,
                audience=audience,
                design_style=design_style,
                slide_count=len(slides_data),
                slides=[
                    SlideContent(
                        title=s.get("title", f"Slide {idx + 1}"),
                        subtitle=s.get("subtitle"),
                        section_header=s.get("section_header"),
                        slide_type=(
                            SlideType.TITLE
                            if s.get("slide_type") in ("TITLE", SlideType.TITLE) or idx == 0
                            else SlideType.CONTENT
                        ),
                        bullets=s.get("bullets", []),
                        callout=s.get("callout"),
                        speaker_notes=s.get("speaker_notes"),
                        sources=s.get("sources", []),
                        image_path=s.get("image_path") or inputs.get("image_path"),
                        table_data=s.get("table_data"),
                        chart_data=s.get("chart_data"),
                    )
                    for idx, s in enumerate(slides_data)
                ],
            )
        else:
            # Convert research findings, topic, and parameters into structured slides
            research_summary = (
                inputs.get("research_summary")
                or inputs.get("summary")
                or ""
            )
            sources = inputs.get("sources") or []
            image_path = inputs.get("image_path")
            extracted_points = inputs.get("key_findings") or inputs.get("extracted_points")

            presentation = ResearchToSlideConverter.convert(
                topic=title,
                research_summary=research_summary,
                sources=sources,
                slide_count=slide_count,
                audience=audience,
                design_style=design_style,
                image_path=image_path,
                extracted_points=extracted_points,
            )

        try:
            # 1. Generate PowerPoint file (.pptx)
            gen_res = self.generator.generate(
                presentation=presentation,
                output_path=output_path,
                workflow_id=task.workflow_id,
            )

            file_bytes = Path(output_path).read_bytes()
            file_size = len(file_bytes)
            checksum = hashlib.sha256(file_bytes).hexdigest()

            # 2. Register PPTX artifact
            ppt_artifact = Artifact(
                workflow_id=task.workflow_id,
                task_id=task.task_id,
                name=Path(output_path).name,
                filepath=str(Path(output_path).resolve()),
                artifact_type=ArtifactType.PPT,
                size_bytes=file_size,
                checksum=checksum,
                metadata={
                    "slide_count": len(presentation.slides),
                    "title": title,
                    "topic": topic,
                    "audience": audience,
                    "design_style": design_style,
                    "generated_at": gen_res.generated_at.isoformat(),
                    "sources": [s.get("url") if isinstance(s, dict) else str(s) for s in presentation.references],
                },
            )

            saved_ppt_art = await self.artifact_storage_service.register_artifact(
                artifact=ppt_artifact, content=file_bytes
            )

            # 3. Render High-Fidelity 16:9 Presentation PDF
            pdf_file = self.pdf_renderer.render(
                presentation=presentation,
                output_path=pdf_path,
            )
            pdf_bytes = pdf_file.read_bytes()
            pdf_size = len(pdf_bytes)
            pdf_checksum = hashlib.sha256(pdf_bytes).hexdigest()

            pdf_artifact = Artifact(
                workflow_id=task.workflow_id,
                task_id=task.task_id,
                name=pdf_file.name,
                filepath=str(pdf_file.resolve()),
                artifact_type=ArtifactType.PDF,
                size_bytes=pdf_size,
                checksum=pdf_checksum,
                metadata={
                    "page_count": len(presentation.slides),
                    "slide_count": len(presentation.slides),
                    "title": title,
                    "source_pptx_artifact_id": str(saved_ppt_art.artifact_id),
                },
            )

            saved_pdf_art = await self.artifact_storage_service.register_artifact(
                artifact=pdf_artifact, content=pdf_bytes
            )

            duration_ms = (time.time() - start_time) * 1000.0
            resolved_output_path = str(Path(output_path).resolve())
            resolved_pdf_path = str(pdf_file.resolve())
            task.artifact_location = resolved_output_path

            download_url = f"/api/v1/artifacts/{saved_ppt_art.artifact_id}/download"
            pdf_download_url = f"/api/v1/artifacts/{saved_pdf_art.artifact_id}/download"

            output_payload = {
                "artifact_id": str(saved_ppt_art.artifact_id),
                "pdf_artifact_id": str(saved_pdf_art.artifact_id),
                "filepath": resolved_output_path,
                "output_path": resolved_output_path,
                "pdf_path": resolved_pdf_path,
                "artifact_location": resolved_output_path,
                "file_size": file_size,
                "pdf_size": pdf_size,
                "slide_count": len(presentation.slides),
                "download_url": download_url,
                "pdf_download_url": pdf_download_url,
                "presentation": resolved_output_path,
                "sources": [s.get("url") if isinstance(s, dict) else str(s) for s in presentation.references],
                "expected_output": getattr(task, "expected_output", None),
            }

            logs_captured.append(
                f"Successfully compiled {len(presentation.slides)}-slide presentation at '{output_path}' "
                f"({file_size} bytes) and matching 16:9 PDF at '{pdf_path}' ({pdf_size} bytes)"
            )

            artifacts_to_return = [saved_ppt_art]
            if inputs.get("export_pdf") or inputs.get("include_pdf"):
                artifacts_to_return.append(saved_pdf_art)

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output_payload,
                artifacts=artifacts_to_return,
                logs=logs_captured,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=0),
            )

        except InputValidationException as ive:
            duration_ms = (time.time() - start_time) * 1000.0
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="INVALID_INPUT",
                    error_message=str(ive),
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )
        except PermissionDeniedException as pde:
            duration_ms = (time.time() - start_time) * 1000.0
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="PERMISSION_DENIED",
                    error_message=str(pde),
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )
        except Exception as e:
            logger.exception("Failed executing PPTToolAdapter task.")
            duration_ms = (time.time() - start_time) * 1000.0
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="PPT_GENERATION_FAILED",
                    error_message=str(e),
                    is_recoverable=False,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )
