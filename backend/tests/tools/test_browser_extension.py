import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from shared.contracts.browser_extension import (
    BrowserExtensionResponse,
)
from shared.contracts.task import Task, TaskCategory

from app.core.exceptions import PermissionDeniedException
from app.engine.registry import CapabilityRegistry
from app.tools.browser_extension import (
    BrowserExtensionAdapter,
    BrowserExtensionConnectionManager,
    BrowserExtensionController,
    register_browser_extension_capability,
)
from app.tools.registry import ToolRegistry


@pytest.fixture
def mock_permission_manager():
    pm = MagicMock()
    pm.check_permission.return_value = True
    return pm


@pytest.fixture
def connection_manager():
    # Fresh instance for testing
    mgr = BrowserExtensionConnectionManager()
    return mgr


def test_register_browser_extension_capability():
    tool_reg = ToolRegistry()
    cap_reg = CapabilityRegistry()
    mock_agent = MagicMock()

    register_browser_extension_capability(tool_reg, cap_reg, worker_agent=mock_agent)

    assert tool_reg.get("browser_extension") is not None
    assert cap_reg.get("web_extension_automation") is not None
    mock_agent.register_adapter.assert_called()


@pytest.mark.asyncio
async def test_connection_manager_connect_disconnect():
    mgr = BrowserExtensionConnectionManager()
    assert not mgr.is_connected

    mock_ws = AsyncMock()
    client_id = await mgr.connect(mock_ws)
    assert client_id is not None
    assert mgr.is_connected
    assert mgr.get_status().connected is True

    await mgr.disconnect()
    assert not mgr.is_connected
    assert mgr.get_status().connected is False


@pytest.mark.asyncio
async def test_connection_manager_send_command_success():
    mgr = BrowserExtensionConnectionManager()
    mock_ws = AsyncMock()
    await mgr.connect(mock_ws)

    # Background task to simulate extension response
    async def simulate_extension():
        await asyncio.sleep(0.05)
        # Verify message sent to websocket
        assert mock_ws.send_text.called
        sent_text = mock_ws.send_text.call_args[0][0]
        cmd_dict = json.loads(sent_text)
        cmd_id = cmd_dict["command_id"]

        response_payload = json.dumps(
            {
                "command_id": cmd_id,
                "success": True,
                "data": {"url": "https://example.com", "title": "Example Domain"},
            }
        )
        await mgr.handle_incoming_message(response_payload)

    task = asyncio.create_task(simulate_extension())
    resp = await mgr.send_command("detect_active_tab")
    await task

    assert resp.success is True
    assert resp.data["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_controller_detect_active_tab(mock_permission_manager):
    mgr = BrowserExtensionConnectionManager()
    controller = BrowserExtensionController(
        connection_manager=mgr, permission_manager=mock_permission_manager
    )

    with patch.object(mgr, "send_command", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = BrowserExtensionResponse(
            command_id="test_1",
            success=True,
            data={"url": "https://example.com", "title": "Example Page"},
            timestamp=time.time(),
        )

        res = await controller.detect_active_tab()
        assert res.success is True
        assert res.data["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_controller_navigate(mock_permission_manager):
    mgr = BrowserExtensionConnectionManager()
    controller = BrowserExtensionController(
        connection_manager=mgr, permission_manager=mock_permission_manager
    )

    with patch.object(mgr, "send_command", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = BrowserExtensionResponse(
            command_id="test_2",
            success=True,
            data={"url": "https://aetherphoenix.ai", "status": "navigating"},
            timestamp=time.time(),
        )

        res = await controller.navigate("https://aetherphoenix.ai")
        assert res.success is True
        assert res.data["url"] == "https://aetherphoenix.ai"


@pytest.mark.asyncio
async def test_controller_permission_denied():
    pm = MagicMock()
    pm.check_permission.return_value = False

    mgr = BrowserExtensionConnectionManager()
    controller = BrowserExtensionController(
        connection_manager=mgr, permission_manager=pm
    )

    with pytest.raises(PermissionDeniedException):
        await controller.navigate("https://sensitive.com")


@pytest.mark.asyncio
async def test_controller_credential_masking(mock_permission_manager):
    mgr = BrowserExtensionConnectionManager()
    controller = BrowserExtensionController(
        connection_manager=mgr, permission_manager=mock_permission_manager
    )

    with patch.object(mgr, "send_command", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = BrowserExtensionResponse(
            command_id="test_3",
            success=True,
            data={"selector": "#password", "action": "fill", "value": "secret123"},
            timestamp=time.time(),
        )

        # Call interact on password field
        res = await controller.interact(
            selector="#password", action="fill", value="secret123"
        )
        assert res.success is True
        # Output must be masked
        assert res.data["value"] == "[MASKED_CREDENTIAL]"


@pytest.mark.asyncio
async def test_adapter_execution(mock_permission_manager):
    mgr = BrowserExtensionConnectionManager()
    controller = BrowserExtensionController(
        connection_manager=mgr, permission_manager=mock_permission_manager
    )
    adapter = BrowserExtensionAdapter(controller=controller)

    with patch.object(
        controller, "extract_content", new_callable=AsyncMock
    ) as mock_extract:
        mock_extract.return_value = MagicMock(
            success=True, data={"content": "Extracted Page Text"}
        )

        from uuid import uuid4

        task = Task(
            task_id=uuid4(),
            workflow_id=uuid4(),
            task_name="Extract Page",
            description="Extract text content from active tab",
            expected_output="Text content",
            category=TaskCategory.BROWSER,
            required_tool="browser_extension",
            input_parameters={"action": "extract_content", "include_html": False},
        )

        exec_res = await adapter.execute(task)
        assert exec_res.success is True
        assert exec_res.output["content"] == "Extracted Page Text"
