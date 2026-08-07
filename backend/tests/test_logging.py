"""Unit tests for the AetherPhoenix centralized logging framework."""

import json
import logging
from pathlib import Path
import tempfile
import pytest

from backend.app.core.logging.formatter import JSONLogFormatter, TextLogFormatter
from backend.app.core.logging.interface import ILogger
from backend.app.core.logging.logger import (
    StructuredLogger,
    create_console_handler,
    create_file_handler,
    get_logger,
    setup_logging,
)


def test_interface_compliance():
    """Verify StructuredLogger implements ILogger interface."""
    python_logger = logging.getLogger("test_compliance")
    logger = StructuredLogger(python_logger)
    assert isinstance(logger, ILogger)


def test_logger_levels(caplog):
    """Test log generation across all severity levels."""
    test_logger = get_logger("test_levels")

    with caplog.at_level(logging.DEBUG):
        test_logger.debug("Debug msg")
        test_logger.info("Info msg")
        test_logger.warning("Warning msg")
        test_logger.warn("Warn alias msg")
        test_logger.error("Error msg")
        test_logger.critical("Critical msg")

    messages = [rec.message for rec in caplog.records]
    assert "Debug msg" in messages
    assert "Info msg" in messages
    assert "Warning msg" in messages
    assert "Warn alias msg" in messages
    assert "Error msg" in messages
    assert "Critical msg" in messages


def test_json_formatter():
    """Test JSONLogFormatter structured output."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message %s",
        args=("1",),
        exc_info=None,
    )
    record.funcName = "test_func"
    record.module = "test_module"
    record.extra_context = {"workflow_id": "wf_123", "agent_id": "agent_01"}

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["timestamp"] is not None
    assert data["level"] == "INFO"
    assert data["logger"] == "test_logger"
    assert data["message"] == "Test message 1"
    assert data["module"] == "test_module"
    assert data["function"] == "test_func"
    assert data["line"] == 10
    assert data["context"]["workflow_id"] == "wf_123"
    assert data["context"]["agent_id"] == "agent_01"


def test_text_formatter():
    """Test TextLogFormatter output."""
    formatter = TextLogFormatter()
    record = logging.LogRecord(
        name="test_text_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=25,
        msg="Sample warning",
        args=(),
        exc_info=None,
    )
    record.funcName = "test_func"
    record.module = "test_module"
    record.extra_context = {"task_id": "task_456"}

    formatted = formatter.format(record)
    assert "[WARNING]" in formatted
    assert "[test_text_logger]" in formatted
    assert "Sample warning" in formatted
    assert "task_id" in formatted


def test_logger_context_binding(caplog):
    """Test logger.bind() and propagation of contextual fields."""
    base_logger = get_logger("test_binding")
    bound_logger = base_logger.bind(session_id="sess_789", agent_name="worker")

    assert bound_logger.context == {"session_id": "sess_789", "agent_name": "worker"}
    assert base_logger.context == {}

    with caplog.at_level(logging.INFO):
        bound_logger.info("Executing bound action", step="step_1")

    record = caplog.records[-1]
    assert hasattr(record, "extra_context")
    assert record.extra_context["session_id"] == "sess_789"
    assert record.extra_context["agent_name"] == "worker"
    assert record.extra_context["step"] == "step_1"


def test_file_handler_output():
    """Test writing logs to a file output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_handler = create_file_handler(
            log_dir=tmpdir, log_file="test_out.log", json_format=True
        )
        test_py_logger = logging.getLogger("test_file_logger")
        test_py_logger.addHandler(file_handler)
        test_py_logger.setLevel(logging.INFO)

        s_logger = StructuredLogger(test_py_logger)
        s_logger.info("File logger test message", key="val")

        file_handler.flush()
        file_handler.close()

        log_file_path = Path(tmpdir) / "test_out.log"
        assert log_file_path.exists()

        content = log_file_path.read_text(encoding="utf-8")
        assert "File logger test message" in content
        data = json.loads(content.strip())
        assert data["message"] == "File logger test message"
        assert data["context"]["key"] == "val"


def test_setup_logging():
    """Test setup_logging helper configures root logger handlers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_logging(
            level="DEBUG",
            log_dir=tmpdir,
            log_file="app_setup.log",
            json_format=True,
            console_output=True,
            file_output=True,
        )

        root = logging.getLogger()
        assert len(root.handlers) == 2
        assert root.level == logging.DEBUG

        # Cleanup handlers to release file lock on Windows
        for handler in list(root.handlers):
            handler.close()
            root.removeHandler(handler)

