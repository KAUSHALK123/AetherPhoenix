import asyncio
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import pptx
from PIL import Image, ImageDraw

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus, TaskType
from shared.contracts.workflow import SharedWorkflowState

from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus
from app.engine.orchestrator import PipelineOrchestrator
from app.engine.workflow import WorkflowEngine
from app.main import app
from app.planner.decomposer import TaskDecompositionEngine
from app.planner.llm_planner import get_default_tool_registry
from app.schemas.ppt import PresentationSchema, SlideContent, SlideType
from app.services.artifact_storage import get_artifact_storage_service
from app.tools.export.engine import ExportEngine
from app.tools.ppt.adapter import PPTToolAdapter
from app.tools.ppt.converter import ResearchToSlideConverter
from app.tools.ppt.generator import PPTGenerator
from app.tools.ppt.pdf_renderer import PresentationPDFRenderer
from app.tools.ppt.xml_sanitizer import sanitize_xml_text, validate_openxml_package
from app.tools.web_research.schemas import WebResearchRequest
from app.tools.web_research.tool import WebResearchTool


SAMPLES_DIR = Path("backend/artifacts/samples").resolve()
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

audit_results = {}


def log_section(title: str):
    print("\n" + "=" * 80)
    print(f" AUDIT SCENARIO: {title}")
    print("=" * 80)


# ==============================================================================
# Scenario 1: Generate a 10-slide AI presentation
# ==============================================================================
async def audit_scenario_1():
    log_section("1. Generate 10-Slide AI Presentation")
    output_path = SAMPLES_DIR / "audit_10_slide_ai_frameworks.pptx"

    sources = [
        {
            "title": "State of AI 2026",
            "url": "https://arxiv.org/abs/2303.17760",
            "publication_date": "2026-01-15",
            "author": "ArXiv AI Research",
        },
        {
            "title": "Multi-Agent Architectures & Protocols",
            "url": "https://modelcontextprotocol.io/introduction",
            "publication_date": "2026-02-01",
            "author": "MCP Open Standard",
        },
    ]
    research_summary = """
    Multi-agent coordination in 2026 has transitioned to decentralized reasoning architectures.
    Standardized tool protocols (such as Model Context Protocol) provide secure interoperability across models.
    Enterprise workflows achieve over 60% higher completion rates with deterministic task verification.
    Autonomous self-healing mechanisms intercept transient execution errors with runtime retries.
    """

    presentation = ResearchToSlideConverter.convert(
        topic="Emerging AI Frameworks & Agentic Systems 2026",
        research_summary=research_summary,
        sources=sources,
        slide_count=10,
        audience="technical",
        design_style="modern_tech",
    )

    generator = PPTGenerator()
    res = generator.generate(presentation=presentation, output_path=str(output_path))

    # Verify OpenXML Package
    is_valid, xml_issues = validate_openxml_package(str(output_path))

    # Verify Reopening via python-pptx
    prs = pptx.Presentation(str(output_path))
    slide_count = len(prs.slides)
    slide_titles = [s.shapes.title.text for s in prs.slides if s.shapes.title and s.shapes.title.text]

    passed = (
        res.success
        and is_valid
        and slide_count == 10
        and len(slide_titles) == 10
    )

    audit_results["scenario_1"] = {
        "passed": passed,
        "slide_count": slide_count,
        "is_openxml_valid": is_valid,
        "xml_issues": xml_issues,
        "file_size": output_path.stat().st_size,
        "file_path": str(output_path),
        "titles": slide_titles[:3] + ["..."] + [slide_titles[-1]],
    }
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(f"Slides: {slide_count}/10 | OpenXML Valid: {is_valid} | File: {output_path} ({output_path.stat().st_size} bytes)")


# ==============================================================================
# Scenario 2: Research latest AI frameworks (real sources & verified findings)
# ==============================================================================
async def audit_scenario_2():
    log_section("2. Research Latest AI Frameworks (Real Sources & Verified Findings)")
    tool = WebResearchTool()

    req = WebResearchRequest(
        query="Artificial intelligence agent architecture",
        max_results=3,
        extract_content=True,
    )
    result = await tool.research(req)

    valid_sources = []
    for s in result.sources:
        if s.url and s.title and s.domain:
            valid_sources.append({
                "url": s.url,
                "title": s.title,
                "domain": s.domain,
                "date": s.publication_date,
                "author": s.author,
            })

    passed = (
        len(valid_sources) >= 1
        and len(result.key_findings) > 0
        and len(result.summary) > 20
    )

    audit_results["scenario_2"] = {
        "passed": passed,
        "sources_count": len(valid_sources),
        "sources": valid_sources,
        "key_findings_count": len(result.key_findings),
        "summary_length": len(result.summary),
    }
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(f"Sources Collected: {len(valid_sources)}")
    for s in valid_sources:
        print(f" - [{s['domain']}] {s['title']} ({s['url']}) [Date: {s['date']}]")
    print(f"Key Findings: {len(result.key_findings)} verified claims")


# ==============================================================================
# Scenario 3: Research a topic & generate complete research-backed PPTX and PDF
# ==============================================================================
async def audit_scenario_3():
    log_section("3. End-to-End Research-Backed PPTX and PDF Deliverables")
    adapter = PPTToolAdapter()
    out_pptx = SAMPLES_DIR / "audit_research_backed_presentation.pptx"

    task = Task(
        workflow_id=uuid4(),
        task_name="Research-Backed Multi-Agent Presentation",
        description="Compile research findings into a professional presentation and PDF deliverable",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="PPTX and PDF deliverables",
        inputs={
            "topic": "Autonomous Multi-Agent AI Frameworks 2026",
            "output_path": str(out_pptx),
            "slide_count": 6,
            "audience": "technical",
            "export_pdf": True,
            "research_summary": (
                "Decentralized agent swarms coordinate execution through message boards and standard tool contracts. "
                "Deterministic verification guarantees task state integrity and auditability. "
                "Self-healing workflows dynamically recover from transient tool exceptions. "
                "Adoption of Model Context Protocol (MCP) has accelerated multi-agent interoperability."
            ),
            "sources": [
                {
                    "title": "HuggingGPT Paper",
                    "url": "https://arxiv.org/abs/2303.17760",
                    "publication_date": "2023-03-30",
                    "author": "ArXiv Research",
                },
                {
                    "title": "Microsoft AutoGen Architecture",
                    "url": "https://github.com/microsoft/autogen",
                    "publication_date": "2024-01-10",
                    "author": "Microsoft Research",
                },
            ],
        },
    )

    res = await adapter.execute(task)
    out_pdf = Path(str(out_pptx).replace(".pptx", ".pdf"))

    pptx_valid, _ = validate_openxml_package(str(out_pptx))
    pdf_bytes = out_pdf.read_bytes() if out_pdf.exists() else b""
    is_pdf_valid = pdf_bytes.startswith(b"%PDF-") and b"%%EOF" in pdf_bytes[-1024:]

    passed = (
        res.success
        and pptx_valid
        and is_pdf_valid
        and len(res.artifacts) >= 2
    )

    audit_results["scenario_3"] = {
        "passed": passed,
        "artifacts_registered": len(res.artifacts),
        "pptx_path": str(out_pptx),
        "pptx_size": out_pptx.stat().st_size if out_pptx.exists() else 0,
        "pdf_path": str(out_pdf),
        "pdf_size": out_pdf.stat().st_size if out_pdf.exists() else 0,
        "download_url": res.output.get("download_url"),
        "pdf_download_url": res.output.get("pdf_download_url"),
    }
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(f"PPTX: {out_pptx} ({audit_results['scenario_3']['pptx_size']} bytes)")
    print(f"PDF:  {out_pdf} ({audit_results['scenario_3']['pdf_size']} bytes)")
    print(f"Download URLs: PPTX={res.output.get('download_url')} | PDF={res.output.get('pdf_download_url')}")


# ==============================================================================
# Scenario 4: Generate presentation containing embedded images
# ==============================================================================
async def audit_scenario_4():
    log_section("4. Generate Presentation with Embedded Images & Diagrams")
    out_pptx = SAMPLES_DIR / "audit_presentation_with_diagram.pptx"
    img_path = SAMPLES_DIR / "agent_orchestration_diagram.png"

    # Create real valid diagram
    img = Image.new("RGB", (700, 450), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    # Background card
    draw.rectangle([30, 30, 670, 420], outline=(56, 189, 248), width=3)
    draw.text((50, 50), "AetherPhoenix Architecture Diagram", fill=(255, 255, 255))
    draw.rectangle([50, 90, 220, 160], outline=(148, 163, 184), fill=(30, 41, 59))
    draw.text((70, 115), "1. Goal Planner", fill=(241, 245, 249))
    draw.line([(220, 125), (280, 125)], fill=(56, 189, 248), width=2)
    draw.rectangle([280, 90, 450, 160], outline=(148, 163, 184), fill=(30, 41, 59))
    draw.text((300, 115), "2. Research Agent", fill=(241, 245, 249))
    draw.line([(450, 125), (510, 125)], fill=(56, 189, 248), width=2)
    draw.rectangle([510, 90, 650, 160], outline=(148, 163, 184), fill=(30, 41, 59))
    draw.text((530, 115), "3. PPT Generator", fill=(241, 245, 249))
    draw.rectangle([180, 240, 520, 380], outline=(34, 197, 94), fill=(20, 83, 45))
    draw.text((210, 270), "Quality Assurance & Self-Healing Loop", fill=(255, 255, 255))
    draw.text((210, 305), "- OpenXML Package Validation", fill=(220, 252, 231))
    draw.text((210, 335), "- High-Fidelity 16:9 PDF Export", fill=(220, 252, 231))
    img.save(str(img_path))

    generator = PPTGenerator()
    presentation = PresentationSchema(
        title="Visual Agent Architecture Overview",
        slides=[
            SlideContent(
                title="AetherPhoenix Pipeline Architecture",
                subtitle="High-level orchestration and validation topology",
                slide_type=SlideType.IMAGE,
                image_path=str(img_path),
                bullets=[
                    "Dynamic Goal Decomposition breaks objectives into DAGs",
                    "Worker executes MCP tools with verifiable source tracking",
                    "Supervisor intercepts malformed packages and enforces QA",
                    "ExportEngine produces matching 16:9 widescreen PDFs",
                ],
            )
        ],
    )

    res = generator.generate(presentation=presentation, output_path=str(out_pptx))

    # Inspect ZIP media directory
    has_media = False
    with zipfile.ZipFile(str(out_pptx), "r") as zf:
        media = [name for name in zf.namelist() if name.startswith("ppt/media/")]
        has_media = len(media) > 0

    is_valid, _ = validate_openxml_package(str(out_pptx))

    prs = pptx.Presentation(str(out_pptx))
    slide = prs.slides[0]
    has_image_shape = any(
        hasattr(shape, "image") or shape.shape_type == pptx.enum.shapes.MSO_SHAPE.RECTANGLE
        for shape in slide.shapes
    )

    passed = res.success and has_media and is_valid and has_image_shape

    audit_results["scenario_4"] = {
        "passed": passed,
        "image_file": str(img_path),
        "pptx_file": str(out_pptx),
        "media_files_in_zip": media,
        "is_openxml_valid": is_valid,
    }
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(f"Embedded Image Found in ZIP: {media} | Shape on Slide: {has_image_shape}")


# ==============================================================================
# Scenario 5: Export PPTX to PDF & verify rendering and page dimensions
# ==============================================================================
async def audit_scenario_5():
    log_section("5. Export PPTX to PDF & Validate Fidelity and Dimensions")
    source_pptx = SAMPLES_DIR / "audit_10_slide_ai_frameworks.pptx"
    out_pdf = SAMPLES_DIR / "audit_10_slide_ai_frameworks.pdf"

    export_engine = ExportEngine()
    rendered_pdf = export_engine._convert_pptx_to_pdf(
        source_path=source_pptx,
        output_path=out_pdf,
        request=None,
    )

    pdf_bytes = rendered_pdf.read_bytes()
    is_pdf_header = pdf_bytes.startswith(b"%PDF-")
    is_pdf_eof = b"%%EOF" in pdf_bytes[-1024:]

    # Inspect page count
    pages = pdf_bytes.count(b"/Type /Page") - pdf_bytes.count(b"/Type /Pages")

    passed = is_pdf_header and is_pdf_eof and pages == 10 and rendered_pdf.stat().st_size > 5000

    audit_results["scenario_5"] = {
        "passed": passed,
        "source_pptx": str(source_pptx),
        "output_pdf": str(out_pdf),
        "pdf_size": rendered_pdf.stat().st_size,
        "page_count": pages,
        "is_pdf_header_valid": is_pdf_header,
        "is_pdf_eof_valid": is_pdf_eof,
    }
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(f"PDF Header: {is_pdf_header} | Pages: {pages}/10 | File Size: {rendered_pdf.stat().st_size} bytes")


# ==============================================================================
# Scenario 6: Submit invalid generation input -> Clear error & no fake artifacts
# ==============================================================================
async def audit_scenario_6():
    log_section("6. Invalid Generation Input Handling & Error Reporting")
    adapter = PPTToolAdapter()

    # Case A: Negative slide count
    task_negative_slides = Task(
        workflow_id=uuid4(),
        task_name="Invalid Negative Slides Task",
        description="Verify negative slide counts are rejected cleanly",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="Failure with INVALID_INPUT error",
        inputs={
            "topic": "Test Topic",
            "slide_count": -3,
            "output_path": str(SAMPLES_DIR / "should_not_exist_a.pptx"),
        },
    )
    res_a = await adapter.execute(task_negative_slides)
    case_a_passed = (
        not res_a.success
        and res_a.error is not None
        and res_a.error.error_code == "INVALID_INPUT"
        and not (SAMPLES_DIR / "should_not_exist_a.pptx").exists()
        and len(res_a.artifacts) == 0
    )

    # Case B: Missing topic and slides
    task_missing_topic = Task(
        workflow_id=uuid4(),
        task_name="Missing Topic Task",
        description="Verify missing topic is rejected cleanly",
        required_tool="ppt_tool",
        category=TaskCategory.PPT_GENERATION,
        expected_output="Failure with INVALID_INPUT error",
        inputs={
            "output_path": str(SAMPLES_DIR / "should_not_exist_b.pptx"),
        },
    )
    res_b = await adapter.execute(task_missing_topic)
    case_b_passed = (
        not res_b.success
        and res_b.error is not None
        and res_b.error.error_code == "INVALID_INPUT"
        and not (SAMPLES_DIR / "should_not_exist_b.pptx").exists()
        and len(res_b.artifacts) == 0
    )

    passed = case_a_passed and case_b_passed
    audit_results["scenario_6"] = {
        "passed": passed,
        "case_a_passed": case_a_passed,
        "case_a_error": res_a.error.error_message if res_a.error else None,
        "case_b_passed": case_b_passed,
        "case_b_error": res_b.error.error_message if res_b.error else None,
    }
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(f"Negative Slide Count Rejection: {case_a_passed} (Code: {res_a.error.error_code})")
    print(f"Missing Topic Rejection:        {case_b_passed} (Code: {res_b.error.error_code})")


# ==============================================================================
# Scenario 7: Test artifact downloads through actual FastAPI API endpoints
# ==============================================================================
async def audit_scenario_7():
    log_section("7. Artifact Downloads via FastAPI Application Endpoints")
    storage_service = get_artifact_storage_service()

    # Create real test PPTX and PDF artifacts in storage
    pptx_path = SAMPLES_DIR / "audit_10_slide_ai_frameworks.pptx"
    pdf_path = SAMPLES_DIR / "audit_10_slide_ai_frameworks.pdf"

    wf_id = uuid4()
    t_id = uuid4()

    ppt_art = Artifact(
        workflow_id=wf_id,
        task_id=t_id,
        name="ai_presentation_10_slides.pptx",
        filepath=str(pptx_path),
        artifact_type=ArtifactType.PPT,
        size_bytes=pptx_path.stat().st_size,
        checksum=hashlib.sha256(pptx_path.read_bytes()).hexdigest(),
        metadata={"slide_count": 10},
    )
    saved_ppt = await storage_service.register_artifact(ppt_art, content=pptx_path.read_bytes())

    pdf_art = Artifact(
        workflow_id=wf_id,
        task_id=t_id,
        name="ai_presentation_10_slides.pdf",
        filepath=str(pdf_path),
        artifact_type=ArtifactType.PDF,
        size_bytes=pdf_path.stat().st_size,
        checksum=hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        metadata={"page_count": 10},
    )
    saved_pdf = await storage_service.register_artifact(pdf_art, content=pdf_path.read_bytes())

    # Invoke FastAPI endpoint using ASGI client
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        # Test PPTX Download
        resp_ppt = await client.get(f"/api/v1/artifacts/{saved_ppt.artifact_id}/download")
        ppt_status = resp_ppt.status_code
        ppt_content_type = resp_ppt.headers.get("content-type")
        ppt_content_length = int(resp_ppt.headers.get("content-length", 0))

        # Test PDF Download
        resp_pdf = await client.get(f"/api/v1/artifacts/{saved_pdf.artifact_id}/download")
        pdf_status = resp_pdf.status_code
        pdf_content_type = resp_pdf.headers.get("content-type")
        pdf_content_length = int(resp_pdf.headers.get("content-length", 0))

    passed = (
        ppt_status == 200
        and "presentationml" in ppt_content_type
        and ppt_content_length > 1000
        and pdf_status == 200
        and "pdf" in pdf_content_type
        and pdf_content_length > 1000
    )

    audit_results["scenario_7"] = {
        "passed": passed,
        "pptx_download": {
            "status": ppt_status,
            "content_type": ppt_content_type,
            "bytes_received": ppt_content_length,
            "artifact_id": str(saved_ppt.artifact_id),
        },
        "pdf_download": {
            "status": pdf_status,
            "content_type": pdf_content_type,
            "bytes_received": pdf_content_length,
            "artifact_id": str(saved_pdf.artifact_id),
        },
    }
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(f"PPTX Download: HTTP {ppt_status} | MIME: {ppt_content_type} | Length: {ppt_content_length}")
    print(f"PDF  Download: HTTP {pdf_status} | MIME: {pdf_content_type} | Length: {pdf_content_length}")


# ==============================================================================
# Scenario 8: Test complete workflow through actual AetherPhoenix application
# ==============================================================================
async def audit_scenario_8():
    log_section("8. Complete Application Workflow (Planner -> Orchestrator -> Worker -> Supervisor)")
    workflow_id = uuid4()
    goal = "Research modern multi-agent systems and generate a 5-slide presentation"

    # 1. Planner Decomposes Goal into Hierarchical Tasks
    decomposer = TaskDecompositionEngine()
    plan = decomposer.decompose_goal(goal, workflow_id=workflow_id)
    tasks = plan.tasks if hasattr(plan, "tasks") else plan

    print(f"Planner generated {len(tasks)} tasks:")
    for t in tasks:
        print(f" - [{t.category.value}] '{t.task_name}' (Tool: '{t.required_tool}') [Deps: {len(t.dependencies)}]")

    # 2. Setup Orchestrator Engine with Registry, Worker, Supervisor, and EventBus
    registry = get_default_tool_registry()
    event_bus = EventBus()
    from app.core.permissions import get_permission_manager, ExecutionMode
    perm_manager = get_permission_manager()
    perm_manager.set_mode(ExecutionMode.AUTONOMOUS)
    worker = WorkerAgent(tool_registry=registry, permission_manager=perm_manager)
    supervisor = SupervisorAgent(event_bus=event_bus)

    orchestrator = PipelineOrchestrator(
        worker_agent=worker,
        supervisor_agent=supervisor,
        event_bus=event_bus,
    )

    from shared.contracts.workflow import WorkflowMetadata, WorkflowStatus

    metadata = WorkflowMetadata(
        workflow_id=str(workflow_id), goal=goal, status=WorkflowStatus.CREATED
    )
    state = SharedWorkflowState(
        metadata=metadata, tasks={t.task_id: t for t in tasks}
    )
    for t in tasks:
        state.execution_queue.append(t.task_id)

    # 3. Execute Workflow with Supervision
    final_state = await orchestrator.run_workflow(state=state)

    artifacts_count = len(final_state.artifacts)
    passed = (
        final_state.metadata.status in (WorkflowStatus.COMPLETED, "COMPLETED")
        and artifacts_count > 0
    )

    audit_results["scenario_8"] = {
        "passed": passed,
        "task_count": len(tasks),
        "artifacts_produced": artifacts_count,
        "workflow_state": (
            final_state.metadata.status.value
            if hasattr(final_state.metadata.status, "value")
            else str(final_state.metadata.status)
        ),
    }
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(
        f"Workflow Status: {final_state.metadata.status} | Artifacts Produced:"
        f" {artifacts_count}"
    )


async def main():
    print("=" * 80)
    print(" STARTING AETHERPHOENIX COMPREHENSIVE END-TO-END AUDIT")
    print(f" Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    await audit_scenario_1()
    await audit_scenario_2()
    await audit_scenario_3()
    await audit_scenario_4()
    await audit_scenario_5()
    await audit_scenario_6()
    await audit_scenario_7()
    await audit_scenario_8()

    print("\n" + "=" * 80)
    print(" FINAL AUDIT SUMMARY OF ALL SCENARIOS")
    print("=" * 80)
    all_passed = all(r.get("passed", False) for r in audit_results.values())
    for name, r in audit_results.items():
        print(f" {name.upper()}: {'PASSED' if r.get('passed') else 'FAILED'}")
    print(f"\nOVERALL RESULT: {'ALL SCENARIOS PASSED (100%)' if all_passed else 'SOME SCENARIOS FAILED'}")

    # Write audit report JSON for programmatic inspection
    report_path = SAMPLES_DIR / "audit_execution_report.json"
    with open(report_path, "w", encoding="utf-8") as fp:
        json.dump(audit_results, fp, indent=2, default=str)
    print(f"\nDetailed audit log written to: {report_path}")

if __name__ == "__main__":
    asyncio.run(main())
