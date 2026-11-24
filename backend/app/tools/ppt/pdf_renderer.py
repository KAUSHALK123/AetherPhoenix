import logging
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from app.core.exceptions import ToolExecutionException
from app.schemas.ppt import PresentationSchema, SlideContent, SlideType

logger = logging.getLogger(__name__)

# 16:9 Widescreen slide dimensions in points (13.33 x 7.5 inches at 72 dpi)
SLIDE_WIDTH = 960.0
SLIDE_HEIGHT = 540.0

THEME_PALETTES = {
    "modern_tech": {
        "header_bg": colors.HexColor("#0F172A"),
        "title_color": colors.HexColor("#FFFFFF"),
        "subtitle_color": colors.HexColor("#94A3B8"),
        "accent": colors.HexColor("#2563EB"),
        "accent_light": colors.HexColor("#38BDF8"),
        "card_bg": colors.HexColor("#F8FAFC"),
        "card_border": colors.HexColor("#E2E8F0"),
        "text_primary": colors.HexColor("#1E293B"),
        "text_secondary": colors.HexColor("#64748B"),
        "callout_bg": colors.HexColor("#EFF6FF"),
        "callout_border": colors.HexColor("#3B82F6"),
    },
    "executive": {
        "header_bg": colors.HexColor("#1A365D"),
        "title_color": colors.HexColor("#FFFFFF"),
        "subtitle_color": colors.HexColor("#CBD5E1"),
        "accent": colors.HexColor("#2B6CB0"),
        "accent_light": colors.HexColor("#63B3ED"),
        "card_bg": colors.HexColor("#F7FAFC"),
        "card_border": colors.HexColor("#E2E8F0"),
        "text_primary": colors.HexColor("#2D3748"),
        "text_secondary": colors.HexColor("#718096"),
        "callout_bg": colors.HexColor("#EBF8FF"),
        "callout_border": colors.HexColor("#3182CE"),
    },
    "minimal": {
        "header_bg": colors.HexColor("#27272A"),
        "title_color": colors.HexColor("#FFFFFF"),
        "subtitle_color": colors.HexColor("#A1A1AA"),
        "accent": colors.HexColor("#52525B"),
        "accent_light": colors.HexColor("#71717A"),
        "card_bg": colors.HexColor("#FAFAFA"),
        "card_border": colors.HexColor("#E4E4E7"),
        "text_primary": colors.HexColor("#18181B"),
        "text_secondary": colors.HexColor("#71717A"),
        "callout_bg": colors.HexColor("#F4F4F5"),
        "callout_border": colors.HexColor("#A1A1AA"),
    },
}


class PresentationPDFRenderer:
    """
    Renders presentation slide decks directly into high-fidelity 16:9 widescreen
    landscape PDF documents, preserving slide layout, dimensions, styling, and images.
    """

    def __init__(self, style_name: str = "modern_tech") -> None:
        self.palette = THEME_PALETTES.get(style_name, THEME_PALETTES["modern_tech"])
        self.styles = getSampleStyleSheet()
        self._init_styles()

    def _init_styles(self) -> None:
        self.title_slide_title = ParagraphStyle(
            "TitleSlideTitle",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=34,
            leading=40,
            textColor=colors.HexColor("#FFFFFF"),
            alignment=1,  # Center
        )
        self.title_slide_subtitle = ParagraphStyle(
            "TitleSlideSubtitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=18,
            leading=24,
            textColor=self.palette["subtitle_color"],
            alignment=1,  # Center
        )
        self.slide_title = ParagraphStyle(
            "SlideTitle",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=self.palette["title_color"],
        )
        self.slide_subtitle = ParagraphStyle(
            "SlideSubtitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=self.palette["subtitle_color"],
        )
        self.bullet_text = ParagraphStyle(
            "BulletText",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=16,
            textColor=self.palette["text_primary"],
        )
        self.callout_text = ParagraphStyle(
            "CalloutText",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=self.palette["accent"],
        )
        self.footer_text = ParagraphStyle(
            "FooterText",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=self.palette["text_secondary"],
        )

    def render(
        self,
        presentation: PresentationSchema,
        output_path: str | Path,
    ) -> Path:
        """
        Compiles the PresentationSchema into a 16:9 widescreen PDF document.
        """
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        total_slides = len(presentation.slides)
        c = canvas.Canvas(str(out_p), pagesize=(SLIDE_WIDTH, SLIDE_HEIGHT))

        for idx, slide in enumerate(presentation.slides, start=1):
            if slide.slide_type == SlideType.TITLE or idx == 1:
                self._draw_title_slide(c, slide, presentation)
            else:
                self._draw_content_slide(c, slide, presentation, idx, total_slides)
            c.showPage()

        c.save()
        self._validate_pdf(out_p, total_slides)
        logger.info(f"Presentation PDF rendered successfully to '{out_p}' ({total_slides} slides)")
        return out_p

    def _draw_title_slide(
        self,
        c: canvas.Canvas,
        slide: SlideContent,
        presentation: PresentationSchema,
    ) -> None:
        """Renders the executive title slide with modern dark banner background."""
        # Full slide dark background
        c.setFillColor(self.palette["header_bg"])
        c.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, fill=True, stroke=False)

        # Decorative accent gradient / ribbon on left
        c.setFillColor(self.palette["accent"])
        c.rect(0, 0, 16, SLIDE_HEIGHT, fill=True, stroke=False)

        # Subtle top accent bar
        c.setFillColor(self.palette["accent_light"])
        c.rect(16, SLIDE_HEIGHT - 8, SLIDE_WIDTH - 16, 8, fill=True, stroke=False)

        # Title container
        content_y = SLIDE_HEIGHT / 2 + 30
        title_para = Paragraph(slide.title, self.title_slide_title)
        _, h = title_para.wrap(SLIDE_WIDTH - 120, 150)
        title_para.drawOn(c, 60, content_y)

        # Subtitle
        sub_text = slide.subtitle or presentation.subtitle or "Strategic & Technical Analysis"
        sub_para = Paragraph(sub_text, self.title_slide_subtitle)
        _, sub_h = sub_para.wrap(SLIDE_WIDTH - 140, 80)
        sub_para.drawOn(c, 70, content_y - sub_h - 16)

        # Audience / Date / Author metadata footer
        meta_items = ["AetherPhoenix Research & Export Engine"]
        if presentation.audience:
            meta_items.append(f"Audience: {presentation.audience.title()}")
        meta_items.append("Verified Deliverable")

        c.setFont("Helvetica", 10)
        c.setFillColor(self.palette["subtitle_color"])
        c.drawCentredString(SLIDE_WIDTH / 2, 45, " | ".join(meta_items))

    def _draw_content_slide(
        self,
        c: canvas.Canvas,
        slide: SlideContent,
        presentation: PresentationSchema,
        slide_idx: int,
        total_slides: int,
    ) -> None:
        """Renders standard content, data, and visual slides."""
        # White base background
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, fill=True, stroke=False)

        # Top Header Banner
        header_height = 80.0
        c.setFillColor(self.palette["header_bg"])
        c.rect(0, SLIDE_HEIGHT - header_height, SLIDE_WIDTH, header_height, fill=True, stroke=False)

        # Left Accent strip on header
        c.setFillColor(self.palette["accent"])
        c.rect(0, SLIDE_HEIGHT - header_height, 8, header_height, fill=True, stroke=False)

        # Bottom accent line under header
        c.setFillColor(self.palette["accent_light"])
        c.rect(8, SLIDE_HEIGHT - header_height, SLIDE_WIDTH - 8, 3, fill=True, stroke=False)

        # Header Title text
        title_para = Paragraph(slide.title, self.slide_title)
        title_para.wrap(SLIDE_WIDTH - 60, 40)
        title_para.drawOn(c, 36, SLIDE_HEIGHT - 48)

        # Header Subtitle / Section if present
        sub_info = slide.section_header or slide.subtitle
        if sub_info:
            sub_para = Paragraph(sub_info, self.slide_subtitle)
            sub_para.wrap(SLIDE_WIDTH - 60, 20)
            sub_para.drawOn(c, 36, SLIDE_HEIGHT - 68)

        # Available body space: from Y=50 (above footer) to Y=SLIDE_HEIGHT - header_height - 15
        body_top = SLIDE_HEIGHT - header_height - 20
        body_bottom = 50.0
        available_height = body_top - body_bottom

        # Check if an image is attached to this slide
        has_image = bool(
            slide.image_path and Path(slide.image_path).exists() and Path(slide.image_path).stat().st_size > 0
        )

        left_width = (SLIDE_WIDTH - 90) * 0.58 if has_image else (SLIDE_WIDTH - 72)
        right_x = 36 + left_width + 20
        right_width = SLIDE_WIDTH - right_x - 36

        # Draw content cards / bullet points in left/main section
        y_cursor = body_top
        bullets = slide.bullets or []

        # Callout card at top if present
        if slide.callout:
            callout_h = 36.0
            c.setFillColor(self.palette["callout_bg"])
            c.setStrokeColor(self.palette["callout_border"])
            c.setLineWidth(1)
            c.roundRect(36, y_cursor - callout_h, left_width, callout_h, 4, fill=True, stroke=True)

            callout_para = Paragraph(f"★ <b>Key Takeaway:</b> {slide.callout}", self.callout_text)
            callout_para.wrap(left_width - 24, callout_h)
            callout_para.drawOn(c, 48, y_cursor - callout_h + 10)
            y_cursor -= (callout_h + 12)

        # Render bullets in structured clean cards
        if bullets:
            num_bullets = len(bullets)
            spacing = 10.0
            item_h = max(34.0, min(56.0, (y_cursor - body_bottom - (num_bullets - 1) * spacing) / num_bullets))

            for bullet in bullets:
                card_y = y_cursor - item_h
                # Card background
                c.setFillColor(self.palette["card_bg"])
                c.setStrokeColor(self.palette["card_border"])
                c.setLineWidth(0.8)
                c.roundRect(36, card_y, left_width, item_h, 5, fill=True, stroke=True)

                # Bullet indicator bar on left of card
                c.setFillColor(self.palette["accent"])
                c.rect(36, card_y, 4, item_h, fill=True, stroke=False)

                # Bullet text
                bullet_para = Paragraph(f"• {bullet}", self.bullet_text)
                bullet_para.wrap(left_width - 24, item_h - 8)
                # Vertically center in card
                bullet_para.drawOn(c, 48, card_y + (item_h - 18) / 2)

                y_cursor -= (item_h + spacing)

        # Draw Table if present
        if slide.table_data and isinstance(slide.table_data, dict):
            headers = slide.table_data.get("headers", [])
            rows = slide.table_data.get("rows", [])
            if headers or rows:
                self._draw_table_card(c, headers, rows, 36, body_bottom + 10, left_width, max(120, y_cursor - body_bottom))

        # Draw Image in right pane if present
        if has_image:
            self._draw_image_card(c, slide.image_path, right_x, body_bottom + 10, right_width, available_height - 10)

        # Footer divider line
        c.setLineWidth(0.6)
        c.setStrokeColor(self.palette["card_border"])
        c.line(36, 40, SLIDE_WIDTH - 36, 40)

        # Footer Title on left
        deck_title = presentation.title
        c.setFont("Helvetica", 8.5)
        c.setFillColor(self.palette["text_secondary"])
        c.drawString(36, 26, f"{deck_title} — AetherPhoenix Verified Presentation")

        # Sources preview if present
        if slide.sources:
            src_text = f"Sources: {', '.join(slide.sources[:2])}"
            c.drawString(340, 26, src_text[:60] + ("..." if len(src_text) > 60 else ""))

        # Slide Number on right
        page_str = f"Slide {slide_idx} of {total_slides}"
        c.drawRightString(SLIDE_WIDTH - 36, 26, page_str)

    def _draw_table_card(
        self,
        c: canvas.Canvas,
        headers: List[str],
        rows: List[List[str]],
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Draws structured tabular data inside a stylized container."""
        c.setFillColor(self.palette["card_bg"])
        c.setStrokeColor(self.palette["card_border"])
        c.roundRect(x, y, width, height, 4, fill=True, stroke=True)

        if not headers and not rows:
            return

        all_rows = ([headers] if headers else []) + rows
        num_rows = len(all_rows)
        row_h = min(28.0, height / max(1, num_rows))
        col_w = width / max(1, len(all_rows[0]))

        cur_y = y + height - row_h
        for r_idx, row in enumerate(all_rows):
            is_header = (r_idx == 0 and bool(headers))
            if is_header:
                c.setFillColor(self.palette["accent"])
                c.rect(x, cur_y, width, row_h, fill=True, stroke=False)
                c.setFillColor(colors.HexColor("#FFFFFF"))
                c.setFont("Helvetica-Bold", 10)
            else:
                c.setFillColor(self.palette["text_primary"])
                c.setFont("Helvetica", 9)

            for c_idx, cell in enumerate(row):
                cell_x = x + (c_idx * col_w) + 8
                c.drawString(cell_x, cur_y + (row_h - 10) / 2, str(cell)[:30])

            cur_y -= row_h

    def _draw_image_card(
        self,
        c: canvas.Canvas,
        image_path: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Draws an embedded image inside a polished container with rounded borders."""
        # Container box
        c.setFillColor(self.palette["card_bg"])
        c.setStrokeColor(self.palette["card_border"])
        c.setLineWidth(1)
        c.roundRect(x, y, width, height, 6, fill=True, stroke=True)

        try:
            # Draw image fitted inside container padding
            padding = 10.0
            img_x = x + padding
            img_y = y + padding
            img_w = width - (padding * 2)
            img_h = height - (padding * 2)

            c.drawImage(
                image_path,
                img_x,
                img_y,
                width=img_w,
                height=img_h,
                preserveAspectRatio=True,
                anchor="c",
            )
        except Exception as e:
            logger.warning(f"Could not render image '{image_path}' to PDF: {e}")
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColor(self.palette["text_secondary"])
            c.drawCentredString(x + width / 2, y + height / 2, "[Image: Visual Diagram]")

    def _validate_pdf(self, pdf_path: Path, expected_pages: int) -> None:
        """Validates that the output file exists, is non-empty, and has valid PDF bytes."""
        if not pdf_path.exists():
            raise ToolExecutionException(f"Validation failed: PDF was not created at '{pdf_path}'.")
        if pdf_path.stat().st_size == 0:
            raise ToolExecutionException(f"Validation failed: PDF created at '{pdf_path}' is empty (0 bytes).")

        with open(pdf_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                raise ToolExecutionException(f"Validation failed: Invalid PDF header '{header!r}' at '{pdf_path}'.")
