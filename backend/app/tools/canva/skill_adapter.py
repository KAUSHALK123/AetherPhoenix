"""
Canva Skill Adapter
Exposes the CanvaSkills layer as a standard ToolAdapter for WorkerAgent and Planner execution.
Handles skill routing, CRITICAL risk policy gating, screenshot/OCR verification checking,
and returns structured ExecutionResult contracts.
"""

import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.task import Task

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager
from app.services.artifact_storage import (
    ArtifactStorageService,
    get_artifact_storage_service,
)
from app.tools.adapter import BaseToolAdapter
from app.tools.browser.controller import BrowserController
from app.tools.canva.controller import CanvaBrowserController
from app.tools.canva.skills import CRITICAL_SKILLS, CanvaSkills
from app.tools.ocr.engine import OCREngine

logger = get_logger(__name__)


class CanvaSkillAdapter(BaseToolAdapter):
    """
    Adapter bridging the WorkerAgent and the CanvaSkills layer.
    Executes reusable high-level flows with screenshot and OCR verification.
    """

    def __init__(
        self,
        skills: Optional[CanvaSkills] = None,
        controller: Optional[BrowserController] = None,
        canva_controller: Optional[CanvaBrowserController] = None,
        ocr_engine: Optional[OCREngine] = None,
        permission_manager: Optional[PermissionManager] = None,
        artifact_storage_service: Optional[ArtifactStorageService] = None,
        artifacts_dir: str = "backend/artifacts",
    ):
        self.skills = skills or CanvaSkills(
            controller=controller,
            canva_controller=canva_controller,
            ocr_engine=ocr_engine,
            permission_manager=permission_manager,
            artifact_storage_service=artifact_storage_service,
            artifacts_dir=artifacts_dir,
        )
        self.permission_manager = permission_manager
        self.artifact_storage_service = (
            artifact_storage_service or get_artifact_storage_service()
        )

    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a Canva skill task by dispatching to the appropriate verified skill flow.
        """
        start_time = time.time()
        logs_captured: list[str] = [
            f"CanvaSkillAdapter executing task '{task.task_name}'"
        ]

        inputs: Dict[str, Any] = (
            getattr(task, "input_parameters", {}) or getattr(task, "inputs", {}) or {}
        )
        workflow_id = task.workflow_id
        task_id = task.task_id

        # Determine skill action from inputs or task metadata
        skill_action = (
            inputs.get("skill")
            or inputs.get("action")
            or getattr(task, "required_tool", "").replace("canva_skill_", "")
        )

        if not skill_action or skill_action in ("canva_skill_adapter", "canva_tool"):
            lower_name = f"{task.task_name} {task.description}".lower()
            if "publish" in lower_name:
                skill_action = "publish_design"
            elif "share" in lower_name:
                skill_action = "share_design"
            elif "purchase" in lower_name or "buy" in lower_name:
                skill_action = "purchase_template"
            elif "export" in lower_name or "download" in lower_name:
                skill_action = "export"
            elif "slide" in lower_name or "page" in lower_name:
                skill_action = "add_slide"
            elif "upload" in lower_name or "image" in lower_name:
                skill_action = "upload_image"
            elif "color" in lower_name or "theme" in lower_name or "palette" in lower_name:
                skill_action = "apply_brand_colors"
            elif "template" in lower_name:
                skill_action = "pick_template"
            elif "text" in lower_name or "content" in lower_name or "heading" in lower_name:
                skill_action = "edit_text"
            elif "create" in lower_name or "design" in lower_name or "poster" in lower_name or "presentation" in lower_name:
                skill_action = "create_design"
            else:
                skill_action = "open_canva"

        norm_action = skill_action.lower().replace("-", "_").strip()
        logs_captured.append(f"Interpreted Canva skill: '{norm_action}'")

        try:
            # 1. Dispatch to corresponding CanvaSkill
            if norm_action in ("open_canva", "open", "launch"):
                url = inputs.get("url", "https://www.canva.com")
                auto_handoff = inputs.get("auto_handoff", True)
                report = await self.skills.open_canva(
                    url=url,
                    auto_handoff=auto_handoff,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif norm_action in ("create_design", "create"):
                design_type = inputs.get("design_type", "presentation")
                width = inputs.get("width")
                height = inputs.get("height")
                topic = inputs.get("topic") or inputs.get("title")
                title = inputs.get("title") or topic
                report = await self.skills.create_design(
                    design_type=design_type,
                    width=width,
                    height=height,
                    topic=topic,
                    title=title,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif norm_action in ("pick_template", "template", "apply_template"):
                query = inputs.get("query") or inputs.get("template_name") or "presentation"
                report = await self.skills.pick_template(
                    query=query,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif norm_action in ("edit_text", "text", "add_text", "content"):
                text = inputs.get("text") or inputs.get("content") or "Heading"
                element = inputs.get("element")
                text_type = inputs.get("text_type", "heading")
                report = await self.skills.edit_text(
                    text=text,
                    element=element,
                    text_type=text_type,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif norm_action in ("add_slide", "slide", "add_page"):
                slide_num = inputs.get("slide_number") or inputs.get("slide")
                report = await self.skills.add_slide(
                    slide_number=slide_num,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif norm_action in ("upload_image", "upload"):
                image_path = inputs.get("image_path") or inputs.get("filepath") or ""
                report = await self.skills.upload_image(
                    image_path=image_path,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif norm_action in ("apply_brand_colors", "colors", "theme", "palette"):
                colors = inputs.get("colors") or inputs.get("palette") or ["#7D2AE8", "#00C4CC"]
                if isinstance(colors, str):
                    colors = [colors]
                bg = inputs.get("background_color")
                report = await self.skills.apply_brand_colors(
                    colors=colors,
                    background_color=bg,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif norm_action in ("export", "export_design", "download"):
                fmt = inputs.get("format") or inputs.get("export_format") or "pdf"
                output_path = inputs.get("output_path")
                report = await self.skills.export(
                    format=fmt,
                    output_path=output_path,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            # CRITICAL Skills
            elif norm_action in ("publish_design", "publish"):
                report = await self.skills.publish_design(
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif norm_action in ("share_design", "share"):
                email_or_link = inputs.get("email") or inputs.get("link")
                report = await self.skills.share_design(
                    email_or_link=email_or_link,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            elif norm_action in ("purchase_template", "purchase"):
                template_id = inputs.get("template_id") or inputs.get("template_name") or "premium_template"
                report = await self.skills.purchase_template(
                    template_id_or_name=template_id,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )

            else:
                raise ValueError(f"Unknown Canva skill action: '{norm_action}'")

            duration_ms = (time.time() - start_time) * 1000.0

            # 2. Check report status
            if report.status == "WAITING_FOR_HUMAN":
                logs_captured.append(f"Skill '{norm_action}' is WAITING_FOR_HUMAN: {report.stuck_reason}")
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=False,
                    output={
                        "status": "WAITING_FOR_HUMAN",
                        "skill": norm_action,
                        "goal": report.goal,
                        "message": report.message,
                        "screenshot_b64": report.final_screenshot_b64,
                        "what_agent_sees": report.what_agent_sees_now,
                    },
                    error=TaskError(
                        error_code="WAITING_FOR_HUMAN",
                        error_message=report.stuck_reason or "Canva authentication barrier requires human intervention.",
                    ),
                    logs=logs_captured,
                    metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=2),
                )

            if not report.success:
                logs_captured.append(f"Skill '{norm_action}' failed verification: {report.stuck_reason}")
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=False,
                    output={
                        "status": report.status,
                        "skill": norm_action,
                        "goal": report.goal,
                        "message": report.message,
                        "what_agent_sees": report.what_agent_sees_now,
                        "screenshot_b64": report.final_screenshot_b64,
                    },
                    error=TaskError(
                        error_code="VERIFICATION_FAILED",
                        error_message=report.stuck_reason or "Skill goal state could not be verified by screenshot/OCR.",
                    ),
                    logs=logs_captured,
                    metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
                )

            # Verified success
            logs_captured.append(f"Skill '{norm_action}' successfully completed and verified: {report.message}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output={
                    "status": "COMPLETED",
                    "skill": norm_action,
                    "goal": report.goal,
                    "message": report.message,
                    "what_agent_sees": report.what_agent_sees_now,
                    "screenshot_b64": report.final_screenshot_b64,
                    "actions_taken": report.actions_taken,
                    "total_steps": report.total_steps,
                },
                logs=logs_captured,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=0),
            )

        except PermissionDeniedException as pde:
            duration_ms = (time.time() - start_time) * 1000.0
            logs_captured.append(f"PermissionDeniedException in skill '{norm_action}': {pde}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="PERMISSION_DENIED",
                    error_message=str(pde),
                ),
                logs=logs_captured,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(f"CanvaSkillAdapter execution error in '{norm_action}': {e}", exc_info=True)
            logs_captured.append(f"Execution error: {str(e)}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="CANVA_SKILL_ERROR",
                    error_message=str(e),
                ),
                logs=logs_captured,
                metrics=ExecutionMetrics(execution_time_ms=duration_ms, exit_code=1),
            )
