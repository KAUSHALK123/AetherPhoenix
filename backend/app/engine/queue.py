from typing import List, Optional
from uuid import UUID


class ExecutionQueue:
    """
    Provides robust queue operations over the SharedWorkflowState's execution_queue.
    """

    def __init__(self, queue_ref: List[UUID]):
        self._queue = queue_ref

    def enqueue(self, task_id: UUID) -> None:
        """Adds a task ID to the end of the queue if it doesn't already exist."""
        if task_id not in self._queue:
            self._queue.append(task_id)

    def dequeue(self) -> Optional[UUID]:
        """Removes and returns the first task ID in the queue."""
        if self._queue:
            return self._queue.pop(0)
        return None

    def peek(self) -> Optional[UUID]:
        """Returns the first task ID without removing it."""
        if self._queue:
            return self._queue[0]
        return None

    def is_empty(self) -> bool:
        """Returns True if the queue is empty."""
        return len(self._queue) == 0

    def size(self) -> int:
        """Returns the number of items in the queue."""
        return len(self._queue)
