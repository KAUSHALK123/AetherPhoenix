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


@router.post("/resolve", response_model=ResolvedCommandResponse)
async def resolve_command_endpoint(request: ResolveCommandRequest) -> ResolvedCommandResponse:
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
