from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.engine.interfaces import BaseWorkflowEngine
from app.engine.queue import ExecutionQueue
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowStatus

logger = get_logger(__name__)


class WorkflowEngine(BaseWorkflowEngine):
    """
    Manages workflow state transitions and task queue operations
    by mutating the SharedWorkflowState.
    """

    def __init__(self, state: SharedWorkflowState):
        self.state = state
        self.queue = ExecutionQueue(self.state.execution_queue)

    def start(self) -> None:
        """Transitions workflow to RUNNING state."""
        current = self.state.metadata.status
        if current in (
            WorkflowStatus.CREATED,
            WorkflowStatus.PAUSED,
            WorkflowStatus.READY,
        ):
            self.state.metadata.status = WorkflowStatus.RUNNING
            w_id = self.state.metadata.workflow_id
            logger.info(f"Workflow {w_id} transitioned to RUNNING")
        else:
            raise ValueError(f"Cannot start workflow from status: {current}")

    def pause(self) -> None:
        """Transitions workflow to PAUSED state."""
        if self.state.metadata.status == WorkflowStatus.RUNNING:
            self.state.metadata.status = WorkflowStatus.PAUSED
            w_id = self.state.metadata.workflow_id
            logger.info(f"Workflow {w_id} transitioned to PAUSED")
        else:
            raise ValueError("Only RUNNING workflows can be paused")

    def cancel(self) -> None:
        """Transitions workflow to CANCELLED state."""
        self.state.metadata.status = WorkflowStatus.CANCELLED
        w_id = self.state.metadata.workflow_id
        logger.info(f"Workflow {w_id} transitioned to CANCELLED")

    def complete(self) -> None:
        """Transitions workflow to COMPLETED state."""
        self.state.metadata.status = WorkflowStatus.COMPLETED
        w_id = self.state.metadata.workflow_id
        logger.info(f"Workflow {w_id} transitioned to COMPLETED")

    def fail(self) -> None:
        """Transitions workflow to FAILED state."""
        self.state.metadata.status = WorkflowStatus.FAILED
        w_id = self.state.metadata.workflow_id
        logger.info(f"Workflow {w_id} transitioned to FAILED")

    def enqueue(self, task: Task) -> None:
        """Registers a task in the state and enqueues it for execution."""
        self.state.tasks[task.task_id] = task
        self.queue.enqueue(task.task_id)
        task.status = TaskStatus.WAITING
        logger.debug(f"Enqueued task {task.task_id}")

    def dequeue(self) -> Optional[Task]:
        """Pops the next task ID and retrieves the actual task."""
        task_id = self.queue.dequeue()
        if task_id:
            return self.state.tasks.get(task_id)
        return None

    def update_task_status(self, task_id: UUID, status: TaskStatus) -> None:
        """Updates task status and manages running/completed list references."""
        task = self.state.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found in workflow state.")

        task.status = status

        if status == TaskStatus.RUNNING:
            if task_id not in self.state.running_tasks:
                self.state.running_tasks.append(task_id)

        elif status == TaskStatus.COMPLETED:
            if task_id in self.state.running_tasks:
                self.state.running_tasks.remove(task_id)
            if task_id not in self.state.completed_tasks:
                self.state.completed_tasks.append(task_id)

        elif status == TaskStatus.FAILED:
            if task_id in self.state.running_tasks:
                self.state.running_tasks.remove(task_id)
            if task_id not in self.state.failed_tasks:
                self.state.failed_tasks.append(task_id)
