@pytest.mark.asyncio
async def test_browser_interact(mock_permission_checker):
    tool = BrowserTool(permission_checker=mock_permission_checker)

    with patch(
        "app.tools.browser.controller.async_playwright"
    ) as mock_async_playwright:
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = MagicMock()
        mock_locator = AsyncMock()
        mock_page.locator.return_value.first = mock_locator

        mock_async_playwright.return_value.start = AsyncMock(
            return_value=mock_playwright
        )
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        await tool.start_session()

        # Test click
        await tool.interact("#button", "click")
        mock_locator.click.assert_called_once()

        # Test fill
        await tool.interact("#input", "fill", "text")
        mock_locator.fill.assert_called_once_with("text", timeout=10000)
