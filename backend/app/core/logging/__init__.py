"""Centralized Logging Framework for AetherPhoenix."""

from app.core.logging.formatter import JSONLogFormatter, TextLogFormatter
from app.core.logging.interface import ILogger
from app.core.logging.logger import (
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
