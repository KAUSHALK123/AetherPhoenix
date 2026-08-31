"""Interface definition for the AetherPhoenix logging framework."""

from abc import ABC, abstractmethod
from typing import Any


class ILogger(ABC):
    """
    Abstract interface for centralized logging across all runtime components,
    services, and AI agents.
    """

    @abstractmethod
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug level message."""
        pass

    @abstractmethod
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info level message."""
        pass

    @abstractmethod
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning level message."""
        pass

    def warn(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Alias for warning."""
        self.warning(msg, *args, **kwargs)

    @abstractmethod
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error level message."""
        pass

    @abstractmethod
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical level message."""
        pass

    @abstractmethod
    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message with a custom integer log level."""
        pass

    @abstractmethod
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error level message with exception traceback."""
        pass

    @abstractmethod
    def bind(self, **kwargs: Any) -> "ILogger":
        """
        Return a new logger instance with contextual key-value pairs bound to it
        (e.g., agent_id, workflow_id, task_id, session_id).
        """
        pass
