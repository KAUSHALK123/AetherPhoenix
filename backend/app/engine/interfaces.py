from abc import ABC, abstractmethod
from typing import Optional

from shared.contracts.task import Task


class BaseWorkflowEngine(ABC):
    """Abstract interface for a Workflow Engine."""

    @abstractmethod
    def start(self) -> None:
        """Starts or resumes the workflow execution."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """Pauses the workflow execution."""
        pass

    @abstractmethod
    def cancel(self) -> None:
        """Cancels the workflow entirely."""
        pass

    @abstractmethod
    def enqueue(self, task: Task) -> None:
        """Enqueues a task for execution."""
        pass

    @abstractmethod
    def dequeue(self) -> Optional[Task]:
        """Retrieves the next pending task for execution."""
        pass
