import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionResult,
    TaskError,
    WorkerReexecutionRequest,
    WorkerReexecutionResult,
)
from shared.contracts.task import Task
from shared.contracts.workflow import SharedWorkflowState

from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus

logger = logging.getLogger(__name__)


class WorkerReexecutionManager:
    """
    Service responsible for formulating re-execution requests,
    managing task attempt history, revalidating permissions, and
    dispatching controlled re-execution requests through WorkerAgent.
    """

    def create_reexecution_request(
        self,
        task: Task,
        recovery_plan: Optional[Any] = None,
        state: Optional[SharedWorkflowState] = None,
    ) -> WorkerReexecutionRequest:
        """
        Formulates an authorized WorkerReexecutionRequest for a task under recovery.
        Preserves original task ID, snapshots previous attempt history,
        and generates a new attempt ID.
        """
        if not task:
            raise ValueError("Task is required to create a re-execution request.")

        # 1. Snapshot previous execution attempt history
        previous_attempt_number = len(task.attempt_history)
        attempt_number = previous_attempt_number + 1

        snapshot = {
            "attempt_id": (
                str(task.current_attempt_id)
                if task.current_attempt_id
                else str(uuid4())
            ),
            "attempt_number": previous_attempt_number,
            "status": (
                task.status.value if hasattr(task.status, "value") else str(task.status)
            ),
            "required_tool": task.required_tool,
            "execution_logs": list(task.execution_logs),
            "artifacts_produced": list(task.artifacts_produced),
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
        }
        task.attempt_history.append(snapshot)

        # 2. Generate new unique attempt ID and set current attempt context
        new_attempt_id = uuid4()
        task.current_attempt_id = new_attempt_id

        # 3. Extract recovery modifications if provided
        recovery_plan_id = recovery_plan.plan_id if recovery_plan else None
        recovery_strategy = (
            recovery_plan.strategy.value
            if recovery_plan and hasattr(recovery_plan.strategy, "value")
            else (str(recovery_plan.strategy) if recovery_plan else None)
        )
        modified_params: Dict[str, Any] = {}

        if recovery_plan and getattr(recovery_plan, "replacement_tasks", None):
            # If an alternative tool replacement task was generated,
            # update current task tool if matching
            rep_task = recovery_plan.replacement_tasks[0]
            if rep_task.required_tool and rep_task.required_tool != task.required_tool:
                modified_params["previous_tool"] = task.required_tool
                task.required_tool = rep_task.required_tool
                modified_params["updated_tool"] = task.required_tool

        logger.info(
            f"Created WorkerReexecutionRequest for task {task.task_id} "
            f"(Attempt #{attempt_number}, Attempt ID: {new_attempt_id})"
        )

        return WorkerReexecutionRequest(
            attempt_id=new_attempt_id,
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            attempt_number=attempt_number,
            recovery_plan_id=recovery_plan_id,
            recovery_strategy=recovery_strategy,
            modified_parameters=modified_params,
            original_task_snapshot=snapshot,
        )

    async def process_reexecution(
        self,
        request: WorkerReexecutionRequest,
        worker_agent: WorkerAgent,
        state: SharedWorkflowState,
        event_bus: Optional[EventBus] = None,
    ) -> WorkerReexecutionResult:
        """
        Dispatches a controlled re-execution request through WorkerAgent,
        revalidating permissions, capturing results, and emitting events.
        """
        logger.info(
            f"WorkerReexecutionManager processing re-execution for task "
            f"{request.task_id} (Attempt #{request.attempt_number}, "
            f"Attempt ID: {request.attempt_id})"
        )

        task = state.tasks.get(request.task_id)
        if not task:
            err_msg = f"Task {request.task_id} not found in SharedWorkflowState."
            logger.error(err_msg)
            return WorkerReexecutionResult(
                attempt_id=request.attempt_id,
                task_id=request.task_id,
                workflow_id=request.workflow_id,
                attempt_number=request.attempt_number,
                execution_result=ExecutionResult(
                    task_id=request.task_id,
                    workflow_id=request.workflow_id,
                    success=False,
                    error=TaskError(
                        error_code="INVALID_REEXECUTION_REQUEST",
                        error_message=err_msg,
                    ),
                ),
            )

        # Emit WORKER_REEXECUTION_STARTED event
        if event_bus:
            await event_bus.publish(
                RuntimeEvent(
                    workflow_id=request.workflow_id,
                    task_id=request.task_id,
                    event_type=EventType.WORKER_REEXECUTION_STARTED,
                    source_component=EventSource.WORKER,
                    payload={
                        "attempt_id": str(request.attempt_id),
                        "attempt_number": request.attempt_number,
                        "recovery_strategy": request.recovery_strategy,
                    },
                )
            )

        # Extract previous attempt IDs from task.attempt_history
        previous_ids: List[UUID] = []
        for att in task.attempt_history:
            att_id_str = att.get("attempt_id")
            if att_id_str:
                try:
                    previous_ids.append(UUID(att_id_str))
                except ValueError:
                    pass

        try:
            # Delegate execution through WorkerAgent using execution infrastructure
            exec_result = await worker_agent.execute(task)

            success = exec_result.success
            final_event = (
                EventType.WORKER_REEXECUTION_COMPLETED
                if success
                else EventType.WORKER_REEXECUTION_FAILED
            )

            # Emit completion or failure event
            if event_bus:
                await event_bus.publish(
                    RuntimeEvent(
                        workflow_id=request.workflow_id,
                        task_id=request.task_id,
                        event_type=final_event,
                        source_component=EventSource.WORKER,
                        payload={
                            "attempt_id": str(request.attempt_id),
                            "attempt_number": request.attempt_number,
                            "success": success,
                            "error_code": (
                                exec_result.error.error_code
                                if exec_result.error
                                else None
                            ),
                        },
                    )
                )

            reexec_result = WorkerReexecutionResult(
                attempt_id=request.attempt_id,
                task_id=request.task_id,
                workflow_id=request.workflow_id,
                attempt_number=request.attempt_number,
                execution_result=exec_result,
                previous_attempt_ids=previous_ids,
            )

            logger.info(
                f"WorkerReexecutionManager completed re-execution for task "
                f"{request.task_id}: success={success}"
            )
            return reexec_result

        except Exception as e:
            logger.exception(
                f"WorkerReexecutionManager exception during re-execution of "
                f"task {request.task_id}: {e}"
            )
            failure_result = ExecutionResult(
                task_id=request.task_id,
                workflow_id=request.workflow_id,
                success=False,
                error=TaskError(
                    error_code="REEXECUTION_FAILED",
                    error_message=str(e),
                ),
            )

            if event_bus:
                await event_bus.publish(
                    RuntimeEvent(
                        workflow_id=request.workflow_id,
                        task_id=request.task_id,
                        event_type=EventType.WORKER_REEXECUTION_FAILED,
                        source_component=EventSource.WORKER,
                        payload={
                            "attempt_id": str(request.attempt_id),
                            "attempt_number": request.attempt_number,
                            "error": str(e),
                        },
                    )
                )

            return WorkerReexecutionResult(
                attempt_id=request.attempt_id,
                task_id=request.task_id,
                workflow_id=request.workflow_id,
                attempt_number=request.attempt_number,
                execution_result=failure_result,
                previous_attempt_ids=previous_ids,
            )
