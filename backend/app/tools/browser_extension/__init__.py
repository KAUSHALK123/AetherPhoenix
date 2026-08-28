"""Browser Extension module for controlling active user browser."""

from app.tools.browser_extension.adapter import BrowserExtensionAdapter
from app.tools.browser_extension.connection_manager import (
    BrowserExtensionConnectionManager,
    get_connection_manager,
)
from app.tools.browser_extension.controller import BrowserExtensionController
from app.tools.browser_extension.interface import register_browser_extension_capability

__all__ = [
    "BrowserExtensionAdapter",
    "BrowserExtensionConnectionManager",
    "BrowserExtensionController",
    "get_connection_manager",
    "register_browser_extension_capability",
]
