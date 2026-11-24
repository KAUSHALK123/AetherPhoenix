from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.tools.browser.mcp import MCPBrowserAdapter, MCPBrowserToolCatalog

router = APIRouter()
_adapter = MCPBrowserAdapter()


class MCPToolCallRequest(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = None


@router.get("/catalog")
async def get_mcp_browser_catalog() -> Dict[str, Any]:
    """Returns the Model Context Protocol (MCP) browser tool catalog and schemas."""
    tools = MCPBrowserToolCatalog.get_tools()
    return {
        "tools": tools,
        "count": len(tools),
        "protocol_version": "2024-11-05",
    }


@router.get("/status")
async def get_mcp_browser_status() -> Dict[str, Any]:
    """Returns the connection and readiness status of the MCP browser service."""
    return _adapter.check_connection()


@router.post("/execute")
async def execute_mcp_browser_tool(request: MCPToolCallRequest) -> Dict[str, Any]:
    """Executes an MCP browser tool call and returns structured results."""
    return await _adapter.execute_tool(name=request.name, arguments=request.arguments)
