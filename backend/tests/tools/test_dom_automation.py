from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.tools.browser.dom import (
    DOMAutomation,
    DOMElement,
    ElementNotFoundError,
    StaleElementError,
)


@pytest.fixture
def mock_page():
    page = MagicMock()
    return page


@pytest.fixture
def dom_automation(mock_page):
    return DOMAutomation(page=mock_page)


@pytest.mark.asyncio
async def test_inspect_element_success(dom_automation, mock_page):
    mock_locator = AsyncMock()
    mock_page.locator.return_value.first = mock_locator

    mock_locator.evaluate.return_value = {
        "tagName": "div",
        "text": "Hello World",
        "attributes": {"class": "test-class"},
    }
    mock_locator.is_visible.return_value = True
    mock_locator.is_enabled.return_value = True

    element = await dom_automation.inspect_element(".my-selector")

    assert isinstance(element, DOMElement)
    assert element.selector == ".my-selector"
    assert element.tag_name == "div"
    assert element.text == "Hello World"
    assert element.is_visible is True
    assert element.is_enabled is True
    assert element.attributes == {"class": "test-class"}
    mock_locator.wait_for.assert_called_once_with(state="attached", timeout=5000)


@pytest.mark.asyncio
async def test_inspect_element_timeout(dom_automation, mock_page):
    mock_locator = AsyncMock()
    mock_page.locator.return_value.first = mock_locator

    mock_locator.wait_for.side_effect = PlaywrightTimeoutError("Timeout")

    with pytest.raises(
        ElementNotFoundError, match="Element not found within 5000ms: .my-selector"
    ):
        await dom_automation.inspect_element(".my-selector")


@pytest.mark.asyncio
async def test_inspect_element_stale(dom_automation, mock_page):
    mock_locator = AsyncMock()
    mock_page.locator.return_value.first = mock_locator

    mock_locator.evaluate.side_effect = Exception("Node is detached from document")

    with pytest.raises(
        StaleElementError, match="Element became stale during inspection: .my-selector"
    ):
        await dom_automation.inspect_element(".my-selector")


@pytest.mark.asyncio
async def test_click_element_success(dom_automation, mock_page):
    mock_locator = AsyncMock()
    mock_page.locator.return_value.first = mock_locator

    await dom_automation.click_element(".btn")

    mock_locator.wait_for.assert_any_call(state="attached", timeout=5000)
    mock_locator.wait_for.assert_any_call(state="visible", timeout=5000)
    mock_locator.click.assert_called_once_with(timeout=5000)


@pytest.mark.asyncio
async def test_fill_element_success(dom_automation, mock_page):
    mock_locator = AsyncMock()
    mock_page.locator.return_value.first = mock_locator

    await dom_automation.fill_element(".input", "test text")

    mock_locator.wait_for.assert_any_call(state="attached", timeout=5000)
    mock_locator.wait_for.assert_any_call(state="visible", timeout=5000)
    mock_locator.fill.assert_called_once_with("test text", timeout=5000)


@pytest.mark.asyncio
async def test_extract_text_success(dom_automation, mock_page):
    mock_locator = AsyncMock()
    mock_page.locator.return_value.first = mock_locator
    mock_locator.inner_text.return_value = " extracted text "

    text = await dom_automation.extract_text(".text")

    assert text == "extracted text"


@pytest.mark.asyncio
async def test_invalid_selector(dom_automation):
    with pytest.raises(ValueError, match="Selector cannot be empty."):
        await dom_automation.click_element("")
