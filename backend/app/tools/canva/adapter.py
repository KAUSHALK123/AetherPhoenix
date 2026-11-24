"""
Canva Tool Adapter
Connects the WorkerAgent to the CanvaBrowserController.
Implements the BaseToolAdapter interface, interprets task inputs,
executes live browser Canva actions, registers exported deliverables as artifacts,
and returns structured ExecutionResult contracts.
"""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.services.artifact_storage import (
    ArtifactStorageService,
    get_artifact_storage_service,
)
from app.tools.adapter import BaseToolAdapter
from app.tools.canva.controller import CanvaBrowserController

logger = logging.getLogger(__name__)


class CanvaToolAdapter(BaseToolAdapter):
    """
    Adapter bridging WorkerAgent and CanvaBrowserController.
    Handles Canva navigation, design creation, elements manipulation, and file delivery.
    """

    def __init__(
        self,
        controller: Optional[CanvaBrowserController] = None,
        permission_manager: Optional[PermissionManager] = None,
        artifact_storage_service: Optional[ArtifactStorageService] = None,
    ):
        self.controller = controller or CanvaBrowserController(
            permission_manager=permission_manager
        )
        self.permission_manager = permission_manager
        self.artifact_storage_service = (
            artifact_storage_service or get_artifact_storage_service()
        )

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a Canva task by interpreting its inputs and calling the controller.
        """
        start_time = time.time()
        logs_captured: list[str] = [
            f"CanvaToolAdapter executing task '{task.task_name}'"
        ]

        inputs: Dict[str, Any] = (
            getattr(task, "input_parameters", {}) or getattr(task, "inputs", {}) or {}
        )
        action = inputs.get("action")
        workflow_id = task.workflow_id
        task_id = task.task_id

        # Determine action from task_name or description if not explicitly set
        if not action:
            lower_name = f"{task.task_name} {task.description}".lower()
            if "export" in lower_name or "download" in lower_name:
                action = "export_design"
            elif "edit" in lower_name or "modify" in lower_name:
                action = "edit_design"
            elif (
                "create" in lower_name
                or "design" in lower_name
                or "poster" in lower_name
                or "thumbnail" in lower_name
            ):
                action = "create_design"
            elif "color" in lower_name or "theme" in lower_name:
                action = "change_colors"
            elif "template" in lower_name:
                action = "apply_template"
            elif "text" in lower_name:
                action = "add_text"
            else:
                action = "open_canva"

        logs_captured.append(f"Interpreted action: '{action}'")

        try:
            if action in ("open_canva", "open", "launch"):
                headless = inputs.get("headless", False)
                res = await self.controller.open_canva(
                    headless=headless,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data or {
                    "status": "opened",
                    "url": "https://www.canva.com",
                }
                logs_captured.append(
                    "Successfully opened Canva in live browser runtime."
                )

            elif action in ("create_design", "create"):
                design_type = inputs.get("design_type") or "instagram_post"
                width = inputs.get("width")
                height = inputs.get("height")
                unit = inputs.get("unit", "px")
                topic = inputs.get("topic") or inputs.get("title") or task.task_name
                title = inputs.get("title") or topic

                res = await self.controller.create_design(
                    design_type=design_type,
                    width=width,
                    height=height,
                    topic=topic,
                    title=title,
                    unit=unit,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data or {
                    "design_type": design_type,
                    "dimensions": f"{width or 1080} x {height or 1080} {unit}",
                    "topic": topic,
                    "editor_open": True,
                }
                logs_captured.append(
                    f"Created design '{design_type}' ({output.get('dimensions')}) with topic '{topic}'."
                )

                # If text content was also requested in inputs, apply it
                text_content = inputs.get("text_content") or inputs.get("text")
                if text_content:
                    await self.controller.add_text(
                        text=text_content,
                        workflow_id=workflow_id,
                        task_id=task_id,
                    )
                    logs_captured.append(
                        f"Added initial text content: '{text_content}'"
                    )

                # If elements or shapes requested, add them
                if inputs.get("shape") or inputs.get("element"):
                    shape = inputs.get("shape") or inputs.get("element") or "rectangle"
                    await self.controller.add_element(
                        shape=shape,
                        workflow_id=workflow_id,
                        task_id=task_id,
                    )
                    logs_captured.append(f"Added shape element: '{shape}'")

                # If color theme requested, apply it
                if inputs.get("palette") or inputs.get("colors") or inputs.get("color"):
                    palette = inputs.get("palette") or inputs.get("colors")
                    if isinstance(palette, str):
                        palette = [palette]
                    await self.controller.change_colors(
                        palette=palette,
                        background_color=inputs.get("background_color"),
                        workflow_id=workflow_id,
                        task_id=task_id,
                    )
                    logs_captured.append(f"Applied color theme: {palette}")

            elif action in ("edit_design", "edit", "modify"):
                design_ref = (
                    inputs.get("design_url")
                    or inputs.get("design_id")
                    or "https://www.canva.com/design"
                )
                res = await self.controller.edit_existing_design(
                    design_url_or_id=design_ref,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data or {
                    "status": "editor_opened",
                    "design_ref": design_ref,
                }
                logs_captured.append(
                    f"Opened existing Canva design for editing: '{design_ref}'"
                )

                # Apply any modifications requested
                if inputs.get("text"):
                    await self.controller.add_text(
                        text=inputs["text"],
                        workflow_id=workflow_id,
                        task_id=task_id,
                    )
                    logs_captured.append(f"Updated text: '{inputs['text']}'")
                if inputs.get("palette") or inputs.get("color"):
                    pal = inputs.get("palette") or [inputs["color"]]
                    await self.controller.change_colors(
                        palette=pal, workflow_id=workflow_id, task_id=task_id
                    )
                    logs_captured.append(f"Updated colors: {pal}")

            elif action in ("add_text", "text"):
                text = inputs.get("text") or inputs.get("content") or "Heading"
                text_type = inputs.get("text_type", "heading")
                res = await self.controller.add_text(
                    text=text,
                    text_type=text_type,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data or {"action": "add_text", "text": text}
                logs_captured.append(f"Added text element: '{text}'")

            elif action in ("add_element", "shape", "elements"):
                shape = inputs.get("shape") or "rectangle"
                res = await self.controller.add_element(
                    shape=shape,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data or {"action": "add_element", "shape": shape}
                logs_captured.append(f"Added canvas element: '{shape}'")

            elif action in ("change_colors", "theme", "colors"):
                palette = inputs.get("palette") or inputs.get("colors")
                if isinstance(palette, str):
                    palette = [palette]
                bg_color = inputs.get("background_color")
                res = await self.controller.change_colors(
                    palette=palette,
                    background_color=bg_color,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data or {"action": "change_colors", "palette": palette}
                logs_captured.append(f"Updated color scheme: {palette}")

            elif action in ("apply_template", "template"):
                template_name = (
                    inputs.get("template_name") or inputs.get("template") or "Modern"
                )
                res = await self.controller.apply_template(
                    template_name=template_name,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
                output = res.data or {
                    "action": "apply_template",
                    "template_name": template_name,
                }
                logs_captured.append(f"Applied design template: '{template_name}'")

            elif action in ("export_design", "export", "download"):
                export_format = (
                    inputs.get("format") or inputs.get("export_format") or "pdf"
                )
                output_path = inputs.get("output_path")

                # If no specific output path provided, generate one under artifacts directory
                if not output_path:
                    ext = (
                        "pdf"
                        if export_format.lower() == "pdf"
                        else (
                            "jpg" if export_format.lower() in ("jpg", "jpeg") else "png"
                        )
                    )
                    filename = f"canva_{task_id}.{ext}"
                    output_path = str(
                        Path("backend") / "artifacts" / str(workflow_id) / filename
                    )

                res = await self.controller.export_design(
                    export_format=export_format,
                    output_path=output_path,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

                actual_filepath = res.data.get("filepath", output_path)
                filename = os.path.basename(actual_filepath)
                file_size = (
                    os.path.getsize(actual_filepath)
                    if os.path.exists(actual_filepath)
                    else 0
                )

                # Compute checksum
                checksum = None
                if os.path.exists(actual_filepath):
                    with open(actual_filepath, "rb") as f:
                        checksum = hashlib.sha256(f.read()).hexdigest()

                # Determine ArtifactType
                art_type = (
                    ArtifactType.PDF
                    if export_format.lower() == "pdf"
                    else ArtifactType.IMAGES
                )

                # Register deliverable in ArtifactStorageService
                artifact = Artifact(
                    workflow_id=workflow_id,
                    task_id=task_id,
                    name=filename,
                    filepath=actual_filepath,
                    artifact_type=art_type,
                    size_bytes=file_size,
                    checksum=checksum,
                    metadata={
                        "source": "canva",
                        "format": export_format.lower(),
                        "design_info": self.controller.active_design_info,
                    },
                )

                if self.artifact_storage_service:
                    await self.artifact_storage_service.save_artifact(
                        artifact=artifact, source_path=actual_filepath
                    )
                    logs_captured.append(
                        f"Artifact '{filename}' registered in ArtifactStorageService (ID: {artifact.artifact_id})."
                    )

                download_url = f"/api/v1/artifacts/{artifact.artifact_id}/download"

                output = {
                    "action": "export_design",
                    "artifact_id": str(artifact.artifact_id),
                    "filename": filename,
                    "filepath": actual_filepath,
                    "size_bytes": file_size,
                    "download_url": download_url,
                    "format": export_format.lower(),
                    "verified": file_size > 0,
                }
                logs_captured.append(
                    f"Exported valid deliverable: {filename} ({file_size} bytes)"
                )

            else:
                raise ValueError(f"Unsupported Canva action: '{action}'")

            duration_ms = (time.time() - start_time) * 1000.0
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=output,
                logs=logs_captured,
                metrics=ExecutionMetrics(
                    execution_time_ms=duration_ms,
                    exit_code=0,
                ),
            )

        except PermissionDeniedException as pe:
            duration_ms = (time.time() - start_time) * 1000.0
            logs_captured.append(f"Permission denied: {pe}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="PERMISSION_DENIED",
                    error_message=str(pe),
                ),
                logs=logs_captured,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(f"CanvaToolAdapter execution failed: {e}", exc_info=True)
            logs_captured.append(f"Execution error: {str(e)}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="CANVA_EXECUTION_ERROR",
                    error_message=str(e),
                ),
                logs=logs_captured,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )
