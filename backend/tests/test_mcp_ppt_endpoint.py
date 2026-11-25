import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
import pptx

@pytest.mark.asyncio
async def test_mcp_ppt_generation_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/mcp/commands/ppt",
            json={"topic": "Solar Energy Solutions", "slide_count": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "artifact_id" in data
        assert "download_url" in data
        assert data["slide_count"] == 5
        assert len(data["slides"]) == 5
        
        # Verify that EVERY content slide has bullet points (not titles only!)
        for slide in data["slides"][1:]:
            assert len(slide["bullets"]) >= 2
            for bullet in slide["bullets"]:
                assert len(bullet) > 10

        # Now test downloading the real generated artifact
        download_res = await client.get(data["download_url"])
        assert download_res.status_code == 200
        assert download_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert len(download_res.content) > 10000

        # Save and verify with python-pptx that slides have body bullet points
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
            tmp.write(download_res.content)
            tmp_path = tmp.name

        prs = pptx.Presentation(tmp_path)
        slides_list = list(prs.slides)
        assert len(slides_list) == 5
        for s in slides_list[1:]:
            paragraphs = [p.text for shape in s.shapes if shape.has_text_frame for p in shape.text_frame.paragraphs if p.text.strip()]
            # Must have title PLUS content bullets
            assert len(paragraphs) >= 3
