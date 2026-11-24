import zipfile
from pathlib import Path
from uuid import uuid4

import pptx
import pytest
from PIL import Image, ImageDraw
from shared.contracts.artifact import ArtifactType
from shared.contracts.task import Task, TaskCategory

from app.schemas.ppt import PresentationSchema, SlideContent, SlideType
from app.tools.export.engine import ExportEngine
from app.tools.ppt.adapter import PPTToolAdapter
from app.tools.ppt.converter import ResearchToSlideConverter
from app.tools.ppt.generator import PPTGenerator
from app.tools.ppt.pdf_renderer import PresentationPDFRenderer
from app.tools.ppt.xml_sanitizer import validate_openxml_package
from app.tools.web_research.schemas import (
    StructuredResearchResult,
    WebResearchRequest,
)
from app.tools.web_research.tool import WebResearchTool


# ==============================================================================
# Mandatory Test 1: Generate 10-slide AI presentation -> Valid 10-slide PPTX
# ==============================================================================
def test_generate_10_slide_ai_presentation(tmp_path):
    generator = PPTGenerator()
    out_file = str(tmp_path / "ai_presentation_10_slides.pptx")

    # Research findings simulated for 10-slide AI topic
    sources = [
        {"title": "State of AI 2026", "url": "https://example.com/state-of-ai-2026", "publication_date": "2026-01-15"},
        {"title": "Agentic AI Architectures", "url": "https://example.com/agentic-ai", "publication_date": "2026-02-01"},
    ]
    research_summary = """
    Emerging AI frameworks in 2026 focus heavily on autonomous multi-agent coordination and dynamic workflows.
    Key architectures include decentralized task decomposition and model-agnostic tool protocols.
    Enterprise adoption has expanded by 64% year-over-year in high-assurance industries.
    Self-healing execution pipelines reduce workflow failure rates by over 45%.
    """
    presentation = ResearchToSlideConverter.convert(
        topic="Emerging AI Frameworks & Agentic Systems 2026",
        research_summary=research_summary,
        sources=sources,
        slide_count=10,
        audience="technical",
        design_style="modern_tech",
    )

    assert len(presentation.slides) == 10
    assert presentation.slide_count == 10

    # Generate PPTX
    result = generator.generate(presentation=presentation, output_path=out_file)
    assert result.success is True
    assert result.slide_count == 10
    assert Path(out_file).exists()
    assert Path(out_file).stat().st_size > 0

    # Validate OpenXML ZIP structure & relationship targets
    is_valid, issues = validate_openxml_package(out_file)
    assert is_valid is True, f"Validation errors: {issues}"

    # Verify python-pptx can reopen and parse all 10 slides
    prs = pptx.Presentation(out_file)
    assert len(prs.slides) == 10
    assert "Emerging AI Frameworks" in prs.slides[0].shapes.title.text

    # Verify notes slide handling
    slide0 = prs.slides[0]
    if slide0.has_notes_slide:
        assert len(slide0.notes_slide.notes_text_frame.text) > 0


# ==============================================================================
# Mandatory Test 2: Research latest AI frameworks -> Real sources and verified findings
# ==============================================================================
@pytest.mark.asyncio
async def test_research_latest_ai_frameworks():
    research_tool = WebResearchTool()

    request = WebResearchRequest(
        query="Artificial intelligence agent architecture",
        max_results=3,
        extract_content=True,
    )

    result: StructuredResearchResult = await research_tool.research(request)

    assert result.query == request.query
    assert isinstance(result.sources, list)
    assert len(result.sources) > 0

    # Verify source attributes: verifiable URL, title, domain, publication date
    for s in result.sources:
        assert s.url.startswith("http://") or s.url.startswith("https://")
        assert len(s.title) > 0
        assert len(s.domain) > 0

    # Verify key findings and summary exist
    assert len(result.key_findings) > 0
    assert len(result.summary) > 20


# ==============================================================================
# Mandatory Test 3: Research and generate presentation -> Research-backed PPTX and PDF
# ==============================================================================
@pytest.mark.asyncio
async def test_research_and_generate_presentation_e2e(tmp_path):
    adapter = PPTToolAdapter()
    out_file = str(tmp_path / "verified_research_presentation.pptx")

    verified_sources = [
        {"title": "DeepSeek R1 Architecture", "url": "https://deepseek.ai/r1-paper", "publication_date": "2026-01-20"},
        {"title": "OpenAI Multi-Agent Swarms", "url": "https://openai.com/research/swarms", "publication_date": "2026-02-10"},
        {"title": "LangChain v1.0 Spec", "url": "https://langchain.com/blog/v1", "publication_date": "2026-02-15"},
    ]
    research_summary = (
        "Multi-agent reasoning architectures have shifted towards verifiable reasoning chains. "
        "Dynamic workflow graphs allow runtime task restructuring and self-correction. "
        "Cross-verification protocols prevent hallucinated claims and citation fabrications. "
        "Standardized MCP protocol adoption reached over 70% in modern developer tooling."
    )

    task = Task(
        workflow_id=uuid4(),
        task_name="Research-Backed Presentation",
        description="Generate 6-slide research-backed presentation with PDF deliverable",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="PPTX and PDF deliverables",
        inputs={
            "topic": "Next-Gen Multi-Agent Reasoning 2026",
            "output_path": out_file,
            "research_summary": research_summary,
            "sources": verified_sources,
            "slide_count": 6,
            "audience": "technical",
            "export_pdf": True,
        },
    )

    result = await adapter.execute(task)

    assert result.success is True
    assert result.error is None
    # Both PPT and PDF artifacts registered
    assert len(result.artifacts) == 2
    artifact_types = [a.artifact_type for a in result.artifacts]
    assert ArtifactType.PPT in artifact_types
    assert ArtifactType.PDF in artifact_types

    # Verify download URLs and paths
    assert "download_url" in result.output
    assert "pdf_download_url" in result.output
    assert Path(result.output["filepath"]).exists()
    assert Path(result.output["pdf_path"]).exists()

    # Verify PPTX contains 6 slides with sources attributed
    prs = pptx.Presentation(out_file)
    assert len(prs.slides) == 6

    # Verify OpenXML integrity
    is_valid, issues = validate_openxml_package(out_file)
    assert is_valid is True, f"OpenXML issues: {issues}"


# ==============================================================================
# Mandatory Test 4: Generate presentation with images -> Images embedded correctly
# ==============================================================================
def test_generate_presentation_with_images(tmp_path):
    generator = PPTGenerator()
    out_file = str(tmp_path / "presentation_with_images.pptx")

    # Create a valid test image
    img_path = str(tmp_path / "architecture_diagram.png")
    img = Image.new("RGB", (600, 400), color=(24, 76, 120))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 550, 350], outline=(255, 255, 255), width=4)
    draw.text((70, 70), "Agent Orchestration Diagram", fill=(255, 255, 255))
    img.save(img_path)

    presentation = PresentationSchema(
        title="Agent Architecture with Visuals",
        slides=[
            SlideContent(
                title="System Architecture Diagram",
                subtitle="Visual overview of agent workflow",
                slide_type=SlideType.IMAGE,
                image_path=img_path,
                bullets=[
                    "Dynamic planner decomposes incoming goals",
                    "Workers execute specialized capabilities via MCP",
                    "Supervisor verifies outputs against criteria",
                ],
            )
        ],
    )

    res = generator.generate(presentation=presentation, output_path=out_file)
    assert res.success is True
    assert Path(out_file).exists()

    # Validate OpenXML package and media inclusion
    is_valid, issues = validate_openxml_package(out_file)
    assert is_valid is True, f"Image presentation OpenXML issues: {issues}"

    # Verify that ppt/media/ directory exists inside zip with embedded image
    with zipfile.ZipFile(out_file, "r") as zf:
        media_files = [f for f in zf.namelist() if f.startswith("ppt/media/")]
        assert len(media_files) >= 1, "Image was not packaged into ppt/media/"

    # Verify python-pptx reopens correctly
    prs = pptx.Presentation(out_file)
    slide = prs.slides[0]
    has_pic = any(shape.shape_type == pptx.enum.shapes.MSO_SHAPE.RECTANGLE or hasattr(shape, "image") for shape in slide.shapes)
    assert has_pic, "Image shape was not created on slide"


# ==============================================================================
# Mandatory Test 5: Export to PDF -> PDF opens and displays correctly
# ==============================================================================
def test_export_to_pdf_fidelity_and_dimensions(tmp_path):
    pdf_renderer = PresentationPDFRenderer()
    pdf_out = str(tmp_path / "presentation_deliverable.pdf")

    presentation = PresentationSchema(
        title="High-Fidelity PDF Export Test",
        slides=[
            SlideContent(
                title="Slide 1: Executive Overview",
                bullets=["Strategic initiative 2026", "Comprehensive market survey", "Proven return on investment"],
                callout="Key Takeaway: Automation accelerates delivery by 4x.",
            ),
            SlideContent(
                title="Slide 2: Quantitative Metrics",
                bullets=["99.98% System Uptime", "Under 150ms mean response latency", "Zero data corruptions detected"],
            ),
            SlideContent(
                title="Slide 3: References & Citations",
                sources=["https://example.com/source1", "https://example.com/source2"],
                bullets=["Verified against primary source literature", "Audited by independent review panel"],
            ),
        ],
    )

    rendered_path = pdf_renderer.render(presentation=presentation, output_path=pdf_out)
    assert rendered_path.exists()
    assert rendered_path.stat().st_size > 1000

    # Validate PDF binary structure
    pdf_bytes = rendered_path.read_bytes()
    assert pdf_bytes.startswith(b"%PDF-"), "Invalid PDF header"
    assert b"%%EOF" in pdf_bytes[-1024:], "Missing PDF end-of-file marker"

    # Verify page count by inspecting /Type /Page references
    page_markers = pdf_bytes.count(b"/Type /Page") - pdf_bytes.count(b"/Type /Pages")
    assert page_markers == 3, f"Expected 3 pages, found {page_markers}"

    # Also test ExportEngine PPTX-to-PDF conversion
    export_engine = ExportEngine()
    ppt_generator = PPTGenerator()
    pptx_path = str(tmp_path / "source_for_export.pptx")
    ppt_generator.generate(presentation=presentation, output_path=pptx_path)

    exported_pdf_path = str(tmp_path / "exported_from_engine.pdf")
    pdf_converted = export_engine._convert_pptx_to_pdf(
        source_path=Path(pptx_path),
        output_path=Path(exported_pdf_path),
        request=None,
    )
    assert pdf_converted.exists()
    assert pdf_converted.stat().st_size > 1000
    assert pdf_converted.read_bytes().startswith(b"%PDF-")


# ==============================================================================
# Mandatory Test 6: Invalid generation input -> Clear error, no fake artifact
# ==============================================================================
@pytest.mark.asyncio
async def test_invalid_generation_input(tmp_path):
    adapter = PPTToolAdapter()

    # Scenario A: slide_count is 0 or negative
    task_invalid_count = Task(
        workflow_id=uuid4(),
        task_name="Invalid Slide Count Test",
        description="Test invalid slide count input handling",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="Failure with clear error",
        inputs={
            "topic": "Test Invalid",
            "slide_count": -5,
            "output_path": str(tmp_path / "should_not_exist.pptx"),
        },
    )
    res_a = await adapter.execute(task_invalid_count)
    assert res_a.success is False
    assert res_a.error is not None
    assert res_a.error.error_code in ("INVALID_INPUT", "PPT_GENERATION_FAILED")
    assert not Path(tmp_path / "should_not_exist.pptx").exists()
    assert len(res_a.artifacts) == 0

    # Scenario B: missing required topic or title
    task_missing_topic = Task(
        workflow_id=uuid4(),
        task_name="Missing Topic Test",
        description="Test missing topic input handling",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="Failure with clear error",
        inputs={
            "output_path": str(tmp_path / "missing_topic.pptx"),
        },
    )
    res_b = await adapter.execute(task_missing_topic)
    assert res_b.success is False
    assert res_b.error is not None
    assert res_b.error.error_code in ("INVALID_INPUT", "PPT_GENERATION_FAILED")
    assert not Path(tmp_path / "missing_topic.pptx").exists()
    assert len(res_b.artifacts) == 0
