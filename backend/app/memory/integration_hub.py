from typing import Any
from uuid import UUID

from shared.contracts.event import EventType, RuntimeEvent
from shared.contracts.execution import ExecutionResult, HealingResult, TaskError
from shared.contracts.memory import (
    MemoryCategory,
    MemoryItem,
    MemoryType,
    RetentionPolicy,
    sanitize_memory_content,
    sanitize_memory_metadata,
)
from shared.contracts.planner import PlannerRequest
from shared.contracts.task import Task, TaskStatus

from app.core.logging import get_logger
from app.memory.manager import MemoryManager, get_memory_manager
from app.memory.rag_pipeline import RAGPipelineService, get_rag_pipeline
from app.memory.task_history import TaskHistoryService, get_task_history_service

logger = get_logger(__name__)


class MemoryIntegrationHub:
    """
    Unified Integration Hub coordinating memory interactions across
    Planner, Worker, Supervisor, and Healing agents.

    Provides targeted context retrieval, task history recording, execution
    result ingestion, supervisor event capture, healing result recording,
    and scoped RAG enrichment without circular dependencies or unchecked leaks.
    """

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        rag_pipeline: RAGPipelineService | None = None,
        task_history: TaskHistoryService | None = None,
    ) -> None:
        self.memory_manager = memory_manager or get_memory_manager()
        self.rag_pipeline = rag_pipeline or get_rag_pipeline()
        self.task_history = task_history or get_task_history_service()
        self.logger = logger

    # -------------------------------------------------------------------------
    # Planner Agent Integration
    # -------------------------------------------------------------------------
    async def prepare_planner_request(
        self,
        request: PlannerRequest,
        top_k: int = 5,
        min_relevance: float = 0.0,
    ) -> PlannerRequest:
        """
        Enriches incoming PlannerRequest with relevant previous knowledge and
        conversation context without overwhelming the context window.
        """
        try:
            # 1. RAG Enrichment
            enriched_request = await self.rag_pipeline.enrich_planner_request(
                request=request,
                top_k=top_k,
                min_score=min_relevance,
            )

            # 2. Store incoming user prompt as a conversation memory item
            await self.memory_manager.create_memory(
                content=request.message,
                category=MemoryCategory.GENERAL_CHAT,
                memory_type=MemoryType.CONVERSATION,
                session_id=request.session_id,
                relevance_score=1.0,
                metadata={"source": "planner_user_request"},
                author_agent="User",
                retention=RetentionPolicy(max_age_days=30, auto_archive=True),
            )

            self.logger.info(
                f"Prepared PlannerRequest for session {request.session_id}"
            )
            return enriched_request
        except Exception as exc:
            self.logger.warning(
                f"Memory integration failed gracefully for planner request: {exc}"
            )
            return request

    # -------------------------------------------------------------------------
    # Worker Agent Integration
    # -------------------------------------------------------------------------
    async def prepare_worker_task(
        self,
        task: Task,
        top_k: int = 3,
        min_score: float = 0.5,
    ) -> Task:
        """
        Injects necessary task context, past relevant execution results, and artifact
        references into a Worker Task prior to execution.
        """
        try:
            enriched_task = await self.rag_pipeline.enrich_worker_task(
                task=task,
                top_k=top_k,
                min_score=min_score,
            )
            self.logger.info(f"Enriched Worker task {task.task_id} with memory context")
            return enriched_task
        except Exception as exc:
            self.logger.warning(
                f"Memory integration failed for worker task {task.task_id}: {exc}"
            )
            return task

    async def record_worker_result(
        self,
        task: Task,
        output_data: Any,
        status: TaskStatus = TaskStatus.COMPLETED,
        execution_summary: str | None = None,
    ) -> MemoryItem | None:
        """
        Stores completed task output, key execution results, and updates task history.
        """
        summary_text = (
            execution_summary
            or f"Task '{task.task_name}' executed with status {status.value}."
        )
        if output_data:
            summary_text += f" Output: {str(output_data)[:400]}"

        # 1. Update task history record
        if status == TaskStatus.COMPLETED:
            exec_res = ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output=(
                    output_data
                    if isinstance(output_data, dict)
                    else {"result": str(output_data)}
                ),
            )
            self.task_history.record_task_completed(
                task_id=task.task_id,
                result=exec_res,
                metadata={"summary": summary_text},
            )

        # 2. Store permanent knowledge memory only for completed significant tasks
        if status == TaskStatus.COMPLETED:
            try:
                memory_item = await self.memory_manager.create_memory(
                    content=summary_text,
                    category=MemoryCategory.PROJECT_CONTEXT,
                    memory_type=MemoryType.TASK_RESULT,
                    workflow_id=str(task.workflow_id) if task.workflow_id else None,
                    task_id=str(task.task_id),
                    relevance_score=0.85,
                    metadata=sanitize_memory_metadata(
                        {
                            "task_name": task.task_name,
                            "assigned_agent": task.assigned_agent,
                            "tool_name": task.required_tool,
                        }
                    ),
                    author_agent=task.assigned_agent or "WorkerAgent",
                    retention=RetentionPolicy(max_age_days=60, auto_archive=True),
                )
                self.logger.info(f"Recorded worker result: {memory_item.memory_id}")
                return memory_item
            except Exception as exc:
                self.logger.warning(f"Failed to persist worker result memory: {exc}")
                return None
        return None

    # -------------------------------------------------------------------------
    # Supervisor Agent Integration
    # -------------------------------------------------------------------------
    async def record_supervisor_event(
        self,
        event: RuntimeEvent,
        workflow_id: str | None = None,
    ) -> MemoryItem | None:
        """
        Captures critical workflow milestones and supervisor events without flooding
        memory with transient execution ticks.
        """
        notable_event_types = {
            EventType.WORKFLOW_COMPLETED,
            EventType.WORKFLOW_FAILED,
            EventType.TASK_FAILED,
        }

        if event.event_type not in notable_event_types:
            return None

        event_desc = (
            f"Supervisor Event: {event.event_type.value} from "
            f"{event.source_component.value}. "
            f"Payload: {str(event.payload)[:300]}"
        )

        try:
            return await self.memory_manager.create_memory(
                content=sanitize_memory_content(event_desc),
                category=MemoryCategory.DECISION,
                memory_type=MemoryType.AGENT_FACT,
                workflow_id=workflow_id
                or (str(event.workflow_id) if event.workflow_id else None),
                relevance_score=0.9,
                metadata={
                    "event_type": event.event_type.value,
                    "source": event.source_component.value,
                },
                author_agent="SupervisorAgent",
                retention=RetentionPolicy(max_age_days=30, auto_archive=True),
            )
        except Exception as exc:
            self.logger.warning(f"Failed to record supervisor event to memory: {exc}")
            return None

    # -------------------------------------------------------------------------
    # Healing Agent Integration
    # -------------------------------------------------------------------------
    async def record_healing_result(
        self,
        task_id: UUID | str,
        workflow_id: UUID | str,
        task_error: TaskError | None,
        healing_result: HealingResult,
    ) -> MemoryItem | None:
        """
        Records self-healing diagnostic resolutions and recovery plan executions into
        task history and persistent memory.
        """
        # 1. Update Task History with retry / self-healing attempt
        self.task_history.record_retry_attempt(
            task_id=task_id,
            attempt_number=getattr(healing_result, "attempt_number", 1),
            reason=getattr(healing_result, "recovery_strategy", "Healing Retry"),
            metadata={
                "healing_success": str(getattr(healing_result, "success", True)),
                "error_code": task_error.error_code if task_error else "",
            },
        )

        # 2. Persist diagnostic knowledge to prevent repeated errors in future planning
        content_desc = (
            f"Healing Resolution for Task {task_id}: Strategy "
            f"'{getattr(healing_result, 'recovery_strategy', 'RETRY')}'. "
            f"Success={getattr(healing_result, 'success', True)}. "
            f"Root Cause: {task_error.error_message if task_error else 'N/A'}"
        )

        try:
            return await self.memory_manager.create_memory(
                content=sanitize_memory_content(content_desc),
                category=MemoryCategory.DECISION,
                memory_type=MemoryType.KNOWLEDGE,
                workflow_id=str(workflow_id),
                task_id=str(task_id),
                relevance_score=0.95,
                metadata={
                    "healing_success": str(getattr(healing_result, "success", True)),
                    "error_code": task_error.error_code if task_error else "",
                },
                author_agent="HealingAgent",
                retention=RetentionPolicy(max_age_days=90, auto_archive=True),
            )
        except Exception as exc:
            self.logger.warning(f"Failed to record healing resolution memory: {exc}")
            return None


_global_memory_hub: MemoryIntegrationHub | None = None


def get_memory_integration_hub() -> MemoryIntegrationHub:
    """Singleton getter for MemoryIntegrationHub."""
    global _global_memory_hub
    if _global_memory_hub is None:
        _global_memory_hub = MemoryIntegrationHub()
    return _global_memory_hub


def reset_memory_integration_hub() -> MemoryIntegrationHub:
    """Resets and returns a fresh singleton MemoryIntegrationHub."""
    global _global_memory_hub
    _global_memory_hub = MemoryIntegrationHub()
    return _global_memory_hub
