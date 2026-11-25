"""
Content generator for PowerPoint presentation generation.
Generates structured presentation outlines (title, N slides, 3-5 concise bullets each, speaker notes)
validated against a Pydantic schema.
Infers sensible content if no topic details are given and respects requested slide counts exactly.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

import httpx
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class SlideOutline(BaseModel):
    """Pydantic schema for an individual presentation slide."""
    title: str = Field(..., description="Slide title")
    subtitle: Optional[str] = Field(None, description="Optional subtitle for title slide")
    bullets: List[str] = Field(default_factory=list, description="3-5 concise bullet points")
    speaker_notes: Optional[str] = Field(None, description="Speaker notes for this slide")


class PresentationOutline(BaseModel):
    """Pydantic schema for a complete presentation outline."""
    title: str = Field(..., description="Overall presentation title")
    slides: List[SlideOutline] = Field(..., description="List of slides matching requested count")


def sanitize_bullet_text(text: str, max_chars: int = 120) -> str:
    """Caps bullet length to prevent slide text overflow."""
    cleaned = text.strip().replace("\n", " ")
    if len(cleaned) > max_chars:
        return cleaned[: max_chars - 3].rstrip() + "..."
    return cleaned


class PPTContentGenerator:
    """Generates structured presentation outlines via LLM or intelligent domain fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    async def generate_outline(
        self,
        topic: str,
        slide_count: int = 5,
        context: Optional[str] = None,
    ) -> PresentationOutline:
        """
        Generates an outline with exactly `slide_count` slides.
        Infers content if topic is minimal or unspecific.
        """
        target_count = max(1, slide_count)
        inferred_topic = self._infer_topic(topic)

        # 1. Attempt LLM generation if API key is present
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                outline = await self._call_gemini_outline(inferred_topic, target_count, gemini_key, context)
                if len(outline.slides) == target_count:
                    return outline
            except Exception as e:
                logger.warning(f"Gemini presentation outline generation failed: {e}. Using deterministic fallback.")

        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                outline = await self._call_openai_outline(inferred_topic, target_count, openai_key, context)
                if len(outline.slides) == target_count:
                    return outline
            except Exception as e:
                logger.warning(f"OpenAI presentation outline generation failed: {e}. Using deterministic fallback.")

        # 2. Deterministic intelligent content generation
        return self._generate_procedural_outline(inferred_topic, target_count, context)

    def _infer_topic(self, topic: str) -> str:
        """Infers a sensible topic title from the user prompt."""
        cleaned = topic.strip()
        if not cleaned or cleaned.lower() in ["presentation", "ppt", "slides", "deck", ""]:
            return "Executive Strategic Briefing"

        # Strip prefixes like "make a 5 slide ppt on", "create presentation about"
        cleaned = re.sub(
            r"^(?:make|create|generate|prepare|design|build)?\s*(?:a|an)?\s*\d*\s*(?:slide|slides|page|pages)?\s*(?:ppt|pptx|presentation|deck|slides)?\s*(?:on|about|for|regarding)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        if not cleaned:
            return "Executive Strategic Briefing"

        return cleaned.title()

    async def _call_gemini_outline(
        self,
        topic: str,
        slide_count: int,
        api_key: str,
        context: Optional[str],
    ) -> PresentationOutline:
        """Calls Gemini API with structured JSON output constraint."""
        prompt = (
            f"You are an expert presentation designer. Create a PowerPoint presentation outline on: '{topic}'.\n"
            f"REQUIREMENT: Exactly {slide_count} slides.\n"
            f"Slide 1 MUST be a TITLE slide with title and subtitle.\n"
            f"Slides 2 to {slide_count} MUST be CONTENT slides, each having 3 to 5 concise bullet points (each bullet max 120 characters) and speaker notes.\n"
            f"Context: {context or 'None'}\n\n"
            "Respond ONLY with valid JSON conforming to this schema:\n"
            f"{json.dumps(PresentationOutline.model_json_schema(), indent=2)}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            outline = PresentationOutline.model_validate(parsed)

            # Enforce bullet character cap and slide count
            return self._normalize_outline(outline, topic, slide_count)

    async def _call_openai_outline(
        self,
        topic: str,
        slide_count: int,
        api_key: str,
        context: Optional[str],
    ) -> PresentationOutline:
        """Calls OpenAI API with JSON output format."""
        prompt = (
            f"Create a presentation outline for '{topic}' with exactly {slide_count} slides.\n"
            f"Slide 1: Title slide.\n"
            f"Slides 2..{slide_count}: 3-5 concise bullets each (max 120 chars per bullet) and speaker notes.\n"
            f"Context: {context or 'None'}\n"
            "Return valid JSON matching PresentationOutline schema."
        )

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "gpt-4o-mini",
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_text)
            outline = PresentationOutline.model_validate(parsed)
            return self._normalize_outline(outline, topic, slide_count)

    def _generate_procedural_outline(
        self,
        topic: str,
        slide_count: int,
        context: Optional[str] = None,
    ) -> PresentationOutline:
        """Generates high-quality domain-specific slides deterministically."""
        slides: List[SlideOutline] = []

        # 1. Title Slide
        slides.append(
            SlideOutline(
                title=topic,
                subtitle="Strategic Overview, Analysis & Roadmap",
                bullets=[],
                speaker_notes=f"Welcome. Today we present an in-depth strategic review of {topic}.",
            )
        )

        # Standard slide themes for topic progression
        content_themes = [
            (
                "Executive Summary & Market Landscape",
                [
                    f"Comprehensive market context and current dynamics in {topic}.",
                    "Key industry drivers, technological maturity, and adoption trends.",
                    "Primary challenges identified across operational and scalability boundaries.",
                    "Strategic rationale and targeted outcomes for immediate execution.",
                ],
                f"This slide establishes the foundational context and market dynamics for {topic}.",
            ),
            (
                "Core Technology & Fundamental Architecture",
                [
                    f"Fundamental operating principles and technical mechanisms of {topic}.",
                    "System architectural framework and component-level decomposition.",
                    "Key efficiency benchmarks, performance parameters, and safety standards.",
                    "Integration interfaces with existing infrastructure and workflows.",
                ],
                f"Reviewing the core technical architecture and operating parameters of {topic}.",
            ),
            (
                "Economic Analysis & Environmental Impact",
                [
                    "Capital expenditure versus long-term operational efficiency savings.",
                    "Lifecycle return on investment and quantifiable economic value.",
                    "Environmental sustainability metrics and carbon footprint reduction.",
                    "Regulatory compliance, policy incentives, and risk mitigations.",
                ],
                "Highlighting the financial viability, efficiency gains, and sustainability impact.",
            ),
            (
                "Implementation Roadmap & Milestones",
                [
                    "Phase 1: Readiness assessment, validation prototyping, and pilot testing.",
                    "Phase 2: Core deployment, infrastructure scaling, and integration.",
                    "Phase 3: Continuous monitoring, automated telemetry, and optimization.",
                    "Clear governance model with milestone gates and performance metrics.",
                ],
                "Outlining the phased rollout schedule, milestones, and governance framework.",
            ),
            (
                "Strategic Outlook & Future Trajectory",
                [
                    f"Emerging innovations and breakthrough paradigms advancing {topic}.",
                    "Global scaling opportunities and strategic ecosystem partnerships.",
                    "Anticipated industry impact over a 3 to 5 year horizon.",
                    "Actionable next steps, stakeholder alignment, and open discussion.",
                ],
                "Concluding with future developments, strategic opportunities, and next steps.",
            ),
        ]

        # Fill up to requested slide_count
        for i in range(1, slide_count):
            theme_idx = (i - 1) % len(content_themes)
            theme_title, default_bullets, theme_notes = content_themes[theme_idx]

            # Adjust title if count is large to maintain uniqueness
            slide_title = f"{i}. {theme_title}" if slide_count > 6 else theme_title
            bullets = [sanitize_bullet_text(b) for b in default_bullets]

            slides.append(
                SlideOutline(
                    title=slide_title,
                    subtitle=None,
                    bullets=bullets,
                    speaker_notes=theme_notes,
                )
            )

        return PresentationOutline(title=topic, slides=slides[:slide_count])

    def _normalize_outline(
        self,
        outline: PresentationOutline,
        topic: str,
        target_count: int,
    ) -> PresentationOutline:
        """Ensures exact slide count, capped bullet lengths, and non-empty titles."""
        slides = outline.slides

        # If too few slides, pad with procedural slides
        if len(slides) < target_count:
            procedural = self._generate_procedural_outline(topic, target_count)
            while len(slides) < target_count:
                slides.append(procedural.slides[len(slides)])

        # If too many slides, trim
        slides = slides[:target_count]

        # Sanitize bullet text and ensure 3-5 bullets for content slides
        for idx, slide in enumerate(slides):
            if not slide.title or not slide.title.strip():
                slide.title = f"Slide {idx + 1}"
            if idx > 0:
                sanitized = [sanitize_bullet_text(b) for b in slide.bullets if b.strip()]
                while len(sanitized) < 3:
                    sanitized.append(f"Strategic consideration for {slide.title}.")
                slide.bullets = sanitized[:5]
            if not slide.speaker_notes:
                slide.speaker_notes = f"Key discussion points for {slide.title}."

        return PresentationOutline(title=outline.title or topic, slides=slides)
