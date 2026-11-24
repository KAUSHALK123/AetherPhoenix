import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pptx
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)

from app.core.exceptions import (
    InputValidationException,
    PermissionDeniedException,
    ToolExecutionException,
)
from app.core.logging import get_logger
from app.core.permissions.manager import PermissionManager
from app.schemas.ppt import (
    PPTGenerationResult,
    PresentationSchema,
    SlideContent,
    SlideType,
)
from app.tools.ppt.xml_sanitizer import sanitize_xml_text, validate_openxml_package

logger = get_logger(__name__)


class PPTGenerator:
    """
    Worker Agent tool for compiling structured presentation data
    into an uncorrupted, fully-validated PowerPoint (.pptx) file.
    Includes XML 1.0 sanitization, OpenXML package verification, and permission checks.
    """

    def __init__(self, permission_manager: Optional[PermissionManager] = None) -> None:
        self.permission_manager = permission_manager or PermissionManager()

    def generate(
        self,
        presentation: PresentationSchema,
        output_path: str,
        workflow_id: Optional[UUID] = None,
    ) -> PPTGenerationResult:
        """
        Generates a PowerPoint presentation at the specified output path.

        Parameters
        ----------
        presentation:
            The structured content and slide data.
        output_path:
            Target file path on the filesystem.
        workflow_id:
            The unique identifier of the active workflow (for permissions).

        Returns
        -------
        PPTGenerationResult:
            Metadata about the generated PowerPoint file.
        """
        if workflow_id is None:
            workflow_id = uuid4()
        logger.info(
            f"Initiating PPT generation: Workflow={workflow_id}, Output={output_path}, "
            f"Slides={len(presentation.slides)}"
        )

        if not presentation or not presentation.slides:
            raise InputValidationException(
                message="Cannot generate PowerPoint presentation: No slides provided.",
                details={"output_path": output_path},
            )

        # 1. Permission Check
        perm_req = PermissionRequest(
            workflow_id=workflow_id,
            permission_type=PermissionType.FILE_SYSTEM,
            reason="Generate PowerPoint presentation file",
            risk_level=RiskLevel.SAFE,
        )
        granted_req = self.permission_manager.request_permission(perm_req)

        if granted_req.status != PermissionStatus.GRANTED:
            logger.error("FILE_SYSTEM write permission rejected.")
            raise PermissionDeniedException(
                message="Cannot write PowerPoint file: FILE_SYSTEM permission denied.",
                details={"permission_type": PermissionType.FILE_SYSTEM},
            )

        # 2. PowerPoint Generation
        try:
            prs = pptx.Presentation()

            # Set slide width and height to 16:9 widescreen layout (960pt x 540pt)
            prs.slide_width = Pt(960)  # 13.33 inches
            prs.slide_height = Pt(540)  # 7.5 inches

            # Iterate over each slide structure
            for idx, slide_data in enumerate(presentation.slides):
                logger.debug(
                    f"Compiling slide {idx + 1}/{len(presentation.slides)}: "
                    f"Title='{slide_data.title}' (Type={slide_data.slide_type.value})"
                )

                if slide_data.slide_type == SlideType.TITLE or (
                    idx == 0
                    and slide_data.slide_type
                    not in (SlideType.IMAGE, SlideType.CHART, SlideType.TABLE)
                ):
                    # Layout 0: default Title Slide layout
                    slide = prs.slides.add_slide(prs.slide_layouts[0])
                    self._populate_title_slide(slide, slide_data)
                else:
                    # Layout 1: default Title and Content layout
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    self._populate_content_slide(slide, slide_data)

                # Append speaker notes if provided (sanitizing text to avoid XML corruption)
                notes_text = sanitize_xml_text(slide_data.speaker_notes)
                if notes_text:
                    notes_slide = slide.notes_slide
                    notes_slide.notes_text_frame.text = notes_text

            # Ensure directory exists before saving
            dir_name = os.path.dirname(output_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)

            # Atomic save: write and flush
            prs.save(output_path)
            logger.info(f"Presentation saved successfully to {output_path}")

        except Exception as e:
            logger.exception("Failed to compile PowerPoint deck.")
            raise ToolExecutionException(
                message=f"PowerPoint generation failed: {str(e)}",
                details={"output_path": output_path},
            ) from e

        # 3. OpenXML Package Structure & File Validation
        self._validate_output_file(output_path, len(presentation.slides))

        # 4. Generate Metadata
        file_size = os.path.getsize(output_path)
        return PPTGenerationResult(
            file_path=os.path.abspath(output_path),
            file_size=file_size,
            slide_count=len(presentation.slides),
            generated_at=datetime.now(timezone.utc),
        )

    def _populate_title_slide(self, slide, slide_data: SlideContent) -> None:
        """Sets sanitized text and styles for a title slide layout."""
        title_shape = getattr(slide.shapes, "title", None)
        subtitle_shape = (
            slide.placeholders[1]
            if len(slide.placeholders) > 1 and slide.placeholders[1] != title_shape
            else None
        )

        clean_title = sanitize_xml_text(slide_data.title)
        clean_sub = sanitize_xml_text(slide_data.subtitle)

        if title_shape and title_shape.has_text_frame:
            title_shape.text = clean_title
            self._apply_text_formatting(
                title_shape, font_size=Pt(44), bold=True, color=RGBColor(15, 23, 42)
            )
        else:
            # Fallback textbox if layout placeholder is absent
            tb = slide.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.33), Inches(1.5))
            tb.text_frame.text = clean_title
            self._apply_text_formatting(
                tb, font_size=Pt(44), bold=True, color=RGBColor(15, 23, 42)
            )

        if clean_sub:
            if subtitle_shape and subtitle_shape.has_text_frame:
                subtitle_shape.text = clean_sub
                self._apply_text_formatting(
                    subtitle_shape,
                    font_size=Pt(22),
                    bold=False,
                    color=RGBColor(71, 85, 105),
                )
            else:
                tb_sub = slide.shapes.add_textbox(Inches(1.0), Inches(3.8), Inches(11.33), Inches(1.0))
                tb_sub.text_frame.text = clean_sub
                self._apply_text_formatting(
                    tb_sub,
                    font_size=Pt(22),
                    bold=False,
                    color=RGBColor(71, 85, 105),
                )

        if slide_data.image_path and os.path.exists(slide_data.image_path):
            self._embed_image(slide, slide_data.image_path)

    def _populate_content_slide(self, slide, slide_data: SlideContent) -> None:
        """Sets text, bullet points, images, and tables for content slide layout."""
        title_shape = getattr(slide.shapes, "title", None)
        clean_title = sanitize_xml_text(slide_data.title)

        if title_shape and title_shape.has_text_frame:
            title_shape.text = clean_title
            self._apply_text_formatting(
                title_shape, font_size=Pt(32), bold=True, color=RGBColor(15, 23, 42)
            )
        else:
            tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.5), Inches(1.0))
            tb.text_frame.text = clean_title
            self._apply_text_formatting(
                tb, font_size=Pt(32), bold=True, color=RGBColor(15, 23, 42)
            )

        content_shape = (
            slide.placeholders[1]
            if len(slide.placeholders) > 1 and slide.placeholders[1] != title_shape
            else None
        )

        bullets = [sanitize_xml_text(b).strip() for b in slide_data.bullets if sanitize_xml_text(b).strip()]

        # Has embedded image
        has_image = bool(
            slide_data.image_path
            and os.path.exists(slide_data.image_path)
            and os.path.getsize(slide_data.image_path) > 0
        )

        if content_shape and content_shape.has_text_frame:
            tf = content_shape.text_frame
            tf.word_wrap = True

            # If image is present, resize content shape to left half
            if has_image:
                content_shape.left = Inches(0.8)
                content_shape.top = Inches(1.6)
                content_shape.width = Inches(6.5)
                content_shape.height = Inches(5.0)

            if bullets:
                first_p = tf.paragraphs[0]
                first_p.text = bullets[0]
                self._apply_paragraph_formatting(first_p, font_size=Pt(17))

                for bullet in bullets[1:]:
                    p = tf.add_paragraph()
                    p.text = bullet
                    self._apply_paragraph_formatting(p, font_size=Pt(17))
        elif bullets:
            # Fallback text frame if layout placeholder not present
            left_pos = Inches(0.8)
            width_pos = Inches(6.5) if has_image else Inches(11.5)
            tb_content = slide.shapes.add_textbox(left_pos, Inches(1.6), width_pos, Inches(5.0))
            tf = tb_content.text_frame
            tf.word_wrap = True
            first_p = tf.paragraphs[0]
            first_p.text = bullets[0]
            self._apply_paragraph_formatting(first_p, font_size=Pt(17))
            for bullet in bullets[1:]:
                p = tf.add_paragraph()
                p.text = bullet
                self._apply_paragraph_formatting(p, font_size=Pt(17))

        # Embed Image if present and verified
        if has_image:
            self._embed_image(slide, slide_data.image_path)

        # Embed Table if present
        if slide_data.table_data and isinstance(slide_data.table_data, dict):
            self._embed_table(slide, slide_data.table_data)

    def _embed_image(self, slide, image_path: str) -> None:
        """Safely embeds an image into the right column of a slide."""
        try:
            img_left = Inches(7.8)
            img_top = Inches(1.8)
            img_width = Inches(4.8)
            img_height = Inches(4.5)

            slide.shapes.add_picture(
                image_path,
                img_left,
                img_top,
                width=img_width,
                height=img_height,
            )
            logger.debug(f"Successfully embedded image '{image_path}' in slide.")
        except Exception as img_err:
            logger.warning(f"Failed to embed image '{image_path}': {img_err}")

    def _embed_table(self, slide, table_data: dict) -> None:
        """Safely embeds a structured table into the slide."""
        try:
            headers = [sanitize_xml_text(h) for h in table_data.get("headers", [])]
            rows = [
                [sanitize_xml_text(c) for c in row]
                for row in table_data.get("rows", [])
            ]
            if not headers and not rows:
                return

            all_rows = ([headers] if headers else []) + rows
            num_rows = len(all_rows)
            num_cols = len(all_rows[0]) if num_rows > 0 else 0

            if num_rows == 0 or num_cols == 0:
                return

            table_shape = slide.shapes.add_table(
                num_rows, num_cols, Inches(0.8), Inches(4.2), Inches(11.5), Inches(2.2)
            )
            tbl = table_shape.table

            for r_idx, row in enumerate(all_rows):
                for c_idx, cell_value in enumerate(row):
                    if c_idx < num_cols:
                        cell = tbl.cell(r_idx, c_idx)
                        cell.text = cell_value
                        for p in cell.text_frame.paragraphs:
                            p.font.size = Pt(13)
                            if r_idx == 0 and headers:
                                p.font.bold = True
                                p.font.color.rgb = RGBColor(30, 41, 59)
        except Exception as tbl_err:
            logger.warning(f"Failed to embed table in slide: {tbl_err}")

    def _apply_text_formatting(
        self, shape, font_size, bold=False, color=None
    ) -> None:
        """Applies consistent typography to all paragraphs of a shape's text frame."""
        if not shape.has_text_frame:
            return
        tf = shape.text_frame
        for p in tf.paragraphs:
            self._apply_paragraph_formatting(p, font_size, bold, color)

    def _apply_paragraph_formatting(
        self, paragraph, font_size, bold=False, color=None
    ) -> None:
        """Helper to style runs within a single paragraph."""
        paragraph.font.name = "Arial"
        paragraph.font.size = font_size
        paragraph.font.bold = bold
        if color:
            paragraph.font.color.rgb = color

    def _validate_output_file(self, file_path: str, expected_slides: int) -> None:
        """
        Validates that the output file exists, is non-empty, passes OpenXML package checks,
        and re-opens cleanly with python-pptx matching the expected slide count.
        """
        logger.debug(f"Verifying generated PowerPoint deck at: {file_path}")

        if not os.path.exists(file_path):
            raise ToolExecutionException(
                message=f"Validation failed: File was not created at {file_path}."
            )

        if os.path.getsize(file_path) == 0:
            raise ToolExecutionException(
                message=f"Validation failed: File created at {file_path} is empty."
            )

        # 1. Deep OpenXML package structure & relationship validation
        is_valid_pkg, issues = validate_openxml_package(file_path)
        if not is_valid_pkg:
            raise ToolExecutionException(
                message=f"Validation failed: OpenXML package structure is corrupt in '{file_path}': {'; '.join(issues)}",
                details={"issues": issues},
            )

        # 2. Re-read with python-pptx to verify presentation can be opened
        try:
            prs = pptx.Presentation(file_path)
            slide_count = len(prs.slides)
            if slide_count != expected_slides:
                raise ToolExecutionException(
                    message=(
                        f"Validation failed: Slide count mismatch. "
                        f"Expected {expected_slides}, got {slide_count}."
                    )
                )
            logger.info(f"PowerPoint verification check succeeded ({slide_count} slides).")
        except ToolExecutionException:
            raise
        except Exception as e:
            logger.exception("Failed to parse output PPTX file.")
            raise ToolExecutionException(
                message=(
                    f"Validation failed: Generated file is corrupted or cannot be reopened. "
                    f"Details: {str(e)}"
                )
            ) from e
