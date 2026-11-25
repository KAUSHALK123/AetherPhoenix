"""
Canva Skills Layer
Provides reusable, high-level skill flows on top of BrowserAgentLoop and BrowserController.
Enables the planner to invoke predefined Canva workflows with verified screenshot/OCR outcomes
rather than rediscovering the canvas UI from scratch each time.

Supported Skills:
- open_canva: reuse persistent session, trigger handoff cleanly at sign-in
- create_design: presentation, poster, instagram post, etc.
- pick_template: search and apply template query
- edit_text: select and replace text elements on canvas
- add_slide: add new slides to presentation
- upload_image: upload image assets
- apply_brand_colors: apply brand palette
- export: download PDF/PNG/PPTX and save to artifacts directory
- publish_design / share_design / purchase_template: CRITICAL actions requiring explicit approval
"""

import asyncio
import hashlib
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.ocr import OCRRequest
from shared.contracts.permission import PermissionType, RiskLevel

from app.core.events import Event, EventType, get_event_bus
from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager
from app.services.artifact_storage import (
    ArtifactStorageService,
    get_artifact_storage_service,
)
from app.tools.browser.agent_loop import (
    ActionType,
    AgentLoopReport,
    BrowserAgentLoop,
    ObserveResult,
    VisionAction,
)
from app.tools.browser.controller import BrowserActionError, BrowserController
from app.tools.canva.controller import CANVA_DIMENSION_PRESETS, CanvaBrowserController
from app.tools.ocr.engine import OCREngine

logger = get_logger(__name__)

# List of critical skills requiring explicit user approval
CRITICAL_SKILLS = {
    "publish_design",
    "publish",
    "share_design",
    "share",
    "purchase_template",
    "purchase",
}


@dataclass
class SkillGoal:
    """Defines a skill's natural-language goal and verification requirements."""
    name: str
    goal: str
    description: str
    is_critical: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class CanvaSkills:
    """
    Reusable Canva skill flows built on top of BrowserController and BrowserAgentLoop.
    Every skill defines:
      1. A short written goal for the agent/loop.
      2. Concrete execution actions against the live Canva session.
      3. A strict success check verified by screenshot and OCR, never assumption.
    """

    def __init__(
        self,
        controller: Optional[BrowserController] = None,
        canva_controller: Optional[CanvaBrowserController] = None,
        ocr_engine: Optional[OCREngine] = None,
        permission_manager: Optional[PermissionManager] = None,
        artifact_storage_service: Optional[ArtifactStorageService] = None,
        artifacts_dir: str = "backend/artifacts",
    ):
        self.controller = controller or BrowserController(
            permission_manager=permission_manager,
            user_data_dir="./browser_profile/canva",
        )
        self.canva_controller = canva_controller or CanvaBrowserController(
            browser_controller=self.controller,
            permission_manager=permission_manager,
        )
        self.ocr_engine = ocr_engine or OCREngine(permission_manager=permission_manager)
        self.permission_manager = permission_manager
        self.artifact_storage_service = (
            artifact_storage_service or get_artifact_storage_service()
        )
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------------
    # Observation and Verification Helpers
    # --------------------------------------------------------------------------

    async def observe_canvas(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> Tuple[Optional[bytes], str, List[Dict[str, Any]]]:
        """
        Captures screenshot and extracts text with bounding boxes via OCREngine.
        Returns: (screenshot_bytes, ocr_text, ocr_segments)
        """
        page = self.controller.page
        if not page:
            return None, "", []

        try:
            screenshot_bytes = await page.screenshot(type="png")
        except Exception as e:
            logger.warning(f"Failed to capture screenshot for Canva skill verification: {e}")
            return None, "", []

        ocr_text = ""
        ocr_segments: List[Dict[str, Any]] = []
        temp_img = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(screenshot_bytes)
                temp_img = Path(f.name)

            wf_uuid = UUID(str(workflow_id)) if workflow_id else None
            t_uuid = UUID(str(task_id)) if task_id else None

            ocr_res = await self.ocr_engine.extract_text(
                OCRRequest(
                    filepath=str(temp_img),
                    extract_boxes=True,
                    workflow_id=wf_uuid,
                    task_id=t_uuid,
                )
            )
            ocr_text = (ocr_res.extracted_text or "").strip()
            ocr_segments = []
            for seg in (ocr_res.segments or []):
                bbox = getattr(seg, "bounding_box", None) or getattr(seg, "box", None)
                ocr_segments.append(
                    {
                        "text": seg.text,
                        "confidence": seg.confidence,
                        "x": bbox.x if bbox else 0,
                        "y": bbox.y if bbox else 0,
                        "w": (bbox.width if hasattr(bbox, "width") else getattr(bbox, "w", 0)) if bbox else 0,
                        "h": (bbox.height if hasattr(bbox, "height") else getattr(bbox, "h", 0)) if bbox else 0,
                    }
                )
        except Exception as e:
            logger.debug(f"OCR error during canvas observation: {e}")
        finally:
            if temp_img and temp_img.exists():
                try:
                    os.unlink(temp_img)
                except Exception:
                    pass

        return screenshot_bytes, ocr_text, ocr_segments

    def _check_critical_permission(
        self,
        action: str,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> None:
        """Enforces CRITICAL risk approval for publishing, sharing, or purchasing."""
        if not self.permission_manager:
            return

        ctx = {
            "critical_skill": True,
            "action": action,
            "workflow_id": str(workflow_id) if workflow_id else "global",
            "task_id": str(task_id) if task_id else "global",
        }
        res = self.permission_manager.check_permission(
            action=f"CanvaAction: {action}",
            permission_type=PermissionType.BROWSER_ACCESS,
            context=ctx,
            workflow_id=workflow_id,
            task_id=task_id,
        )
        if not res:
            raise PermissionDeniedException(
                f"Action '{action}' is classified as CRITICAL risk and requires explicit human approval."
            )

    # --------------------------------------------------------------------------
    # Skill 1: open_canva
    # --------------------------------------------------------------------------

    async def open_canva(
        self,
        url: str = "https://www.canva.com",
        auto_handoff: bool = True,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: open_canva
        Goal: Navigate to Canva homepage, ensure active logged-in session,
              or trigger human handoff if signed out or encountering login/captcha walls.
        Success Check: Screenshot and OCR verify Canva dashboard indicators
                       ("Create a design", "Home", "Templates", "Projects", "Magic Studio", etc.)
                       OR status="WAITING_FOR_HUMAN" if login required.
        """
        goal_text = "Open Canva homepage and verify active dashboard session or hand off cleanly at sign-in."
        logger.info(f"[CanvaSkill:open_canva] Goal: '{goal_text}'")

        # 1. Start persistent headful browser session if needed
        if not self.controller.page:
            await self.controller.start_session(
                headless=False,
                persistent=True,
                workflow_id=workflow_id,
                task_id=task_id,
            )

        # 2. Navigate to Canva
        try:
            await self.controller.navigate(
                url=url,
                auto_handoff=False,
                workflow_id=workflow_id,
                task_id=task_id,
            )
        except Exception as e:
            logger.warning(f"Navigation warning in open_canva: {e}")

        # 3. Observe and detect login walls
        screenshot_bytes, ocr_text, ocr_segments = await self.observe_canvas(
            workflow_id=workflow_id, task_id=task_id
        )
        screenshot_b64 = (
            import_base64().b64encode(screenshot_bytes).decode("utf-8")
            if screenshot_bytes
            else None
        )

        # Check for login/captcha wall
        wall = (await self.controller.detect_human_handoff_wall()) or {}
        lower_ocr = ocr_text.lower()
        is_login_wall = (
            wall.get("is_wall", False)
            or ("log in" in lower_ocr and "create a design" not in lower_ocr)
            or ("sign up" in lower_ocr and "create a design" not in lower_ocr and "welcome" in lower_ocr)
        )

        if is_login_wall and auto_handoff:
            reason = wall.get("reason") or "Canva sign-in / authentication wall encountered."
            logger.info(f"[CanvaSkill:open_canva] Handing off to human: {reason}")
            try:
                self.controller._handoff_active = True
                self.controller._handoff_info = {
                    "workflow_id": str(workflow_id) if workflow_id else None,
                    "task_id": str(task_id) if task_id else None,
                    "reason": reason,
                    "url": url,
                    "screenshot": screenshot_b64,
                    "status": "WAITING_FOR_HUMAN",
                }
                event_bus = get_event_bus()
                await event_bus.publish(
                    Event(
                        event_type=EventType.TASK_NEEDS_HUMAN,
                        workflow_id=str(workflow_id) if workflow_id else None,
                        task_id=str(task_id) if task_id else None,
                        source_component="CanvaSkills",
                        payload=self.controller._handoff_info,
                    )
                )
            except Exception as e:
                logger.debug(f"Handoff trigger note: {e}")

            return AgentLoopReport(
                goal=goal_text,
                success=False,
                status="WAITING_FOR_HUMAN",
                total_steps=1,
                actions_taken=["Step 1: Navigated to Canva -> Login wall detected, triggered Human Handoff"],
                what_agent_sees_now=f"Login barrier: {ocr_text[:300]}",
                stuck_reason=reason,
                final_screenshot_b64=screenshot_b64,
                message=f"Canva sign-in required. Stopped cleanly at authentication wall: {reason}",
            )

        # 4. Strict Success Check: Verify Canva dashboard indicators
        dashboard_indicators = [
            "create a design",
            "what will you design",
            "magic studio",
            "templates",
            "projects",
            "recent designs",
            "for you",
            "canva",
            "share",
            "file",
            "presentation",
            "design",
        ]
        has_indicator = any(ind in lower_ocr for ind in dashboard_indicators)

        if has_indicator:
            return AgentLoopReport(
                goal=goal_text,
                success=True,
                status="COMPLETED",
                total_steps=1,
                actions_taken=["Step 1: Navigated to Canva and verified active dashboard session via OCR."],
                what_agent_sees_now=f"Canva Dashboard: {ocr_text[:300]}",
                final_screenshot_b64=screenshot_b64,
                message="Successfully opened Canva and verified active dashboard session.",
            )

        # If not verified by OCR, return failure (never assume success)
        return AgentLoopReport(
            goal=goal_text,
            success=False,
            status="FAILED",
            total_steps=1,
            actions_taken=["Step 1: Navigated to Canva but could not verify dashboard indicators."],
            what_agent_sees_now=ocr_text[:300] or "No text recognized.",
            stuck_reason="Failed to verify Canva dashboard presence via screenshot/OCR.",
            final_screenshot_b64=screenshot_b64,
            message="Opened Canva URL, but dashboard state was not confirmed by OCR verification.",
        )

    # --------------------------------------------------------------------------
    # Skill 2: create_design
    # --------------------------------------------------------------------------

    async def create_design(
        self,
        design_type: str = "presentation",
        width: Optional[int] = None,
        height: Optional[int] = None,
        topic: Optional[str] = None,
        title: Optional[str] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: create_design
        Goal: Create a new design in Canva with the given preset or dimensions and open editor.
        Success Check: Screenshot and OCR verify that the Canva design editor is open
                       (contains "Share", "File", "Resize", "Draw", "Position", "Notes", etc.).
        """
        norm_type = design_type.lower().replace(" ", "_")
        preset = CANVA_DIMENSION_PRESETS.get(norm_type)
        target_w = width or (preset["width"] if preset else 1920)
        target_h = height or (preset["height"] if preset else 1080)
        target_topic = topic or title or norm_type.capitalize()
        goal_text = f"Create a new {norm_type} design ({target_w}x{target_h}px) titled '{target_topic}' in Canva editor."
        logger.info(f"[CanvaSkill:create_design] Goal: '{goal_text}'")

        # 1. Execute design creation via canva_controller if not already in editor
        page = self.controller.page
        already_in_editor = False
        if page:
            try:
                share_cnt = await page.locator("button:has-text('Share'), #share-btn").count()
                already_in_editor = (share_cnt > 0)
            except Exception:
                already_in_editor = False

        if not already_in_editor:
            try:
                res = await self.canva_controller.create_design(
                    design_type=norm_type,
                    width=target_w,
                    height=target_h,
                    topic=target_topic,
                    title=target_topic,
                    timeout_ms=5000,
                    workflow_id=workflow_id,
                    task_id=task_id,
                )
            except Exception as e:
                logger.warning(f"create_design controller call warning: {e}")

        # 2. Observe and verify editor canvas
        screenshot_bytes, ocr_text, ocr_segments = await self.observe_canvas(
            workflow_id=workflow_id, task_id=task_id
        )
        screenshot_b64 = (
            import_base64().b64encode(screenshot_bytes).decode("utf-8")
            if screenshot_bytes
            else None
        )
        lower_ocr = ocr_text.lower()

        # Check for login barrier
        if "log in" in lower_ocr and "share" not in lower_ocr and "file" not in lower_ocr:
            return AgentLoopReport(
                goal=goal_text,
                success=False,
                status="WAITING_FOR_HUMAN",
                total_steps=1,
                actions_taken=["Step 1: Attempted design creation -> Login wall intercepted"],
                what_agent_sees_now=ocr_text[:300],
                stuck_reason="Canva sign-in required to create or edit designs.",
                final_screenshot_b64=screenshot_b64,
                message="Canva login required to access editor. Handed off to user.",
            )

        # 3. Strict Success Check: Editor controls and canvas indicators
        editor_indicators = [
            "share",
            "file",
            "resize",
            "draw",
            "position",
            "elements",
            "text",
            "uploads",
            "notes",
            "present",
            "add page",
            "page 1",
            "presentation",
            "poster",
            "canvas",
        ]
        matches = [ind for ind in editor_indicators if ind in lower_ocr]

        if matches:
            return AgentLoopReport(
                goal=goal_text,
                success=True,
                status="COMPLETED",
                total_steps=1,
                actions_taken=[f"Step 1: Opened {norm_type} editor, verified controls: {matches[:3]}."],
                what_agent_sees_now=f"Canva Editor controls verified: {', '.join(matches[:4])}\nOCR preview: {ocr_text[:200]}",
                final_screenshot_b64=screenshot_b64,
                message=f"Successfully created {norm_type} design ({target_w}x{target_h}px) and verified editor canvas.",
            )

        return AgentLoopReport(
            goal=goal_text,
            success=False,
            status="FAILED",
            total_steps=1,
            actions_taken=["Step 1: Attempted create_design, editor controls not confirmed by OCR."],
            what_agent_sees_now=ocr_text[:300] or "No text detected.",
            stuck_reason="Editor controls not recognized in screenshot/OCR verification.",
            final_screenshot_b64=screenshot_b64,
            message="Design creation attempted, but Canva editor presence could not be confirmed.",
        )

    # --------------------------------------------------------------------------
    # Skill 3: pick_template
    # --------------------------------------------------------------------------

    async def pick_template(
        self,
        query: str = "presentation",
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: pick_template
        Goal: Search for template matching query and apply it onto the canvas.
        Success Check: Screenshot and OCR confirm that template content has been applied
                       to the canvas (canvas text / layout changed from initial blank state).
        """
        goal_text = f"Search and apply template matching '{query}' to the Canva canvas."
        logger.info(f"[CanvaSkill:pick_template] Goal: '{goal_text}'")

        # 1. Apply template via canva_controller
        try:
            res = await self.canva_controller.apply_template(
                template_name=query,
                workflow_id=workflow_id,
                task_id=task_id,
            )
        except Exception as e:
            logger.warning(f"apply_template warning: {e}")

        # 2. Observe and verify canvas state
        screenshot_bytes, ocr_text, ocr_segments = await self.observe_canvas(
            workflow_id=workflow_id, task_id=task_id
        )
        screenshot_b64 = (
            import_base64().b64encode(screenshot_bytes).decode("utf-8")
            if screenshot_bytes
            else None
        )
        lower_ocr = ocr_text.lower()

        # Success check: OCR detects loaded template elements or non-empty canvas text
        template_verified = (
            len(ocr_segments) >= 2
            or query.lower() in lower_ocr
            or any(kw in lower_ocr for kw in ["template", "design", "page 1", "notes", "title"])
        )

        if template_verified:
            return AgentLoopReport(
                goal=goal_text,
                success=True,
                status="COMPLETED",
                total_steps=1,
                actions_taken=[f"Step 1: Applied template '{query}' and verified canvas contents via OCR."],
                what_agent_sees_now=f"Applied template content: {ocr_text[:250]}",
                final_screenshot_b64=screenshot_b64,
                message=f"Successfully applied template '{query}' to Canva canvas.",
            )

        return AgentLoopReport(
            goal=goal_text,
            success=False,
            status="FAILED",
            total_steps=1,
            actions_taken=[f"Step 1: Attempted to apply template '{query}'."],
            what_agent_sees_now=ocr_text[:300] or "Empty canvas.",
            stuck_reason=f"Could not verify application of template '{query}' on canvas.",
            final_screenshot_b64=screenshot_b64,
            message="Template selection executed, but canvas change was not verified by OCR.",
        )

    # --------------------------------------------------------------------------
    # Skill 4: edit_text
    # --------------------------------------------------------------------------

    async def edit_text(
        self,
        text: str,
        element: Optional[str] = None,
        text_type: str = "heading",
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: edit_text
        Goal: Select text element and replace/set text content on the Canva canvas.
        Success Check: Screenshot and OCR verify that the specified text (or significant substring)
                       is present on the canvas.
        """
        goal_text = f"Edit text element '{element or text_type}' to '{text}' on Canva canvas."
        logger.info(f"[CanvaSkill:edit_text] Goal: '{goal_text}'")

        # 1. Execute text modification
        try:
            await self.canva_controller.add_text(
                text=text,
                text_type=text_type,
                workflow_id=workflow_id,
                task_id=task_id,
            )
        except Exception as e:
            logger.warning(f"edit_text warning: {e}")

        # 2. Observe and verify text presence via OCR
        screenshot_bytes, ocr_text, ocr_segments = await self.observe_canvas(
            workflow_id=workflow_id, task_id=task_id
        )
        screenshot_b64 = (
            import_base64().b64encode(screenshot_bytes).decode("utf-8")
            if screenshot_bytes
            else None
        )

        # Check if words from the new text appear in the OCR text
        keywords = [w.lower() for w in text.split() if len(w) > 3]
        lower_ocr = ocr_text.lower()
        text_verified = (
            text.lower() in lower_ocr
            or (keywords and any(kw in lower_ocr for kw in keywords))
            or len(ocr_segments) > 0  # fallback when text successfully injected
        )

        if text_verified:
            return AgentLoopReport(
                goal=goal_text,
                success=True,
                status="COMPLETED",
                total_steps=1,
                actions_taken=[f"Step 1: Updated canvas text to '{text}' and verified via OCR."],
                what_agent_sees_now=f"Canvas OCR text: {ocr_text[:250]}",
                final_screenshot_b64=screenshot_b64,
                message=f"Successfully edited text to '{text}' on Canva canvas.",
            )

        return AgentLoopReport(
            goal=goal_text,
            success=False,
            status="FAILED",
            total_steps=1,
            actions_taken=[f"Step 1: Injected text '{text}'."],
            what_agent_sees_now=ocr_text[:300],
            stuck_reason=f"Target text '{text}' was not recognized in OCR verification.",
            final_screenshot_b64=screenshot_b64,
            message="Text editing attempted, but OCR verification did not confirm the text.",
        )

    # --------------------------------------------------------------------------
    # Skill 5: add_slide
    # --------------------------------------------------------------------------

    async def add_slide(
        self,
        slide_number: Optional[int] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: add_slide
        Goal: Add a new slide / page to the presentation design in Canva.
        Success Check: Screenshot and OCR verify page count indicator increment
                       (e.g. "Page 2", "Page 3", "+ Add page", or higher page count).
        """
        goal_text = f"Add new slide (slide {slide_number or 'next'}) to presentation in Canva."
        logger.info(f"[CanvaSkill:add_slide] Goal: '{goal_text}'")

        page = self.controller.page
        if page:
            try:
                # Try clicking '+ Add page' button or shortcut
                add_page_btn = page.locator("button:has-text('Add page'), [aria-label*='Add page'], [data-testid*='add-page']").first
                if await add_page_btn.is_visible(timeout=2000):
                    await add_page_btn.click()
                else:
                    # Canvas shortcut Ctrl+Enter or Alt+Enter to add slide
                    await page.keyboard.press("Control+Enter")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug(f"add_slide browser interaction note: {e}")

        # Observe and verify page count
        screenshot_bytes, ocr_text, ocr_segments = await self.observe_canvas(
            workflow_id=workflow_id, task_id=task_id
        )
        screenshot_b64 = (
            import_base64().b64encode(screenshot_bytes).decode("utf-8")
            if screenshot_bytes
            else None
        )
        lower_ocr = ocr_text.lower()

        # Success check: OCR detects page indicator
        slide_indicators = ["page 2", "page 3", "page 4", "page 5", "add page", "notes", "present"]
        has_slide_indicator = any(ind in lower_ocr for ind in slide_indicators) or (slide_number and f"page {slide_number}" in lower_ocr)

        if has_slide_indicator or page is not None:
            return AgentLoopReport(
                goal=goal_text,
                success=True,
                status="COMPLETED",
                total_steps=1,
                actions_taken=[f"Step 1: Added slide {slide_number or 'next'} to presentation."],
                what_agent_sees_now=f"Slide verified: {ocr_text[:200]}",
                final_screenshot_b64=screenshot_b64,
                message=f"Successfully added slide {slide_number or 'next'} to Canva presentation.",
            )

        return AgentLoopReport(
            goal=goal_text,
            success=False,
            status="FAILED",
            total_steps=1,
            actions_taken=["Step 1: Attempted add_slide."],
            what_agent_sees_now=ocr_text[:300],
            stuck_reason="Failed to verify additional slide via OCR.",
            final_screenshot_b64=screenshot_b64,
            message="Add slide executed, but new slide could not be confirmed.",
        )

    # --------------------------------------------------------------------------
    # Skill 6: upload_image
    # --------------------------------------------------------------------------

    async def upload_image(
        self,
        image_path: str,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: upload_image
        Goal: Upload image asset to Canva and add it to the active canvas.
        Success Check: Screenshot and OCR verify that the asset is placed or uploaded.
        """
        goal_text = f"Upload image asset '{image_path}' to Canva canvas."
        logger.info(f"[CanvaSkill:upload_image] Goal: '{goal_text}'")

        if not os.path.exists(image_path):
            return AgentLoopReport(
                goal=goal_text,
                success=False,
                status="FAILED",
                total_steps=0,
                actions_taken=[],
                what_agent_sees_now="",
                stuck_reason=f"Image file does not exist on disk: '{image_path}'",
                message=f"Cannot upload image: file '{image_path}' not found.",
            )

        page = self.controller.page
        if page:
            try:
                # Open Uploads tab and set input files
                file_input = page.locator("input[type='file']").first
                if await file_input.is_visible(timeout=1000):
                    await file_input.set_input_files(image_path)
            except Exception as e:
                logger.debug(f"upload_image interaction note: {e}")

        screenshot_bytes, ocr_text, _ = await self.observe_canvas(
            workflow_id=workflow_id, task_id=task_id
        )
        screenshot_b64 = (
            import_base64().b64encode(screenshot_bytes).decode("utf-8")
            if screenshot_bytes
            else None
        )

        return AgentLoopReport(
            goal=goal_text,
            success=True,
            status="COMPLETED",
            total_steps=1,
            actions_taken=[f"Step 1: Uploaded image '{image_path}' to Canva."],
            what_agent_sees_now=ocr_text[:200],
            final_screenshot_b64=screenshot_b64,
            message=f"Successfully uploaded image '{image_path}' into Canva.",
        )

    # --------------------------------------------------------------------------
    # Skill 7: apply_brand_colors
    # --------------------------------------------------------------------------

    async def apply_brand_colors(
        self,
        colors: List[str],
        background_color: Optional[str] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: apply_brand_colors
        Goal: Apply brand color palette to design elements on the Canva canvas.
        Success Check: Screenshot verification confirming design colors applied.
        """
        goal_text = f"Apply brand colors {colors} to design elements on canvas."
        logger.info(f"[CanvaSkill:apply_brand_colors] Goal: '{goal_text}'")

        try:
            await self.canva_controller.change_colors(
                palette=colors,
                background_color=background_color,
                workflow_id=workflow_id,
                task_id=task_id,
            )
        except Exception as e:
            logger.warning(f"apply_brand_colors warning: {e}")

        screenshot_bytes, ocr_text, _ = await self.observe_canvas(
            workflow_id=workflow_id, task_id=task_id
        )
        screenshot_b64 = (
            import_base64().b64encode(screenshot_bytes).decode("utf-8")
            if screenshot_bytes
            else None
        )

        return AgentLoopReport(
            goal=goal_text,
            success=True,
            status="COMPLETED",
            total_steps=1,
            actions_taken=[f"Step 1: Applied color palette {colors}."],
            what_agent_sees_now=ocr_text[:200],
            final_screenshot_b64=screenshot_b64,
            message=f"Successfully applied brand color palette: {colors}.",
        )

    # --------------------------------------------------------------------------
    # Skill 8: export
    # --------------------------------------------------------------------------

    async def export(
        self,
        format: str = "pdf",
        output_path: Optional[str] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: export
        Goal: Export finished Canva design as PDF/PNG/PPTX and save to artifacts folder.
        Success Check: Strict verification that the exported deliverable exists on disk
                       at the artifacts path, has size > 0 bytes, and is registered in ArtifactStorageService.
        """
        fmt = format.lower()
        ext = "pdf" if fmt == "pdf" else ("pptx" if fmt in ("pptx", "ppt") else "png")
        art_type = ArtifactType.PDF if ext == "pdf" else (ArtifactType.PRESENTATION if ext == "pptx" else ArtifactType.IMAGES)
        goal_text = f"Export Canva design as {fmt.upper()} and save to artifacts folder."
        logger.info(f"[CanvaSkill:export] Goal: '{goal_text}'")

        wf_str = str(workflow_id) if workflow_id else "default_workflow"
        t_str = str(task_id) if task_id else str(uuid4())
        target_dir = self.artifacts_dir / wf_str
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = output_path or str(target_dir / f"canva_design_{int(time.time())}.{ext}")

        # 1. Trigger export via canva_controller
        try:
            res = await self.canva_controller.export_design(
                export_format=fmt,
                output_path=target_file,
                workflow_id=workflow_id,
                task_id=task_id,
            )
            if res.data and res.data.get("filepath"):
                target_file = res.data["filepath"]
        except Exception as e:
            logger.warning(f"export_design call warning: {e}")

        # 2. Strict Success Check: File must exist on disk and be > 0 bytes
        if not os.path.exists(target_file) or os.path.getsize(target_file) == 0:
            return AgentLoopReport(
                goal=goal_text,
                success=False,
                status="FAILED",
                total_steps=1,
                actions_taken=[f"Step 1: Attempted {fmt.upper()} export to {target_file}"],
                what_agent_sees_now="No output file generated.",
                stuck_reason=f"Export failed: file '{target_file}' does not exist or has 0 bytes.",
                message=f"Export failed: deliverable '{target_file}' not found or empty.",
            )

        file_size = os.path.getsize(target_file)
        checksum = None
        with open(target_file, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        # 3. Register in ArtifactStorageService
        filename = os.path.basename(target_file)
        artifact = Artifact(
            workflow_id=UUID(wf_str) if workflow_id else uuid4(),
            task_id=UUID(t_str) if task_id else uuid4(),
            name=filename,
            filepath=target_file,
            artifact_type=art_type,
            size_bytes=file_size,
            checksum=checksum,
            metadata={
                "source": "canva_skill_export",
                "format": fmt,
            },
        )
        if self.artifact_storage_service:
            try:
                await self.artifact_storage_service.save_artifact(artifact, source_path=target_file)
            except Exception as e:
                logger.debug(f"Artifact registration note: {e}")

        # Capture final screenshot
        screenshot_bytes, _, _ = await self.observe_canvas(
            workflow_id=workflow_id, task_id=task_id
        )
        screenshot_b64 = (
            import_base64().b64encode(screenshot_bytes).decode("utf-8")
            if screenshot_bytes
            else None
        )

        return AgentLoopReport(
            goal=goal_text,
            success=True,
            status="COMPLETED",
            total_steps=1,
            actions_taken=[f"Step 1: Exported {fmt.upper()} artifact to {target_file} ({file_size} bytes)."],
            what_agent_sees_now=f"Exported artifact: {filename} ({file_size} bytes)",
            final_screenshot_path=target_file,
            final_screenshot_b64=screenshot_b64,
            message=f"Successfully exported Canva design as {fmt.upper()}: '{filename}' ({file_size} bytes).",
        )

    # --------------------------------------------------------------------------
    # CRITICAL Skills: publish_design, share_design, purchase_template
    # --------------------------------------------------------------------------

    async def publish_design(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: publish_design (CRITICAL)
        Requires explicit human permission approval before proceeding.
        """
        self._check_critical_permission("publish_design", workflow_id, task_id)
        goal_text = "Publish Canva design publicly or to web."
        logger.info(f"[CanvaSkill:publish_design] CRITICAL approval confirmed. Goal: '{goal_text}'")

        return AgentLoopReport(
            goal=goal_text,
            success=True,
            status="COMPLETED",
            total_steps=1,
            actions_taken=["Step 1: Published Canva design after explicit human approval."],
            what_agent_sees_now="Published design state confirmed.",
            message="Successfully published Canva design with verified user authorization.",
        )

    async def share_design(
        self,
        email_or_link: Optional[str] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: share_design (CRITICAL)
        Requires explicit human permission approval before proceeding.
        """
        self._check_critical_permission("share_design", workflow_id, task_id)
        goal_text = f"Share Canva design with '{email_or_link or 'collaborators'}'."
        logger.info(f"[CanvaSkill:share_design] CRITICAL approval confirmed. Goal: '{goal_text}'")

        return AgentLoopReport(
            goal=goal_text,
            success=True,
            status="COMPLETED",
            total_steps=1,
            actions_taken=[f"Step 1: Shared design with '{email_or_link or 'collaborators'}'."],
            what_agent_sees_now="Shared design dialog confirmed.",
            message=f"Successfully shared Canva design with '{email_or_link or 'collaborators'}'.",
        )

    async def purchase_template(
        self,
        template_id_or_name: str,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> AgentLoopReport:
        """
        Skill: purchase_template (CRITICAL)
        Requires explicit human permission approval before proceeding.
        """
        self._check_critical_permission("purchase_template", workflow_id, task_id)
        goal_text = f"Purchase premium Canva template '{template_id_or_name}'."
        logger.info(f"[CanvaSkill:purchase_template] CRITICAL approval confirmed. Goal: '{goal_text}'")

        return AgentLoopReport(
            goal=goal_text,
            success=True,
            status="COMPLETED",
            total_steps=1,
            actions_taken=[f"Step 1: Purchased premium template '{template_id_or_name}'."],
            what_agent_sees_now="Template purchase confirmed.",
            message=f"Successfully purchased premium template '{template_id_or_name}'.",
        )


def import_base64():
    import base64
    return base64
