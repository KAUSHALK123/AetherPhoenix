import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import UUID

from shared.contracts.execution import ExecutionResult, TaskError
from shared.contracts.task import Task, TaskCategory, TaskStatus
from shared.contracts.task_history import TaskHistoryRecord, WorkflowHistoryRecord

logger = logging.getLogger(__name__)


class TaskHistoryService:
    """
    Service responsible for recording, tracking, retrieving, and filtering
    historical execution records of workflows and individual tasks.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        # Storage indexed by workflow_id
        self._workflows: dict[UUID, WorkflowHistoryRecord] = {}
        # Storage indexed by task_id -> list of TaskHistoryRecords
        self._task_records: dict[UUID, list[TaskHistoryRecord]] = {}

        # Task registry to look up task metadata by task_id
        self._task_registry: dict[UUID, Task] = {}

    def _to_uuid(self, val: UUID | str) -> UUID:
        """Utility method to safely coerce string or UUID into UUID."""
        if isinstance(val, UUID):
            return val
        return UUID(str(val))

    def record_task_created(
        self,
        task: Task,
        metadata: dict[str, Any] | None = None,
    ) -> TaskHistoryRecord:
        """
        Records the creation of a task and registers it under its parent workflow.
        """
        with self._lock:
            task_id = task.task_id
            workflow_id = task.workflow_id
            self._task_registry[task_id] = task.model_copy(deep=True)

            record = TaskHistoryRecord(
                task_id=task_id,
                workflow_id=workflow_id,
                parent_task_id=task.parent_task_id,
                task_name=task.task_name,
                task_category=task.category,
                assigned_agent=task.assigned_agent,
                required_tool=task.required_tool,
                status=TaskStatus.CREATED,
                retry_count=task.retry_count,
                attempt_number=1,
                inputs={},
                outputs={},
                created_at=task.created_at or datetime.now(timezone.utc),
                metadata=metadata or {},
            )

            if task_id not in self._task_records:
                self._task_records[task_id] = []
            self._task_records[task_id].append(record)

            # Ensure workflow entry exists
            if workflow_id not in self._workflows:
                self._workflows[workflow_id] = WorkflowHistoryRecord(
                    workflow_id=workflow_id,
                    goal="",
                    status="CREATED",
                    total_tasks=1,
                    tasks_history=[record],
                    created_at=datetime.now(timezone.utc),
                )
            else:
                wf = self._workflows[workflow_id]
                wf.total_tasks = len(
                    {
                        rec.task_id
                        for recs in self._task_records.values()
                        for rec in recs
                        if rec.workflow_id == workflow_id
                    }
                )
                wf.tasks_history.append(record)

            logger.info(
                f"TaskHistoryService recorded creation for task {task_id} "
                f"(Workflow: {workflow_id}, Name: '{task.task_name}')"
            )
            return record

    def record_task_started(
        self,
        task: Task,
        agent_name: str = "WorkerAgent",
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskHistoryRecord:
        """
        Records when a task execution is started by an agent.
        """
        with self._lock:
            task_id = task.task_id
            workflow_id = task.workflow_id
            self._task_registry[task_id] = task.model_copy(deep=True)

            attempt_number = task.retry_count + 1
            start_time = datetime.now(timezone.utc)

            record = TaskHistoryRecord(
                task_id=task_id,
                workflow_id=workflow_id,
                parent_task_id=task.parent_task_id,
                task_name=task.task_name,
                task_category=task.category,
                assigned_agent=agent_name,
                required_tool=task.required_tool,
                status=TaskStatus.RUNNING,
                retry_count=task.retry_count,
                attempt_number=attempt_number,
                inputs=inputs or {},
                outputs={},
                created_at=task.created_at or start_time,
                started_at=start_time,
                metadata=metadata or {},
            )

            if task_id not in self._task_records:
                self._task_records[task_id] = []
            self._task_records[task_id].append(record)

            if workflow_id in self._workflows:
                self._workflows[workflow_id].tasks_history.append(record)
                if self._workflows[workflow_id].started_at is None:
                    self._workflows[workflow_id].started_at = start_time
                self._workflows[workflow_id].status = "RUNNING"

            logger.info(
                f"TaskHistoryService recorded execution start for task {task_id} "
                f"(Agent: {agent_name}, Attempt #{attempt_number})"
            )
            return record

    def record_task_completed(
        self,
        task_id: UUID | str,
        result: ExecutionResult,
        metadata: dict[str, Any] | None = None,
    ) -> TaskHistoryRecord:
        """
        Records successful task execution outcome with metrics and outputs.
        """
        t_id = self._to_uuid(task_id)
        with self._lock:
            existing_records = self._task_records.get(t_id, [])
            last_record = existing_records[-1] if existing_records else None

            workflow_id = result.workflow_id
            task_name = last_record.task_name if last_record else "Task"
            category = last_record.task_category if last_record else TaskCategory.OTHER
            agent_name = last_record.assigned_agent if last_record else "WorkerAgent"
            req_tool = last_record.required_tool if last_record else None
            attempt = last_record.attempt_number if last_record else 1
            started = last_record.started_at if last_record else None

            now = datetime.now(timezone.utc)
            duration_ms = result.metrics.execution_time_ms

            record = TaskHistoryRecord(
                task_id=t_id,
                workflow_id=workflow_id,
                parent_task_id=last_record.parent_task_id if last_record else None,
                task_name=task_name,
                task_category=category,
                assigned_agent=agent_name,
                required_tool=req_tool,
                status=TaskStatus.COMPLETED,
                retry_count=last_record.retry_count if last_record else 0,
                attempt_number=attempt,
                inputs=last_record.inputs if last_record else {},
                outputs=result.output or {},
                error=None,
                execution_time_ms=duration_ms,
                created_at=last_record.created_at if last_record else now,
                started_at=started,
                completed_at=now,
                metadata=metadata or {},
            )

            if t_id not in self._task_records:
                self._task_records[t_id] = []
            self._task_records[t_id].append(record)

            if workflow_id in self._workflows:
                wf = self._workflows[workflow_id]
                wf.tasks_history.append(record)
                wf.completed_tasks = len(
                    {
                        rec.task_id
                        for recs in self._task_records.values()
                        for rec in recs
                        if rec.workflow_id == workflow_id
                        and rec.status == TaskStatus.COMPLETED
                    }
                )

            logger.info(
                f"TaskHistoryService recorded completion for task {t_id} "
                f"(Duration: {duration_ms:.2f}ms)"
            )
            return record

    def record_task_failed(
        self,
        task_id: UUID | str,
        error: TaskError | Exception | str,
        metadata: dict[str, Any] | None = None,
    ) -> TaskHistoryRecord:
        """
        Records a failed task execution with details of the failure error.
        """
        t_id = self._to_uuid(task_id)
        with self._lock:
            existing_records = self._task_records.get(t_id, [])
            last_record = existing_records[-1] if existing_records else None

            workflow_id = last_record.workflow_id if last_record else UUID(int=0)
            task_name = last_record.task_name if last_record else "Task"
            category = last_record.task_category if last_record else TaskCategory.OTHER
            agent_name = last_record.assigned_agent if last_record else "WorkerAgent"
            req_tool = last_record.required_tool if last_record else None
            attempt = last_record.attempt_number if last_record else 1
            started = last_record.started_at if last_record else None

            now = datetime.now(timezone.utc)
            duration_ms = 0.0
            if started:
                duration_ms = (now - started).total_seconds() * 1000.0

            if isinstance(error, TaskError):
                task_err = error
            elif isinstance(error, Exception):
                task_err = TaskError(
                    error_code=getattr(error, "code", "EXECUTION_FAILED"),
                    error_message=str(error),
                )
            else:
                task_err = TaskError(
                    error_code="EXECUTION_FAILED",
                    error_message=str(error),
                )

            record = TaskHistoryRecord(
                task_id=t_id,
                workflow_id=workflow_id,
                parent_task_id=last_record.parent_task_id if last_record else None,
                task_name=task_name,
                task_category=category,
                assigned_agent=agent_name,
                required_tool=req_tool,
                status=TaskStatus.FAILED,
                retry_count=last_record.retry_count if last_record else 0,
                attempt_number=attempt,
                inputs=last_record.inputs if last_record else {},
                outputs={},
                error=task_err,
                execution_time_ms=duration_ms,
                created_at=last_record.created_at if last_record else now,
                started_at=started,
                completed_at=now,
                metadata=metadata or {},
            )

            if t_id not in self._task_records:
                self._task_records[t_id] = []
            self._task_records[t_id].append(record)

            if workflow_id in self._workflows:
                wf = self._workflows[workflow_id]
                wf.tasks_history.append(record)
                wf.failed_tasks = len(
                    {
                        rec.task_id
                        for recs in self._task_records.values()
                        for rec in recs
                        if rec.workflow_id == workflow_id
                        and rec.status == TaskStatus.FAILED
                    }
                )

            logger.warning(
                f"TaskHistoryService recorded failure for task {t_id}: "
                f"[{task_err.error_code}] {task_err.error_message}"
            )
            return record

    def record_retry_attempt(
        self,
        task_id: UUID | str,
        attempt_number: int,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskHistoryRecord:
        """
        Records a retry attempt decision for a task.
        """
        t_id = self._to_uuid(task_id)
        with self._lock:
            existing_records = self._task_records.get(t_id, [])
            last_record = existing_records[-1] if existing_records else None

            workflow_id = last_record.workflow_id if last_record else UUID(int=0)
            task_name = last_record.task_name if last_record else "Task"
            category = last_record.task_category if last_record else TaskCategory.OTHER
            agent_name = (
                last_record.assigned_agent if last_record else "SupervisorAgent"
            )
            req_tool = last_record.required_tool if last_record else None
            now = datetime.now(timezone.utc)

            record_meta = metadata or {}
            if reason:
                record_meta["retry_reason"] = reason

            record = TaskHistoryRecord(
                task_id=t_id,
                workflow_id=workflow_id,
                parent_task_id=last_record.parent_task_id if last_record else None,
                task_name=task_name,
                task_category=category,
                assigned_agent=agent_name,
                required_tool=req_tool,
                status=TaskStatus.HEALING,
                retry_count=attempt_number - 1,
                attempt_number=attempt_number,
                inputs=last_record.inputs if last_record else {},
                outputs={},
                created_at=last_record.created_at if last_record else now,
                started_at=now,
                metadata=record_meta,
            )

            if t_id not in self._task_records:
                self._task_records[t_id] = []
            self._task_records[t_id].append(record)

            if workflow_id in self._workflows:
                self._workflows[workflow_id].tasks_history.append(record)

            logger.info(
                f"TaskHistoryService recorded retry #{attempt_number} for task {t_id}"
            )

            return record

    def record_workflow_status(
        self,
        workflow_id: UUID | str,
        goal: str = "",
        status: str = "RUNNING",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowHistoryRecord:
        """
        Records or updates top-level workflow history record.
        """
        wf_id = self._to_uuid(workflow_id)
        with self._lock:
            now = datetime.now(timezone.utc)
            if wf_id in self._workflows:
                wf = self._workflows[wf_id]
                wf.status = status
                if goal:
                    wf.goal = goal
                if metadata:
                    wf.metadata.update(metadata)
                if status in ("COMPLETED", "FAILED", "CANCELLED"):
                    wf.completed_at = now
                return wf
            else:
                wf = WorkflowHistoryRecord(
                    workflow_id=wf_id,
                    goal=goal,
                    status=status,
                    created_at=now,
                    metadata=metadata or {},
                )
                self._workflows[wf_id] = wf
                return wf

    def get_task_history(self, task_id: UUID | str) -> list[TaskHistoryRecord]:
        """
        Retrieves all historical execution records for a specific task ID.
        """
        t_id = self._to_uuid(task_id)
        with self._lock:
            return list(self._task_records.get(t_id, []))

    def get_workflow_history(
        self, workflow_id: UUID | str
    ) -> WorkflowHistoryRecord | None:
        """
        Retrieves the top-level WorkflowHistoryRecord for a given workflow ID.
        """
        wf_id = self._to_uuid(workflow_id)
        with self._lock:
            wf = self._workflows.get(wf_id)
            if wf:
                return wf.model_copy(deep=True)
            return None

    def get_workflow_task_records(
        self, workflow_id: UUID | str
    ) -> list[TaskHistoryRecord]:
        """
        Retrieves all task history records belonging to a workflow ID.
        """
        wf_id = self._to_uuid(workflow_id)
        with self._lock:
            return [
                rec
                for recs in self._task_records.values()
                for rec in recs
                if rec.workflow_id == wf_id
            ]

    def filter_history(
        self,
        workflow_id: UUID | str | None = None,
        status: TaskStatus | str | None = None,
        agent_name: str | None = None,
        category: TaskCategory | str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[TaskHistoryRecord]:
        """
        Queries and filters task history records across all executions.
        """
        wf_id = self._to_uuid(workflow_id) if workflow_id else None
        target_status = status.value if isinstance(status, TaskStatus) else status
        target_cat = category.value if isinstance(category, TaskCategory) else category

        with self._lock:
            all_records: list[TaskHistoryRecord] = [
                rec for recs in self._task_records.values() for rec in recs
            ]

            filtered: list[TaskHistoryRecord] = []
            for rec in all_records:
                if wf_id and rec.workflow_id != wf_id:
                    continue

                if target_status:
                    rec_status = (
                        rec.status.value
                        if isinstance(rec.status, TaskStatus)
                        else str(rec.status)
                    )
                    if rec_status != str(target_status):
                        continue

                if agent_name and rec.assigned_agent != agent_name:
                    continue

                if target_cat:
                    rec_cat = (
                        rec.task_category.value
                        if isinstance(rec.task_category, TaskCategory)
                        else str(rec.task_category)
                    )
                    if rec_cat != str(target_cat):
                        continue

                rec_time = rec.created_at
                if start_time and rec_time < start_time:
                    continue
                if end_time and rec_time > end_time:
                    continue

                filtered.append(rec)

            # Sort chronologically
            filtered.sort(key=lambda r: r.created_at)

            if limit and limit > 0:
                filtered = filtered[:limit]

            return filtered

    def clear_history(self) -> None:
        """Clears all stored historical records."""
        with self._lock:
            self._workflows.clear()
            self._task_records.clear()
            self._task_registry.clear()
            logger.info("TaskHistoryService history cleared.")


_task_history_service_instance: TaskHistoryService | None = None


def get_task_history_service() -> TaskHistoryService:
    """
    Returns global singleton TaskHistoryService instance.
    """
    global _task_history_service_instance
    if _task_history_service_instance is None:
        _task_history_service_instance = TaskHistoryService()
    return _task_history_service_instance


def reset_task_history_service() -> TaskHistoryService:
    """
    Resets and returns a clean global TaskHistoryService instance.
    """
    global _task_history_service_instance
    _task_history_service_instance = TaskHistoryService()
    return _task_history_service_instance
