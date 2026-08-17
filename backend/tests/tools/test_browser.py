from unittest.mock import AsyncMock, patch

import pytest
from shared.contracts.permission import PermissionType

from app.engine.registry import CapabilityRegistry
from app.tools.browser import BrowserTool, register_browser_capability
from app.tools.registry import ToolRegistry


@pytest.fixture
def mock_permission_checker():
    def checker(permission: PermissionType) -> bool:
        return True

    return checker


def test_register_browser_capability():
    tool_reg = ToolRegistry()
    cap_reg = CapabilityRegistry()

    register_browser_capability(tool_reg, cap_reg)

    assert tool_reg.get("browser_automation") is not None
    assert cap_reg.get("web_searcher") is not None


@pytest.mark.asyncio
async def test_browser_initialization(mock_permission_checker):
    tool = BrowserTool(permission_checker=mock_permission_checker)

    with patch("app.tools.browser.controller.async_playwright") as mock_async_playwright:
        # Setup mocks
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()

        mock_async_playwright.return_value.start = AsyncMock(
            return_value=mock_playwright
        )
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Test start
        await tool.start_session()
        mock_async_playwright.return_value.start.assert_called_once()
        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_page.assert_called_once()

        # Test close
        await tool.close_session()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()


@pytest.mark.asyncio
async def test_browser_permission_denied():
    def deny_checker(permission: PermissionType) -> bool:
        return False

    tool = BrowserTool(permission_checker=deny_checker)
    with pytest.raises(
        PermissionError, match="Action denied: Missing BROWSER_ACCESS permission"
    ):
        await tool.start_session()


@pytest.mark.asyncio
async def test_browser_navigate(mock_permission_checker):
    tool = BrowserTool(permission_checker=mock_permission_checker)

    with patch("app.tools.browser.controller.async_playwright") as mock_async_playwright:
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_async_playwright.return_value.start = AsyncMock(
            return_value=mock_playwright
        )
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        await tool.start_session()

        # Test navigate
        result = await tool.navigate("https://example.com")
        assert result is True
        mock_page.goto.assert_called_once_with(
            "https://example.com", wait_until="domcontentloaded", timeout=30000.0
        )


@pytest.mark.asyncio
async def test_browser_extract_content(mock_permission_checker):
    tool = BrowserTool(permission_checker=mock_permission_checker)

    with patch("app.tools.browser.controller.async_playwright") as mock_async_playwright:
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_async_playwright.return_value.start = AsyncMock(
            return_value=mock_playwright
        )
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        mock_page.evaluate.return_value = "Test Content"

        await tool.start_session()

        content = await tool.extract_content()
        assert content == "Test Content"
        mock_page.evaluate.assert_called_once_with("document.body.innerText")


@pytest.mark.asyncio
async def test_browser_interact(mock_permission_checker):
    tool = BrowserTool(permission_checker=mock_permission_checker)

    with patch("app.tools.browser.controller.async_playwright") as mock_async_playwright:
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_async_playwright.return_value.start = AsyncMock(
            return_value=mock_playwright
        )
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        await tool.start_session()

        # Test click
        await tool.interact("#button", "click")
        mock_page.click.assert_called_once_with("#button", timeout=10000.0)

        # Test fill
        await tool.interact("#input", "fill", "text")
        mock_page.fill.assert_called_once_with("#input", "text", timeout=10000.0)
