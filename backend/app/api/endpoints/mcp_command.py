from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.tools.terminal.command_resolver import CommandResolverEngine

router = APIRouter()


class ResolveCommandRequest(BaseModel):
    query: Optional[str] = None
    prompt: Optional[str] = None
    target_os: Optional[str] = None
    os_type: Optional[str] = None


class ResolvedCommandResponse(BaseModel):
    command: str
    display_name: str
    description: str
    category: str
    risk_level: str
    platform: str
    is_safe: bool
    explanation: Optional[str] = None


class MCPResearchRequest(BaseModel):
    query: Optional[str] = None
    prompt: Optional[str] = None
    max_results: Optional[int] = 5


class MCPSourceItem(BaseModel):
    title: str
    url: str
    domain: str
    snippet: str


class MCPPPTRequest(BaseModel):
    topic: Optional[str] = None
    prompt: Optional[str] = None
    slide_count: Optional[int] = 5
    title: Optional[str] = None


class SlidePreviewItem(BaseModel):
    slide_number: int
    title: str
    bullets: List[str]


class MCPPPTResponse(BaseModel):
    artifact_id: str
    filename: str
    download_url: str
    file_size_bytes: int
    slide_count: int
    title: str
    slides: List[SlidePreviewItem]
    preview_content: str


class MCPResearchResponse(BaseModel):
    query: str
    summary: str
    sources: List[MCPSourceItem]
    total_sources_found: int
    execution_time_seconds: float


@router.post("/research", response_model=MCPResearchResponse)
async def execute_mcp_research_endpoint(
    request: MCPResearchRequest,
) -> MCPResearchResponse:
    """
    MCP-compatible endpoint to execute live web research, gather multi-source information,
    and synthesize clean, detailed results in small concise paragraphs.
    """
    from app.tools.web_research.schemas import WebResearchRequest
    from app.tools.web_research.tool import WebResearchTool

    effective_query = (
        request.query
        or request.prompt
        or "latest technology trends"
    ).strip()

    tool = WebResearchTool()
    req = WebResearchRequest(
        query=effective_query,
        max_results=request.max_results or 5,
        extract_content=True,
    )
    result = await tool.research(req)

    clean_sources = [
        MCPSourceItem(
            title=s.title or s.domain or "Web Source",
            url=s.url,
            domain=s.domain or "web",
            snippet=s.snippet or "",
        )
        for s in result.sources
        if getattr(s, "status", None) in ("SUCCESS", "SourceStatus.SUCCESS", getattr(getattr(s, "status", None), "value", "SUCCESS"))
    ]

    return MCPResearchResponse(
        query=result.query,
        summary=result.summary,
        sources=clean_sources,
        total_sources_found=len(clean_sources),
        execution_time_seconds=result.execution_time_seconds,
    )


@router.post("/ppt", response_model=MCPPPTResponse)
async def generate_mcp_ppt_endpoint(request: MCPPPTRequest) -> MCPPPTResponse:
    """
    MCP-compatible endpoint to generate a fully populated PowerPoint presentation (.pptx)
    with complete outlines, structured titles, 3-5 informative bullets per slide, and speaker notes.
    """
    import hashlib
    import re
    import uuid
    from pathlib import Path
    from shared.contracts.artifact import Artifact, ArtifactType
    from app.core.config import get_config
    from app.schemas.ppt import PresentationSchema, SlideContent, SlideType
    from app.services.artifact_storage import get_artifact_storage_service
    from app.tools.ppt.content_generator import PPTContentGenerator
    from app.tools.ppt.generator import PPTGenerator

    topic = (request.topic or request.prompt or "Executive Strategic Presentation").strip()
    slide_count = max(1, request.slide_count or 5)

    # 1. Generate rich structured outline with bullets
    content_gen = PPTContentGenerator()
    outline = await content_gen.generate_outline(topic=topic, slide_count=slide_count)

    schema_slides = []
    for idx, s in enumerate(outline.slides):
        s_type = SlideType.TITLE if idx == 0 else SlideType.CONTENT
        schema_slides.append(
            SlideContent(
                title=s.title,
                subtitle=s.subtitle,
                slide_type=s_type,
                bullets=s.bullets,
                speaker_notes=s.speaker_notes,
            )
        )

    presentation = PresentationSchema(
        title=outline.title or topic,
        slides=schema_slides,
    )

    # 2. Compile .pptx file
    clean_stem = re.sub(r"[^\w\s-]", "", topic).strip().replace(" ", "_").lower()
    if not clean_stem or clean_stem in ["presentation", "ppt"]:
        clean_stem = "presentation"
    filename = f"{clean_stem}.pptx"

    cfg = get_config()
    workflow_id = uuid.uuid4()
    task_id = uuid.uuid4()
    output_dir = Path(cfg.ARTIFACTS_DIR) / str(workflow_id) / str(task_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / filename)

    generator = PPTGenerator()
    generator.generate(
        presentation=presentation,
        output_path=output_path,
        workflow_id=workflow_id,
    )

    file_bytes = Path(output_path).read_bytes()
    checksum = hashlib.sha256(file_bytes).hexdigest()

    # 3. Register with ArtifactStorageService
    storage_svc = get_artifact_storage_service()
    artifact = Artifact(
        workflow_id=workflow_id,
        task_id=task_id,
        name=filename,
        filepath=str(Path(output_path).resolve()),
        artifact_type=ArtifactType.PPT,
        size_bytes=len(file_bytes),
        checksum=checksum,
    )
    registered = await storage_svc.register_artifact(artifact)

    # 4. Format preview content with full bullets
    preview_lines = [f"# {presentation.title}"]
    slide_previews = []
    for idx, s in enumerate(presentation.slides, 1):
        preview_lines.append(f"\n### Slide {idx}: {s.title}")
        if s.subtitle:
            preview_lines.append(f"*{s.subtitle}*")
        for b in s.bullets:
            preview_lines.append(f"- {b}")
        slide_previews.append(
            SlidePreviewItem(
                slide_number=idx,
                title=s.title,
                bullets=s.bullets,
            )
        )

    return MCPPPTResponse(
        artifact_id=str(registered.artifact_id),
        filename=filename,
        download_url=f"/api/v1/artifacts/{registered.artifact_id}/download",
        file_size_bytes=len(file_bytes),
        slide_count=len(presentation.slides),
        title=presentation.title,
        slides=slide_previews,
        preview_content="\n".join(preview_lines),
    )


@router.post("/resolve", response_model=ResolvedCommandResponse)
async def resolve_command_endpoint(
    request: ResolveCommandRequest,
) -> ResolvedCommandResponse:
    """
    MCP-compatible endpoint to resolve natural language user prompts
    (e.g., 'chk my ipaddress', 'check disk space', 'show processes')
    into platform-safe executable shell commands.
    """
    effective_query = request.query or request.prompt or ""
    effective_os = request.target_os or request.os_type
    res = CommandResolverEngine.resolve(effective_query, target_os=effective_os)
    return ResolvedCommandResponse(
        command=res.command,
        display_name=res.display_name,
        description=res.description,
        category=res.category,
        risk_level=res.risk_level,
        platform=res.platform,
        is_safe=res.is_safe,
        explanation=res.explanation,
    )


@router.get("/catalog")
async def get_mcp_command_catalog() -> Dict[str, Any]:
    """
    Returns the standard MCP command taxonomy and translation patterns.
    """
    catalog = CommandResolverEngine.get_catalog()
    categories = list(dict.fromkeys(item["category"] for item in catalog))
    return {
        "categories": categories,
        "catalog": catalog,
        "count": len(catalog),
    }
