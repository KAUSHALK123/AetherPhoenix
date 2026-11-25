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
