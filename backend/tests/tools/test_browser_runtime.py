from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from shared.contracts.browser import BrowserState

from app.core.exceptions import PermissionDeniedException
from app.tools.browser.controller import BrowserController
from app.tools.browser.dom import DOMAutomation, InteractiveElement
from app.tools.browser.interaction import ObserveActVerifyEngine
from app.tools.browser.mcp import MCPBrowserAdapter, MCPBrowserToolCatalog


@pytest.fixture
def mock_pm():
    pm = MagicMock()
    pm.check_permission.return_value = True
    return pm


@pytest.fixture
def browser_controller(mock_pm):
    return BrowserController(permission_manager=mock_pm)


# --- 1. Session Lifecycle & Reuse Tests ---


@pytest.mark.asyncio
async def test_session_lifecycle(browser_controller):
    with patch("app.tools.browser.controller.async_playwright") as mock_ap:
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_ap.return_value.start = AsyncMock(return_value=mock_pw)
        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.title.return_value = "Blank Page"
        mock_page.url = "about:blank"
        mock_page.screenshot.return_value = b"fake-jpeg"

        # Start Session
        res = await browser_controller.start_session(headless=True)
        assert res.success is True
        assert browser_controller.session is not None
        assert browser_controller.session.state == BrowserState.READY

        # Session Reuse
        reuse_res = await browser_controller.start_session(headless=True)
        assert reuse_res.success is True
        assert reuse_res.data["reused"] is True

        # Close Session
        close_res = await browser_controller.close_session()
        assert close_res.success is True
        assert browser_controller.session is None


# --- 2. Tab Management Tests ---


@pytest.mark.asyncio
async def test_tab_management(browser_controller):
    with patch("app.tools.browser.controller.async_playwright") as mock_ap:
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page1 = AsyncMock()
        mock_page2 = AsyncMock()

        mock_ap.return_value.start = AsyncMock(return_value=mock_pw)
        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.side_effect = [mock_page1, mock_page2]
        mock_page1.title.return_value = "Tab 1"
        mock_page1.url = "https://example.com"
        mock_page1.screenshot.return_value = b"frame1"

        mock_page2.title.return_value = "Tab 2"
        mock_page2.url = "https://canva.com"
        mock_page2.screenshot.return_value = b"frame2"

        await browser_controller.start_session()
        assert len(browser_controller._pages) == 1

        # Open second tab
        tab2_res = await browser_controller.new_tab("https://canva.com")
        assert tab2_res.success is True
        assert tab2_res.data["total_tabs"] == 2
        assert tab2_res.data["active_tab_index"] == 1

        # Switch back to tab 0
        switch_res = await browser_controller.switch_tab(0)
        assert switch_res.success is True
        assert switch_res.data["active_tab_index"] == 0

        # Close tab 1
        close_tab_res = await browser_controller.close_tab(1)
        assert close_tab_res.success is True
        assert close_tab_res.data["remaining_tabs"] == 1


# --- 3. Observe-Act-Verify Interaction Loop Tests ---


@pytest.mark.asyncio
async def test_observe_act_verify_loop_success():
    mock_page = AsyncMock()
    mock_page.url = "https://www.canva.com"
    mock_page.title.return_value = "Canva: Visual Suite for Everyone"

    engine = ObserveActVerifyEngine()

    # Mock DOM interactive elements
    mock_elements = [
        InteractiveElement(
            selector="button[data-testid='signup-button']",
            tag_name="button",
            text="Sign up",
            role="button",
            is_visible=True,
            is_enabled=True,
            attributes={"data-testid": "signup-button"},
        ),
        InteractiveElement(
            selector="input[name='search']",
            tag_name="input",
            text="",
            role="searchbox",
            is_visible=True,
            is_enabled=True,
            attributes={"placeholder": "Search templates", "name": "search"},
        ),
    ]

    with patch.object(
        DOMAutomation, "get_interactive_elements", return_value=mock_elements
    ), patch.object(
        DOMAutomation, "scroll_into_view", new_callable=AsyncMock
    ), patch.object(
        DOMAutomation, "click_element", new_callable=AsyncMock
    ), patch.object(
        DOMAutomation, "highlight_element", new_callable=AsyncMock
    ):
        success, result = await engine.execute_loop(
            page=mock_page,
            action="click",
            target="Sign up",
            expected_outcome="Navigates to signup",
        )

        assert success is True
        assert result["action"] == "click"
        assert result["target"] == "button[data-testid='signup-button']"
        assert (
            "verified" in result["details"].lower()
            or "click" in result["details"].lower()
        )


@pytest.mark.asyncio
async def test_observe_act_verify_fill():
    mock_page = AsyncMock()
    mock_page.url = "https://docs.python.org/3/"
    mock_page.title.return_value = "3.12 Documentation"

    mock_input_locator = AsyncMock()
    mock_input_locator.input_value.return_value = "asyncio"
    mock_page.locator.return_value = mock_input_locator

    engine = ObserveActVerifyEngine()
    mock_elements = [
        InteractiveElement(
            selector="input[name='q']",
            tag_name="input",
            text="",
            role="searchbox",
            is_visible=True,
            is_enabled=True,
            attributes={"placeholder": "Quick search", "name": "q"},
        )
    ]

    with patch.object(
        DOMAutomation, "get_interactive_elements", return_value=mock_elements
    ), patch.object(
        DOMAutomation, "scroll_into_view", new_callable=AsyncMock
    ), patch.object(
        DOMAutomation, "fill_element", new_callable=AsyncMock
    ), patch.object(
        DOMAutomation, "highlight_element", new_callable=AsyncMock
    ):
        success, result = await engine.execute_loop(
            page=mock_page,
            action="fill",
            target="Quick search",
            value="asyncio",
            expected_outcome="Field contains 'asyncio'",
        )

        assert success is True
        assert result["action"] == "fill"


# --- 4. Navigation & Error Reporting (Website Fails to Load) ---


@pytest.mark.asyncio
async def test_website_fails_to_load_reporting(browser_controller):
    with patch("app.tools.browser.controller.async_playwright") as mock_ap:
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_ap.return_value.start = AsyncMock(return_value=mock_pw)
        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_browser.new_page.return_value = mock_page

        # Simulate 404 response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.status_text = "Not Found"
        mock_page.goto.return_value = mock_response

        await browser_controller.start_session()
        res = await browser_controller.navigate(
            "https://broken-url-example.com/missing"
        )

        assert res.success is False
        assert "HTTP 404" in res.error


# --- 5. Security & Permission Tests ---


@pytest.mark.asyncio
async def test_permission_denied():
    denying_pm = MagicMock()
    denying_pm.check_permission.return_value = False

    controller = BrowserController(permission_manager=denying_pm)
    with pytest.raises(PermissionDeniedException):
        await controller.start_session()


@pytest.mark.asyncio
async def test_credential_masking(browser_controller):
    with patch("app.tools.browser.controller.async_playwright") as mock_ap:
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_ap.return_value.start = AsyncMock(return_value=mock_pw)
        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.screenshot.return_value = b"screenshot"

        await browser_controller.start_session()

        with patch.object(
            DOMAutomation, "fill_element", new_callable=AsyncMock
        ), patch.object(DOMAutomation, "highlight_element", new_callable=AsyncMock):
            res = await browser_controller.interact(
                selector="input#password", action="fill", value="SuperSecret123!"
            )
            assert res.success is True
            # Credential must be masked in returned output
            assert res.data["value"] == "[MASKED_CREDENTIAL]"


# --- 6. MCP Browser Adapter Tests ---


@pytest.mark.asyncio
async def test_mcp_browser_tools(browser_controller):
    adapter = MCPBrowserAdapter(controller=browser_controller)

    # 1. Catalog discovery
    tools = MCPBrowserToolCatalog.get_tools()
    tool_names = [t["name"] for t in tools]
    assert "browser_navigate" in tool_names
    assert "browser_click" in tool_names
    assert "browser_fill" in tool_names
    assert "browser_observe" in tool_names
    assert "browser_screenshot" in tool_names

    # 2. Status check
    status = adapter.check_connection()
    assert status["connected"] is True
    assert status["tools_count"] == len(tools)

    # 3. Tool execution with mock
    with patch.object(
        browser_controller, "navigate", new_callable=AsyncMock
    ) as mock_nav:
        mock_nav.return_value = MagicMock(
            success=True, data={"url": "https://www.canva.com", "title": "Canva"}
        )
        res = await adapter.execute_tool(
            "browser_navigate", {"url": "https://www.canva.com"}
        )
        assert res["isError"] is False
        assert "Successfully navigated" in res["content"][0]["text"]
