import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import ExecutionResult, TaskError
from shared.contracts.task import Task, TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowStatus

from app.core.events.bus import EventBus
from app.core.logging import get_logger
from app.engine.workflow import WorkflowEngine
from app.agents.worker.agent import WorkerAgent
from app.agents.supervisor.agent import SupervisorAgent

logger = get_logger(__name__)


class PipelineOrchestrator:
    """
    Central runtime coordinator responsible for driving the execution of workflows.
    Orchestrates Planner -> WorkflowEngine -> Worker -> Supervisor lifecycle loop,
    manages dependency resolution, concurrency, error retries, and publishes state events.
    """

    def __init__(
        self,
        worker_agent: WorkerAgent,
        supervisor_agent: SupervisorAgent,
        event_bus: EventBus,
    ) -> None:
        self.worker = worker_agent
        self.supervisor = supervisor_agent
        self.event_bus = event_bus

    async def _emit_orchestrator_event(
        self,
        event_type: EventType,
        workflow_id: UUID,
        task_id: Optional[UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publishes an event from the Orchestrator on the system event bus."""
        event = RuntimeEvent(
            workflow_id=workflow_id,
            task_id=task_id,
            event_type=event_type,
            source_component=EventSource.EXECUTION_ENGINE,
            payload=payload or {},
        )
        await self.event_bus.publish(event)

    async def run_workflow(
        self,
        state: SharedWorkflowState,
        max_retries: int = 3,
    ) -> SharedWorkflowState:
        """
        Executes a workflow state end-to-end.
        Loads tasks, runs execution loops driven by dependencies, runs worker/supervisor steps,
        handles transient failures with retries, propagates blocking failures, and updates workflow status.
        """
        workflow_id = state.metadata.workflow_id
        logger.info(f"Starting workflow execution for: {workflow_id} (Goal: '{state.metadata.goal}')")

        # 1. Start Workflow Engine
        engine = WorkflowEngine(state)
        engine.start()

        # Update and sync progress initially
        self.supervisor.monitor.update_progress_state(state)

        # Emit WORKFLOW_STARTED event
        await self._emit_orchestrator_event(
            event_type=EventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            payload={"goal": state.metadata.goal},
        )

        running_futures: Dict[UUID, asyncio.Task] = {}

        while state.metadata.status == WorkflowStatus.RUNNING:
            # Deadlock and lifecycle checks
            # Retrieve currently enqueued tasks (copying to avoid mutation issues during iteration)
            queue_snapshot = list(state.execution_queue)
            
            # Start ready tasks
            for task_id in queue_snapshot:
                task = state.tasks.get(task_id)
                if not task:
                    continue

                # Evaluate dependencies / prerequisites
                prereq_status = self.supervisor.monitor.parallel_monitor.check_prerequisites(task_id, state)
                logger.debug(f"Task {task_id} ('{task.task_name}') dependency check: {prereq_status}")

                if prereq_status == "READY":
                    # Remove from queue and mark as RUNNING
                    state.execution_queue.remove(task_id)
                    engine.update_task_status(task_id, TaskStatus.RUNNING)
                    
                    # Update progress state
                    self.supervisor.monitor.update_progress_state(state)

                    # Emit TASK_STARTED event
                    await self._emit_orchestrator_event(
                        event_type=EventType.TASK_STARTED,
                        workflow_id=workflow_id,
                        task_id=task_id,
                        payload={"task_name": task.task_name},
                    )

                    # Asynchronous execution & supervision task
                    async def execute_task_with_supervision(t=task):
                        try:
                            # 1. Execute task in Worker
                            res = await self.worker.execute(t)
                        except Exception as e:
                            logger.exception(f"Exception during worker execution of task {t.task_id}")
                            res = ExecutionResult(
                                task_id=t.task_id,
                                workflow_id=t.workflow_id,
                                success=False,
                                error=TaskError(
                                    error_code="UNEXPECTED_EXCEPTION",
                                    error_message=str(e),
                                    is_recoverable=True,
                                ),
                            )

                        # 2. Validate output in Supervisor
                        validation = await self.supervisor.execute(t, result=res, state=state)

                        # Publish TASK_COMPLETED / TASK_FAILED based on validation decision
                        if validation.is_valid:
                            await self._emit_orchestrator_event(
                                event_type=EventType.TASK_COMPLETED,
                                workflow_id=workflow_id,
                                task_id=t.task_id,
                                payload={"output_keys": list(res.output.keys()) if res.output else []},
                            )
                        else:
                            await self._emit_orchestrator_event(
                                event_type=EventType.TASK_FAILED,
                                workflow_id=workflow_id,
                                task_id=t.task_id,
                                payload={
                                    "error_code": res.error.error_code if res.error else "VALIDATION_FAILED",
                                    "issues": validation.issues,
                                },
                            )

                            # 3. If failed, evaluate and trigger retry
                            retried = await self.supervisor.execute(
                                t,
                                state=state,
                                error=res.error or TaskError(
                                    error_code="VALIDATION_FAILED",
                                    error_message="Supervisor output validation failed.",
                                ),
                                max_retries=max_retries,
                            )
                            if retried:
                                logger.info(f"Task {t.task_id} failed validation. Controlled retry triggered.")
                                await self._emit_orchestrator_event(
                                    event_type=EventType.TASK_RETRIED,
                                    workflow_id=workflow_id,
                                    task_id=t.task_id,
                                    payload={"retry_count": t.retry_count},
                                )
                            else:
                                logger.info(f"Task {t.task_id} failed validation and is not retryable.")
                        
                        return validation

                    # Spawn execution task concurrently
                    running_futures[task_id] = asyncio.create_task(execute_task_with_supervision())

                elif prereq_status == "BLOCKED":
                    # Prerequisites failed. Set status to BLOCKED and remove from queue
                    state.execution_queue.remove(task_id)
                    engine.update_task_status(task_id, TaskStatus.BLOCKED)
                    
                    # Update progress state to propagate blockages down the dependency tree
                    self.supervisor.monitor.update_progress_state(state)

                elif prereq_status == "PENDING":
                    # Prerequisites are still in progress. Leave in queue and wait.
                    pass

            # Check running tasks
            if running_futures:
                # Wait for at least one running task to complete
                done, _ = await asyncio.wait(
                    list(running_futures.values()),
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Identify which task future completed and clean up from active map
                completed_ids = []
                for t_id, fut in list(running_futures.items()):
                    if fut in done:
                        completed_ids.append(t_id)
                        del running_futures[t_id]

                # Update state progress
                self.supervisor.monitor.update_progress_state(state)
            else:
                # Loop condition: no running tasks and no items in execution queue
                if not state.execution_queue:
                    break
                else:
                    # Deadlock check: items exist in queue but none can run (prereqs pending but no tasks running)
                    # This happens if there's a dependency cycle or all pending tasks are stuck
                    logger.error(f"Deadlock detected for workflow {workflow_id}. execution_queue has items, but none are ready/running.")
                    break

        # Final progress evaluation and state updates
        self.supervisor.monitor.update_progress_state(state)
        progress = state.progress

        if progress.failed_tasks > 0 or progress.blocked_tasks > 0:
            engine.fail()
            final_event = EventType.WORKFLOW_FAILED
            logger.error(f"Workflow {workflow_id} execution FAILED (Completed: {progress.completed_tasks}, Failed: {progress.failed_tasks}, Blocked: {progress.blocked_tasks})")
        else:
            engine.complete()
            final_event = EventType.WORKFLOW_COMPLETED
            logger.info(f"Workflow {workflow_id} execution COMPLETED successfully.")

        # Emit final workflow event
        await self._emit_orchestrator_event(
            event_type=final_event,
            workflow_id=workflow_id,
            payload={
                "goal": state.metadata.goal,
                "completed_tasks": progress.completed_tasks,
                "total_tasks": progress.total_tasks,
            },
        )

        return state
