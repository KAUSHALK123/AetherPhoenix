"""Centralized Logging Framework for AetherPhoenix."""

from backend.app.core.logging.formatter import JSONLogFormatter, TextLogFormatter
from backend.app.core.logging.interface import ILogger
from backend.app.core.logging.logger import (
    StructuredLogger,
    create_console_handler,
    create_file_handler,
    get_logger,
    setup_logging,
)

__all__ = [
    "ILogger",
    "StructuredLogger",
    "JSONLogFormatter",
    "TextLogFormatter",
    "create_console_handler",
    "create_file_handler",
    "get_logger",
    "setup_logging",
]
