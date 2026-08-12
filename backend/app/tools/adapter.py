from abc import ABC, abstractmethod

from shared.contracts.execution import ExecutionResult
from shared.contracts.task import Task


class BaseToolAdapter(ABC):
    """
    Abstract base class for all Tool Adapters.

    A Tool Adapter bridges the gap between the Worker Agent and the actual
    executable tool (e.g., Browser, PowerShell, Python). It is responsible
    for executing a given Task and returning an ExecutionResult.
    """

    @abstractmethod
    async def execute(self, task: Task) -> ExecutionResult:
        """
        Executes a task using the underlying tool implementation.

        Args:
            task (Task): The atomic task to be executed.

        Returns:
            ExecutionResult: The structured result of the execution.
        """
        pass
