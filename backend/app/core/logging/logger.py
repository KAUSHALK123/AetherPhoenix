"""Core logger implementation, handlers, setup and factory for AetherPhoenix."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.logging.formatter import JSONLogFormatter, TextLogFormatter
from app.core.logging.interface import ILogger


class StructuredLogger(ILogger):
    """
    Concrete structured logger implementation wrapping Python's standard logging.Logger.
    Supports context binding and structured metadata propagation.
    """

    def __init__(
        self,
        logger: logging.Logger,
        context: Optional[Dict[str, Any]] = None,
    ):
        self._logger = logger
        self._context: Dict[str, Any] = context.copy() if context else {}

    @property
    def name(self) -> str:
        """Returns the underlying logger name."""
        return self._logger.name

    @property
    def context(self) -> Dict[str, Any]:
        """Returns a copy of the logger's bound context."""
        return self._context.copy()

    def bind(self, **kwargs: Any) -> "StructuredLogger":
        """
        Create a new StructuredLogger instance with merged contextual variables.
        """
        new_context = self._context.copy()
        new_context.update(kwargs)
        return StructuredLogger(self._logger, context=new_context)

    def _prepare_extra(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Prepares the extra dict for LogRecord formatting."""
        extra = kwargs.pop("extra", {}).copy() if "extra" in kwargs else {}

        # Merge bound context and any extra kwargs passed to log call
        combined_context = self._context.copy()

        # Any additional non-reserved kwargs passed directly to log call
        # become part of context
        for key in list(kwargs.keys()):
            if key not in ("exc_info", "stack_info", "stacklevel"):
                combined_context[key] = kwargs.pop(key)

        extra["extra_context"] = combined_context
        return extra

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = self._prepare_extra(kwargs)
        self._logger.debug(msg, *args, extra=extra, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = self._prepare_extra(kwargs)
        self._logger.info(msg, *args, extra=extra, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = self._prepare_extra(kwargs)
        self._logger.warning(msg, *args, extra=extra, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = self._prepare_extra(kwargs)
        self._logger.error(msg, *args, extra=extra, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = self._prepare_extra(kwargs)
        self._logger.critical(msg, *args, extra=extra, **kwargs)

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        extra = self._prepare_extra(kwargs)
        self._logger.log(level, msg, *args, extra=extra, **kwargs)


def create_console_handler(
    json_format: bool = True,
) -> logging.StreamHandler:
    """Creates a console log handler writing to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = JSONLogFormatter() if json_format else TextLogFormatter()
    handler.setFormatter(formatter)
    return handler


def create_file_handler(
    log_dir: str = "logs",
    log_file: str = "aether_phoenix.log",
    json_format: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Handler:
    """Creates a rotating file log handler in the designated directory."""
    log_path = Path(log_dir)
    try:
        log_path.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to current directory if specified directory creation fails
        log_path = Path(".")

    filepath = log_path / log_file
    handler = RotatingFileHandler(
        filepath, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    formatter = JSONLogFormatter() if json_format else TextLogFormatter()
    handler.setFormatter(formatter)
    return handler


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    log_file: str = "aether_phoenix.log",
    json_format: bool = True,
    console_output: bool = True,
    file_output: bool = True,
) -> None:
    """
    Centralized initialization function for the AetherPhoenix logging framework.
    Configures root logger handlers, formatters, and log levels.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to prevent duplicated logs
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    if console_output:
        console_handler = create_console_handler(json_format=json_format)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)

    if file_output:
        file_handler = create_file_handler(
            log_dir=log_dir, log_file=log_file, json_format=json_format
        )
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)


def get_logger(name: str = "AetherPhoenix") -> StructuredLogger:
    """
    Factory function to retrieve a StructuredLogger instance.

    Args:
        name: Name of the logger (typically module __name__ or component name).

    Returns:
        StructuredLogger wrapping standard logging logger.
    """
    python_logger = logging.getLogger(name)
    return StructuredLogger(python_logger)
