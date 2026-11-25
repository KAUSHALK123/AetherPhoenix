import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest
from shared.contracts.browser import BrowserResult

from app.tools.browser.controller import BrowserController
from app.tools.canva.controller import (
    CanvaBrowserController,
)


@pytest.fixture
def mock_browser_controller():
    mock_browser = MagicMock(spec=BrowserController)
    mock_page = MagicMock()
    mock_page.url = "https://www.canva.com"
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    mock_page.keyboard.type = AsyncMock()
    mock_page.locator = MagicMock(
        return_value=MagicMock(
            first=MagicMock(is_visible=AsyncMock(return_value=False))
        )
    )
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.expect_download = MagicMock()

    mock_browser._browser = MagicMock()
    mock_browser._page = mock_page
    mock_browser._session = MagicMock()
    mock_browser.permission_manager = None
    mock_browser.start_session = AsyncMock(return_value=BrowserResult(success=True))
    mock_browser.navigate = AsyncMock(
        return_value=BrowserResult(success=True, data={"url": "https://www.canva.com"})
    )

    return mock_browser


@pytest.mark.asyncio
async def test_canva_controller_open_canva(mock_browser_controller):
    controller = CanvaBrowserController(browser_controller=mock_browser_controller)

    res = await controller.open_canva(headless=False)

    assert res.success is True
    assert res.data["action"] == "open_canva"
    assert "canva.com" in res.data["url"]
    mock_browser_controller.navigate.assert_called_once()
    assert controller.active_design_info["status"] == "ready"


@pytest.mark.asyncio
async def test_canva_controller_create_instagram_post(mock_browser_controller):
    controller = CanvaBrowserController(browser_controller=mock_browser_controller)

    res = await controller.create_design(
        design_type="instagram_post",
        width=1080,
        height=1080,
        topic="Product Launch",
    )

    assert res.success is True
    assert res.data["design_type"] == "instagram_post"
    assert res.data["width"] == 1080
    assert res.data["height"] == 1080
    assert res.data["topic"] == "Product Launch"
    assert res.data["editor_open"] is True
    assert controller.active_design_info["dimensions"] == "1080 x 1080 px"


@pytest.mark.asyncio
async def test_canva_controller_create_poster(mock_browser_controller):
    controller = CanvaBrowserController(browser_controller=mock_browser_controller)

    res = await controller.create_design(
        design_type="poster",
        topic="College Fest 2026",
    )

    assert res.success is True
    assert res.data["design_type"] == "poster"
    assert res.data["width"] == 1080
    assert res.data["height"] == 1080 or res.data["height"] == 1920
    assert "College Fest" in res.data["topic"]


@pytest.mark.asyncio
async def test_canva_controller_create_presentation(mock_browser_controller):
    controller = CanvaBrowserController(browser_controller=mock_browser_controller)

    res = await controller.create_design(
        design_type="presentation",
        topic="Quarterly Business Review",
    )

    assert res.success is True
    assert res.data["design_type"] == "presentation"
    assert res.data["width"] == 1920
    assert res.data["height"] == 1080
    assert res.data["editor_open"] is True


@pytest.mark.asyncio
async def test_canva_controller_create_youtube_thumbnail(mock_browser_controller):
    controller = CanvaBrowserController(browser_controller=mock_browser_controller)

    res = await controller.create_design(
        design_type="youtube_thumbnail",
        topic="AI Tutorial",
    )

    assert res.success is True
    assert res.data["design_type"] == "youtube_thumbnail"
    assert res.data["width"] == 1280
    assert res.data["height"] == 720


@pytest.mark.asyncio
async def test_canva_controller_edit_existing_design(mock_browser_controller):
    controller = CanvaBrowserController(browser_controller=mock_browser_controller)

    design_id = "DAF12345ABC"
    res = await controller.edit_existing_design(design_url_or_id=design_id)

    assert res.success is True
    assert res.data["status"] == "editor_opened"
    mock_browser_controller.navigate.assert_called_with(
        url=f"https://www.canva.com/design/{design_id}/edit",
        timeout_ms=30000.0,
        workflow_id=None,
        task_id=None,
    )


@pytest.mark.asyncio
async def test_canva_controller_add_text_and_elements(mock_browser_controller):
    controller = CanvaBrowserController(browser_controller=mock_browser_controller)

    # Test add text
    text_res = await controller.add_text("Welcome to the Fest!", text_type="heading")
    assert text_res.success is True
    assert text_res.data["text"] == "Welcome to the Fest!"
    assert any(
        call.args and call.args[0] == "t"
        for call in mock_browser_controller._page.keyboard.press.call_args_list
    )

    # Test add shape element
    elem_res = await controller.add_element(shape="rectangle")
    assert elem_res.success is True
    assert elem_res.data["shape"] == "rectangle"
    mock_browser_controller._page.keyboard.press.assert_called_with("r")

    # Test change colors
    color_res = await controller.change_colors(palette=["#7D2AE8", "#00C4CC"])
    assert color_res.success is True
    assert color_res.data["palette"] == ["#7D2AE8", "#00C4CC"]

    # Test apply template
    tpl_res = await controller.apply_template("Minimalist Poster")
    assert tpl_res.success is True
    assert tpl_res.data["template_name"] == "Minimalist Poster"


@pytest.mark.asyncio
async def test_canva_controller_export_pdf_verified(mock_browser_controller):
    controller = CanvaBrowserController(browser_controller=mock_browser_controller)
    controller._active_design_info = {
        "title": "College Fest Poster",
        "topic": "College Fest",
        "dimensions": "1080 x 1920 px",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "test_design.pdf")
        res = await controller.export_design(export_format="pdf", output_path=out_pdf)

        assert res.success is True
        assert res.data["format"] == "pdf"
        assert res.data["verified"] is True
        assert os.path.exists(out_pdf)
        assert os.path.getsize(out_pdf) > 0

        # Verify PDF header bytes
        with open(out_pdf, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"
