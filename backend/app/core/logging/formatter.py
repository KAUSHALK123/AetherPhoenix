"""Log formatters for structured logging in AetherPhoenix."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict


class JSONLogFormatter(logging.Formatter):
    """
    Structured JSON log formatter for machine-readable logging.
    Encodes log entries as JSON objects containing timestamp, log level,
    logger name, message, location, contextual parameters, and stack trace info.
    """

    # Reserved attributes from standard logging.LogRecord to exclude from extra context
    RESERVED_ATTRS = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "extra_context",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Formats log record into a JSON string."""
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        log_data: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Gather extra contextual variables passed via extra or logger binding
        extra_context: Dict[str, Any] = {}
        if hasattr(record, "extra_context") and isinstance(record.extra_context, dict):
            extra_context.update(record.extra_context)

        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS:
                try:
                    # Ensure value is JSON serializable or string fallback
                    json.dumps(value)
                    extra_context[key] = value
                except (TypeError, OverflowError):
                    extra_context[key] = str(value)

        if extra_context:
            log_data["context"] = extra_context

        # Add exception details if present
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            log_data["exception"] = record.exc_text

        return json.dumps(log_data)


class TextLogFormatter(logging.Formatter):
    """
    Human-readable structured text log formatter.
    Formats logs into standard readable text output while retaining structured context.
    """

    RESERVED_ATTRS = JSONLogFormatter.RESERVED_ATTRS

    def format(self, record: logging.LogRecord) -> str:
        """Formats log record into a structured text string."""
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3]

        base_msg = (
            f"[{timestamp}] [{record.levelname}] [{record.name}] {record.getMessage()}"
        )

        extra_context: Dict[str, Any] = {}
        if hasattr(record, "extra_context") and isinstance(record.extra_context, dict):
            extra_context.update(record.extra_context)

        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS:
                extra_context[key] = value

        if extra_context:
            base_msg += f" | context={extra_context}"

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            base_msg += f"\n{record.exc_text}"

        return base_msg
