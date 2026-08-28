import asyncio
import json
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import WebSocket
from shared.contracts.browser_extension import (
    BrowserExtensionCommand,
    BrowserExtensionResponse,
    ExtensionConnectionStatus,
)

from app.core.logging import get_logger

logger = get_logger(__name__)


class ExtensionNotConnectedError(Exception):
    """Raised when an operation is requested but no browser extension is connected."""

    pass


class BrowserExtensionConnectionManager:
    """
    Manages active WebSocket connections from the Chrome browser extension.
    Handles command dispatching, response mapping, and connection lifecycle.
    """

    _instance: Optional["BrowserExtensionConnectionManager"] = None

    def __init__(self):
        self._active_websocket: Optional[WebSocket] = None
        self._client_id: Optional[str] = None
        self._pending_commands: Dict[str, asyncio.Future[BrowserExtensionResponse]] = {}
        self._active_tab_url: Optional[str] = None
        self._active_tab_title: Optional[str] = None
        self._last_heartbeat: Optional[float] = None
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "BrowserExtensionConnectionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_connected(self) -> bool:
        return self._active_websocket is not None

    def get_status(self) -> ExtensionConnectionStatus:
        return ExtensionConnectionStatus(
            connected=self.is_connected,
            client_id=self._client_id,
            active_tab_url=self._active_tab_url,
            active_tab_title=self._active_tab_title,
            last_heartbeat=self._last_heartbeat,
        )

    async def connect(self, websocket: WebSocket) -> str:
        """Accepts a WebSocket connection from the browser extension."""
        await websocket.accept()
        async with self._lock:
            # If an existing connection exists, close it cleanly
            if self._active_websocket:
                try:
                    await self._active_websocket.close()
                except Exception:
                    pass

            self._client_id = str(uuid.uuid4())
            self._active_websocket = websocket
            self._last_heartbeat = time.time()
            logger.info(
                f"Browser Extension connected with client_id: {self._client_id}"
            )
            return self._client_id

    async def disconnect(self) -> None:
        """Cleans up when browser extension disconnects."""
        async with self._lock:
            self._active_websocket = None
            self._client_id = None
            logger.info("Browser Extension disconnected.")

            # Cancel any pending command futures
            for command_id, future in list(self._pending_commands.items()):
                if not future.done():
                    future.set_exception(
                        ExtensionNotConnectedError(
                            "Extension disconnected while command was executing"
                        )
                    )
            self._pending_commands.clear()

    async def handle_incoming_message(self, raw_data: str) -> None:
        """Processes incoming JSON messages from the connected extension."""
        self._last_heartbeat = time.time()
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as e:
            logger.warning(f"Malformed JSON message from extension: {e}")
            return

        msg_type = data.get("type")

        if msg_type == "heartbeat" or msg_type == "status_update":
            self._active_tab_url = data.get("active_tab_url", self._active_tab_url)
            self._active_tab_title = data.get(
                "active_tab_title", self._active_tab_title
            )
            return

        # Handle command responses
        command_id = data.get("command_id")
        if command_id and command_id in self._pending_commands:
            future = self._pending_commands.pop(command_id)
            if not future.done():
                response = BrowserExtensionResponse(
                    command_id=command_id,
                    success=data.get("success", False),
                    data=data.get("data"),
                    error=data.get("error"),
                    timestamp=time.time(),
                )
                future.set_result(response)

    async def send_command(
        self,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> BrowserExtensionResponse:
        """
        Dispatches a command to the connected Browser Extension over WebSocket
        and waits for the response up to timeout_seconds.
        """
        if not self._active_websocket:
            raise ExtensionNotConnectedError(
                "Browser Extension is not connected to AetherPhoenix"
            )

        command_id = str(uuid.uuid4())
        command = BrowserExtensionCommand(
            command_id=command_id,
            action=action,
            parameters=parameters or {},
            task_id=task_id,
            workflow_id=workflow_id,
            timestamp=time.time(),
        )

        loop = asyncio.get_event_loop()
        future: asyncio.Future[BrowserExtensionResponse] = loop.create_future()
        self._pending_commands[command_id] = future

        try:
            await self._active_websocket.send_text(command.model_dump_json())
            logger.debug(f"Dispatched command {command_id} ({action}) to extension")

            response = await asyncio.wait_for(future, timeout=timeout_seconds)
            return response
        except asyncio.TimeoutError:
            self._pending_commands.pop(command_id, None)
            logger.error(
                f"Command {command_id} ({action}) timed out after {timeout_seconds}s"
            )
            return BrowserExtensionResponse(
                command_id=command_id,
                success=False,
                error=f"Extension request timed out after {timeout_seconds} seconds",
                timestamp=time.time(),
            )
        except Exception as e:
            self._pending_commands.pop(command_id, None)
            logger.error(f"Error sending command {command_id} ({action}): {e}")
            return BrowserExtensionResponse(
                command_id=command_id,
                success=False,
                error=str(e),
                timestamp=time.time(),
            )


def get_connection_manager() -> BrowserExtensionConnectionManager:
    return BrowserExtensionConnectionManager.get_instance()
