import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.pdf import (
    HeadingElement,
    ParagraphElement,
    PDFDocumentInput,
    PDFElement,
    PDFGenerationResult,
)
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.config import get_config
from app.core.exceptions import PermissionDeniedException
from app.core.permissions import PermissionManager
from app.services.artifact_storage import (
    ArtifactStorageService,
    get_artifact_storage_service,
)
from app.tools.adapter import BaseToolAdapter
from app.tools.pdf.generator import PDFGenerator
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class _AwaitablePDFResult(PDFGenerationResult):
    """Subclass of PDFGenerationResult that can also be awaited if called in async context."""

    def __await__(self):
        async def _coro():
            return self

        return _coro().__await__()


class PDFToolAdapter(BaseToolAdapter):
    """
    Tool Adapter bridging WorkerAgent and PDFGenerator.
    Compiles structured PDF documents from Tasks or payloads, registers artifacts,
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
        self.generator = PDFGenerator(permission_manager=permission_manager)

    def execute(
        self,
        task_or_payload: Any,
        workflow_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Executes PDF generation. Supports both Task contract objects (for WorkerAgent)
        and raw dictionary/PDFDocumentInput payloads (for direct/sync invocations).
        """
        if isinstance(task_or_payload, Task):
            # Asynchronous Task execution for WorkerAgent
            return self._execute_task(task_or_payload)
        else:
            # Synchronous / payload execution
            return self._execute_payload(task_or_payload, workflow_id=workflow_id)

    def _execute_payload(
        self, payload: Any, workflow_id: Optional[UUID] = None
    ) -> _AwaitablePDFResult:
        """Executes PDF generation from raw dictionary payload or PDFDocumentInput."""
        if isinstance(payload, PDFDocumentInput):
            input_data = payload
        else:
            payload_copy = dict(payload)
            if "title" not in payload_copy:
                payload_copy["title"] = payload_copy.get(
                    "topic", "Generated PDF Document"
                )
            if "output_path" not in payload_copy:
                cfg = get_config()
                out_dir = Path(cfg.ARTIFACTS_DIR) / "pdf_outputs"
                out_dir.mkdir(parents=True, exist_ok=True)
                payload_copy["output_path"] = str(out_dir / "document.pdf")

            input_data = PDFDocumentInput.model_validate(payload_copy)

        if workflow_id and not input_data.workflow_id:
            input_data.workflow_id = workflow_id

        gen_res = self.generator.generate(input_data)
        return _AwaitablePDFResult(**gen_res.model_dump())

    async def _execute_task(self, task: Task) -> ExecutionResult:
        """Executes a Task contract, generates a valid PDF, registers the artifact, and returns ExecutionResult."""
        start_time = time.time()
        logs_captured = [f"PDFToolAdapter executing task '{task.task_name}'"]

        inputs: Dict[str, Any] = (
            task.inputs.copy() if hasattr(task, "inputs") and task.inputs else {}
        )

        topic = (
            inputs.get("title")
            or inputs.get("topic")
            or inputs.get("document_title")
            or inputs.get("goal")
            or task.task_name
            or "Executive PDF Document"
        )
        title = inputs.get("title") or topic
        subtitle = inputs.get("subtitle") or inputs.get("description")
        author = inputs.get("author") or "AetherPhoenix"

        # Determine output file path
        if inputs.get("output_path"):
            output_path = str(Path(inputs["output_path"]).expanduser().resolve())
        elif inputs.get("filepath"):
            output_path = str(Path(inputs["filepath"]).expanduser().resolve())
        elif task.artifact_location:
            cfg = get_config()
            if Path(task.artifact_location).is_absolute():
                output_path = str(Path(task.artifact_location))
            else:
                output_path = str(Path(cfg.ARTIFACTS_DIR) / task.artifact_location)
        else:
            cfg = get_config()
            output_dir = (
                Path(cfg.ARTIFACTS_DIR) / str(task.workflow_id) / str(task.task_id)
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / "document.pdf")

        if not output_path.lower().endswith(".pdf"):
            output_path = f"{output_path}.pdf"

        # Build elements from inputs
        elements_data = inputs.get("elements")
        pdf_elements: List[PDFElement] = []
        if elements_data and isinstance(elements_data, list) and len(elements_data) > 0:
            for item in elements_data:
                if isinstance(item, dict):
                    el_type = item.get("element_type", "paragraph")
                    if el_type == "heading":
                        pdf_elements.append(
                            HeadingElement(
                                text=item.get("text", "Heading"),
                                level=item.get("level", 1),
                            )
                        )
                    else:
                        pdf_elements.append(
                            ParagraphElement(
                                text=item.get("text", ""),
                                bold=item.get("bold", False),
                                italic=item.get("italic", False),
                            )
                        )
        elif inputs.get("content") or inputs.get("text"):
            raw_text = inputs.get("content") or inputs.get("text") or ""
            pdf_elements.append(HeadingElement(text=title, level=1))
            for para in str(raw_text).split("\n\n"):
                para_clean = para.strip()
                if para_clean:
                    pdf_elements.append(ParagraphElement(text=para_clean))
        else:
            # Default structured document content
            pdf_elements = [
                HeadingElement(text=title, level=1),
                ParagraphElement(
                    text="This document provides comprehensive analysis, operational telemetry, and implementation details.",
                    bold=False,
                ),
                HeadingElement(text="1. Executive Summary", level=2),
                ParagraphElement(
                    text="The system architecture combines autonomous worker capabilities, supervisory validation contracts, and self-healing resilience.",
                    bold=False,
                ),
                HeadingElement(
                    text="2. Technical Specifications & Verification", level=2
                ),
                ParagraphElement(
                    text="All execution stages conform strictly to typed Pydantic contracts and rigorous lifecycle verifications.",
                    bold=False,
                ),
                HeadingElement(text="3. Conclusion", level=2),
                ParagraphElement(
                    text="Execution verification concluded with complete integrity checks and validated checksums.",
                    bold=False,
                ),
            ]

        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            doc_input = PDFDocumentInput(
                title=title,
                subtitle=subtitle,
                author=author,
                workflow_id=task.workflow_id,
                task_id=task.task_id,
                elements=pdf_elements,
                output_path=output_path,
                metadata=inputs,
            )

            gen_res = self.generator.generate(doc_input)
            file_bytes = Path(output_path).read_bytes()
            file_size = len(file_bytes)

            # Register artifact in storage service
            artifact = self.generator.create_artifact(
                gen_res, workflow_id=task.workflow_id, task_id=task.task_id
            )
            saved_artifact = await self.artifact_storage_service.register_artifact(
                artifact=artifact, content=file_bytes
            )

            resolved_output_path = str(Path(output_path).resolve())
            task.artifact_location = resolved_output_path

            duration_ms = (time.time() - start_time) * 1000.0
            download_url = f"/api/v1/artifacts/{saved_artifact.artifact_id}/download"

            output_payload = {
                "artifact_id": str(saved_artifact.artifact_id),
                "filepath": resolved_output_path,
                "output_path": resolved_output_path,
                "artifact_location": resolved_output_path,
                "pdf_path": resolved_output_path,
                "file_size": file_size,
                "page_count": gen_res.page_count,
                "download_url": download_url,
                "expected_output": getattr(task, "expected_output", None),
            }

            logs_captured.append(
                f"Successfully compiled PDF document at '{resolved_output_path}' ({file_size} bytes)"
            )

            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output_payload,
                artifacts=[saved_artifact],
                logs=logs_captured,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=0),
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
            logger.exception("Failed executing PDFToolAdapter task.")
            duration_ms = (time.time() - start_time) * 1000.0
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                logs=logs_captured,
                error=TaskError(
                    error_code="PDF_GENERATION_FAILED",
                    error_message=str(e),
                    is_recoverable=True,
                ),
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )


def register_pdf_tool(registry: ToolRegistry) -> Tool:
    """
    Registers the PDF Generator tool and aliases with the provided ToolRegistry.
    """
    pdf_tool = Tool(
        name="pdf_generator",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.pdf.tool.PDFToolAdapter",
        dependencies=["reportlab"],
        required_permissions=[PermissionType.FILE_SYSTEM.value],
    )
    registry.register(pdf_tool)

    # Register alias "pdf_tool" for flexible planner binding
    try:
        registry.register(
            Tool(
                name="pdf_tool",
                version="1.0.0",
                status=ToolState.READY,
                health=ToolHealth.HEALTHY,
                adapter="app.tools.pdf.tool.PDFToolAdapter",
                dependencies=["reportlab"],
                required_permissions=[PermissionType.FILE_SYSTEM.value],
            )
        )
    except ValueError:
        pass

    logger.info("Successfully registered 'pdf_generator' tool in ToolRegistry.")
    return pdf_tool
