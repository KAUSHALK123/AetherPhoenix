import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.tools.web_research.tool import WebResearchTool
from app.tools.web_research.schemas import WebResearchRequest

@pytest.mark.asyncio
async def test_mcp_research_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/mcp/commands/research",
            json={"query": "latest trends in edge AI", "max_results": 3}
        )
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "summary" in data
        assert "sources" in data
        assert len(data["sources"]) >= 2
        # Verify clean small paragraph structure
        summary = data["summary"]
        assert "Executive Overview" in summary or "Key Trends" in summary or "Trends" in summary
        paragraphs = [p.strip() for p in summary.split("\n\n") if p.strip()]
        for p in paragraphs:
            # None of the paragraphs should be massive unbroken walls of text
            assert len(p) < 1200

@pytest.mark.asyncio
async def test_web_research_tool_clean_paragraphs():
    tool = WebResearchTool()
    req = WebResearchRequest(query="latest trends in edge AI", max_results=3, extract_content=False)
    res = await tool.research(req)
    assert res.summary is not None
    assert len(res.sources) >= 2
    paragraphs = [p.strip() for p in res.summary.split("\n\n") if p.strip()]
    for p in paragraphs:
        assert len(p) < 1200
