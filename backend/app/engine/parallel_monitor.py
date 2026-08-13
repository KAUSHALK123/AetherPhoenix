from typing import List, Optional
from uuid import UUID

from shared.contracts.task import TaskStatus
from shared.contracts.workflow import SharedWorkflowState


class ParallelTaskMonitor:
    """
    Observer component responsible for tracking and validating executions of
    parallel execution groups and task dependency graphs.
    """

    def get_parallel_group(
        self, task_id: UUID, state: SharedWorkflowState
    ) -> Optional[List[UUID]]:
        """
        Retrieves the parallel group containing the given task_id.
        """
        if not state.planner_output or not state.planner_output.parallel_groups:
            return None

        for group in state.planner_output.parallel_groups:
            if task_id in group:
                return group
        return None

    def get_group_status(self, group: List[UUID], state: SharedWorkflowState) -> str:
        """
        Returns the overall status of the parallel execution group:
        - "COMPLETED": if all tasks in the group are COMPLETED.
        - "FAILED": if any task in the group is FAILED or BLOCKED.
        - "RUNNING": if any task is RUNNING, or if there is a mix of states.
        - "PENDING": if all tasks are CREATED, READY, or WAITING.
        """
        statuses = []
        for task_id in group:
            task = state.tasks.get(task_id)
            if task:
                statuses.append(task.status)
            else:
                statuses.append(TaskStatus.CREATED)

        if any(s in (TaskStatus.FAILED, TaskStatus.BLOCKED) for s in statuses):
            return "FAILED"

        if all(s == TaskStatus.COMPLETED for s in statuses):
            return "COMPLETED"

        if any(s == TaskStatus.RUNNING for s in statuses) or any(
            s == TaskStatus.COMPLETED for s in statuses
        ):
            return "RUNNING"

        return "PENDING"

    def check_prerequisites(self, task_id: UUID, state: SharedWorkflowState) -> str:
        """
        Validates the dependencies of task_id.
        - "READY": if all prerequisite tasks are COMPLETED.
        - "BLOCKED": if any prerequisite task is FAILED or BLOCKED.
        - "PENDING": if prerequisites are still RUNNING or waiting to start.
        """
        if not state.planner_output or not state.planner_output.dependency_graph:
            return "READY"

        prerequisites = state.planner_output.dependency_graph.get(task_id, [])
        if not prerequisites:
            return "READY"

        has_blocked_or_failed = False
        has_pending_or_running = False

        for prereq_id in prerequisites:
            prereq_task = state.tasks.get(prereq_id)
            if not prereq_task:
                has_pending_or_running = True
                continue

            if prereq_task.status in (TaskStatus.FAILED, TaskStatus.BLOCKED):
                has_blocked_or_failed = True
            elif prereq_task.status != TaskStatus.COMPLETED:
                has_pending_or_running = True

        if has_blocked_or_failed:
            return "BLOCKED"
        if has_pending_or_running:
            return "PENDING"

        return "READY"
