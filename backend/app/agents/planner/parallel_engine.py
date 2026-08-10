import logging
from typing import Dict, List
from uuid import UUID

from shared.contracts.task import Task

logger = logging.getLogger(__name__)


class ParallelTaskAnalyzer:
    """
    Engine responsible for identifying tasks that can execute in parallel
    based on their dependency requirements.
    """

    def analyze_parallel_groups(
        self, tasks: List[Task], dependency_graph: Dict[UUID, List[UUID]]
    ) -> List[List[UUID]]:
        """
        Calculates execution groups where tasks in the same group can run in parallel.
        Returns a list of parallel groups (lists of task UUIDs).
        """
        # If no tasks, return empty
        if not tasks:
            return []

        # Exclude non-executable phase tasks from parallel execution groups
        executable_tasks = [t for t in tasks if t.assigned_agent != "System"]
        task_ids = {t.task_id for t in executable_tasks}

        in_degree: Dict[UUID, int] = {t_id: 0 for t_id in task_ids}
        adj_list: Dict[UUID, List[UUID]] = {t_id: [] for t_id in task_ids}

        # Build adjacency list from dependencies and parent relationships
        for task in executable_tasks:
            all_deps = set(task.dependencies)
            if task.parent_task_id:
                all_deps.add(task.parent_task_id)
                
            for dep in all_deps:
                if dep in task_ids:
                    adj_list[dep].append(task.task_id)
                    in_degree[task.task_id] += 1

        raw_groups = []
        current_layer = [t_id for t_id, count in in_degree.items() if count == 0]

        while current_layer:
            raw_groups.append(current_layer)
            next_layer = []
            for node in current_layer:
                for neighbor in adj_list[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_layer.append(neighbor)
            current_layer = next_layer

        # A group is only "parallel" if it contains more than 1 task
        return [group for group in raw_groups if len(group) > 1]
