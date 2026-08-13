from datetime import datetime, timezone
from typing import Optional

from shared.contracts.task import TaskStatus
from shared.contracts.workflow import ProgressState, SharedWorkflowState


class WorkflowProgressMonitor:
    """
    Component responsible for calculating real-time workflow progress metrics
    by consuming the SharedWorkflowState.
    """

    def calculate_progress(self, state: SharedWorkflowState) -> ProgressState:
        """
        Calculates and returns the ProgressState for the workflow.
        """
        tasks = state.tasks
        total_tasks = len(tasks)

        completed_tasks = 0
        running_tasks = 0
        failed_tasks = 0
        blocked_tasks = 0
        pending_tasks = 0

        for task in tasks.values():
            if task.status == TaskStatus.COMPLETED:
                completed_tasks += 1
            elif task.status == TaskStatus.RUNNING:
                running_tasks += 1
            elif task.status == TaskStatus.FAILED:
                failed_tasks += 1
            elif task.status == TaskStatus.BLOCKED:
                blocked_tasks += 1
            elif task.status in (
                TaskStatus.CREATED,
                TaskStatus.READY,
                TaskStatus.WAITING,
            ):
                pending_tasks += 1

        overall_percentage = 0.0
        if total_tasks > 0:
            overall_percentage = (completed_tasks / total_tasks) * 100.0

        execution_duration_seconds = self.calculate_duration(state)

        # Estimate remaining time if possible (simple heuristic)
        estimated_remaining_time_seconds: Optional[int] = None
        if completed_tasks > 0 and execution_duration_seconds > 0:
            avg_time_per_task = execution_duration_seconds / completed_tasks
            remaining_tasks = total_tasks - completed_tasks
            estimated_remaining_time_seconds = int(avg_time_per_task * remaining_tasks)

        return ProgressState(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            running_tasks=running_tasks,
            failed_tasks=failed_tasks,
            pending_tasks=pending_tasks,
            blocked_tasks=blocked_tasks,
            overall_percentage=overall_percentage,
            execution_duration_seconds=execution_duration_seconds,
            estimated_remaining_time_seconds=estimated_remaining_time_seconds,
        )

    def calculate_duration(self, state: SharedWorkflowState) -> float:
        """
        Calculates execution duration in seconds.
        """
        metadata = state.metadata
        if not metadata.started_at:
            return 0.0

        end_time = metadata.completed_at or datetime.now(timezone.utc)
        return max(0.0, (end_time - metadata.started_at).total_seconds())

    def update_progress_state(self, state: SharedWorkflowState) -> None:
        """
        Updates SWS progress in-place.
        """
        state.progress = self.calculate_progress(state)
