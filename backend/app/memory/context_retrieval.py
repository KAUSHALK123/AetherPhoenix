import time

from shared.contracts.context_retrieval import (
    AgentType,
    ContextRetrievalRequest,
    ContextRetrievalResponse,
)
from shared.contracts.memory import (
    MemoryCategory,
    sanitize_memory_content,
    sanitize_memory_metadata,
)
from shared.contracts.rag import (
    RAGSourceType,
    RetrievalQuery,
    RetrievedContextItem,
)
from shared.contracts.task import Task

from app.core.logging import get_logger
from app.memory.conversation_memory import ConversationMemoryService
from app.memory.rag_pipeline import (
    RAGContextBuilder,
    RAGPipelineService,
    get_rag_pipeline,
)
from app.memory.task_history import TaskHistoryService, get_task_history_service

logger = get_logger(__name__)


class ContextRetrievalService:
    """
    Dedicated Context Retrieval Service for AI Agents.

    Determines what stored memory or knowledge should be provided to an agent
    for a given task. Filters out irrelevant memory, enforces context limits,
    preserves source metadata, supports workflow awareness and agent-specific retrieval.
    """

    def __init__(
        self,
        rag_pipeline: RAGPipelineService | None = None,
        task_history: TaskHistoryService | None = None,
        conversation_memory: ConversationMemoryService | None = None,
    ) -> None:
        self.rag_pipeline = rag_pipeline or get_rag_pipeline()
        self.task_history = task_history or get_task_history_service()
        self.conversation_memory = conversation_memory
        self.logger = logger

    def construct_query(self, request: ContextRetrievalRequest) -> str:
        """
        Constructs a targeted retrieval query string from the request parameters.
        Combines task details, workflow goal, user prompt, and agent type context.
        """
        parts: list[str] = []

        if request.user_request and request.user_request.strip():
            parts.append(request.user_request.strip())

        if request.task_name and request.task_name.strip():
            parts.append(f"Task: {request.task_name.strip()}")

        if request.task_description and request.task_description.strip():
            parts.append(request.task_description.strip())

        if request.workflow_goal and request.workflow_goal.strip():
            parts.append(f"Goal: {request.workflow_goal.strip()}")

        if not parts:
            agent_str = (
                request.agent_type.value
                if hasattr(request.agent_type, "value")
                else str(request.agent_type)
            )
            query = f"Context for {agent_str} agent"
        else:
            query = " | ".join(parts)

        return query

    async def retrieve_context(
        self,
        request: ContextRetrievalRequest,
    ) -> ContextRetrievalResponse:
        """
        Executes workflow-aware and agent-specific context retrieval.
        Retrieves, ranks, filters, sanitizes, and limits context items.
        """
        start_time = time.time()
        query_text = self.construct_query(request)

        self.logger.info(
            f"Context Retrieval requested for agent '{request.agent_type}' "
            f"with query: '{query_text}'",
            extra_context={
                "agent_type": str(request.agent_type),
                "workflow_id": request.workflow_id,
                "task_id": request.task_id,
                "session_id": request.session_id,
                "max_items": request.max_items,
                "min_relevance_score": request.min_relevance_score,
            },
        )

        try:
            # 1. Execute primary retrieval via RAG Pipeline
            source_types = request.source_types
            rag_query = RetrievalQuery(
                query_text=query_text,
                top_k=request.max_items * 3,  # Candidate pool for post-filtering
                min_score=request.min_relevance_score,
                session_id=request.session_id,
                category=None,
                source_types=source_types,
                metadata_filter=request.metadata_filter or {},
            )

            rag_result = await self.rag_pipeline.retrieve(query=rag_query)
            candidate_items: list[RetrievedContextItem] = list(rag_result.items)
            filtered_count = 0

            # 2. Workflow-specific Task History Retrieval
            if request.include_previous_tasks and (
                request.workflow_id or request.task_name
            ):
                existing_ids = {
                    item.source_id for item in candidate_items if item.source_id
                }
                w_id = None
                if request.workflow_id:
                    try:
                        from uuid import UUID

                        w_id = UUID(request.workflow_id)
                    except ValueError:
                        w_id = None

                workflow_task_records = []
                if w_id:
                    workflow_task_records = (
                        self.task_history.get_workflow_task_records(w_id)
                    )
                else:
                    workflow_task_records = self.task_history.filter_history(
                        limit=request.max_items
                    )

                for tr in workflow_task_records:
                    if str(tr.task_id) in existing_ids:
                        continue
                    if request.task_id and str(tr.task_id) == str(request.task_id):
                        # Exclude current running task record itself
                        continue

                    output_str = (
                        tr.outputs.get("output_summary")
                        or tr.outputs.get("summary")
                        or (str(tr.outputs) if tr.outputs else "N/A")
                    )
                    content_str = (
                        f"Previous Task '{tr.task_name}' (Status: {tr.status.value}). "
                        f"Agent: {tr.assigned_agent}. Output: {output_str}"
                    )
                    score = (
                        0.95
                        if tr.status.value == "completed"
                        else (0.8 if tr.status.value == "failed" else 0.6)
                    )

                    item = RetrievedContextItem(
                        content=sanitize_memory_content(content_str),
                        score=score,
                        source_type=RAGSourceType.TASK_HISTORY,
                        source_id=str(tr.task_id),
                        metadata=sanitize_memory_metadata(
                            {
                                "workflow_id": str(tr.workflow_id),
                                "assigned_agent": tr.assigned_agent,
                                "status": tr.status.value,
                            }
                        ),
                        created_at=tr.created_at,
                    )
                    candidate_items.append(item)

            # 3. Apply Category Filtering
            if request.categories:
                allowed_cats = {
                    cat.value if isinstance(cat, MemoryCategory) else str(cat)
                    for cat in request.categories
                }
                filtered_candidates = []
                for item in candidate_items:
                    item_cat = item.metadata.get("category")
                    if item_cat is None or item_cat in allowed_cats:
                        filtered_candidates.append(item)
                    else:
                        filtered_count += 1
                candidate_items = filtered_candidates

            # 4. Agent-Specific Weighting & Relevance Tuning
            agent_str = (
                request.agent_type.value
                if hasattr(request.agent_type, "value")
                else str(request.agent_type).lower()
            )

            scored_items: list[tuple[float, RetrievedContextItem]] = []
            for item in candidate_items:
                adjusted_score = item.score
                item_cat = item.metadata.get("category", "")

                if agent_str == AgentType.PLANNER.value:
                    if item_cat in (
                        MemoryCategory.PREFERENCE.value,
                        MemoryCategory.PROJECT_CONTEXT.value,
                    ):
                        adjusted_score = min(1.0, adjusted_score * 1.2)
                elif agent_str == AgentType.WORKER.value:
                    if (
                        item_cat
                        in (
                            MemoryCategory.INSTRUCTION.value,
                            MemoryCategory.DECISION.value,
                        )
                        or item.source_type == RAGSourceType.TASK_HISTORY
                    ):
                        adjusted_score = min(1.0, adjusted_score * 1.15)
                elif agent_str == AgentType.HEALING.value:
                    status_meta = item.metadata.get("status", "")
                    if (
                        status_meta in ("failed", "healing")
                        or item.source_type == RAGSourceType.TASK_HISTORY
                    ):
                        adjusted_score = min(1.0, adjusted_score * 1.3)

                if adjusted_score >= request.min_relevance_score:
                    item.score = round(adjusted_score, 4)
                    scored_items.append((adjusted_score, item))
                else:
                    filtered_count += 1

            # Sort descending by adjusted relevance score
            scored_items.sort(key=lambda x: x[0], reverse=True)

            # Deduplicate by normalized content
            unique_items: list[RetrievedContextItem] = []
            seen_content = set()
            for _, item in scored_items:
                norm_text = item.content.strip().lower()
                if norm_text not in seen_content:
                    seen_content.add(norm_text)
                    unique_items.append(item)

            # 5. Apply Context Limit (max_items)
            final_items = unique_items[: request.max_items]
            if len(unique_items) > request.max_items:
                filtered_count += len(unique_items) - request.max_items

            # 6. Format Markdown Context for Prompt Injection
            formatted_context = RAGContextBuilder.build_formatted_context(
                items=final_items,
                query=query_text,
            )

            execution_time_ms = (time.time() - start_time) * 1000.0

            response = ContextRetrievalResponse(
                query_used=query_text,
                items=final_items,
                formatted_context=formatted_context,
                total_retrieved=len(final_items),
                filtered_count=filtered_count,
                metadata={
                    "status": "success",
                    "execution_time_ms": round(execution_time_ms, 2),
                    "agent_type": agent_str,
                    "workflow_id": request.workflow_id,
                    "task_id": request.task_id,
                    "min_relevance_score": request.min_relevance_score,
                    "max_items": request.max_items,
                },
            )

            self.logger.info(
                f"Context Retrieval completed for agent '{agent_str}': "
                f"returned {len(final_items)} items in {execution_time_ms:.1f}ms",
                extra_context={
                    "total_retrieved": len(final_items),
                    "filtered_count": filtered_count,
                    "execution_time_ms": round(execution_time_ms, 2),
                },
            )
            return response

        except Exception as exc:
            execution_time_ms = (time.time() - start_time) * 1000.0
            self.logger.error(
                f"Context Retrieval failed gracefully for query '{query_text}': "
                f"{str(exc)}",
                exc_info=True,
            )
            return ContextRetrievalResponse(
                query_used=query_text,
                items=[],
                formatted_context="",
                total_retrieved=0,
                filtered_count=0,
                metadata={
                    "status": "error",
                    "error_message": str(exc),
                    "execution_time_ms": round(execution_time_ms, 2),
                    "agent_type": str(request.agent_type),
                },
            )

    async def get_context_for_planner(
        self,
        user_request: str,
        session_id: str | None = None,
        max_items: int = 5,
        min_relevance_score: float = 0.0,
    ) -> ContextRetrievalResponse:
        """
        Convenience helper to retrieve context tailored for PlannerAgent.
        """
        req = ContextRetrievalRequest(
            user_request=user_request,
            agent_type=AgentType.PLANNER,
            session_id=session_id,
            max_items=max_items,
            min_relevance_score=min_relevance_score,
            categories=[
                MemoryCategory.PREFERENCE,
                MemoryCategory.PROJECT_CONTEXT,
                MemoryCategory.INSTRUCTION,
                MemoryCategory.DECISION,
            ],
        )
        return await self.retrieve_context(req)

    async def get_context_for_worker(
        self,
        task: Task,
        workflow_goal: str | None = None,
        session_id: str | None = None,
        max_items: int = 5,
        min_relevance_score: float = 0.0,
    ) -> ContextRetrievalResponse:
        """
        Convenience helper to retrieve context tailored for WorkerAgent.
        """
        req = ContextRetrievalRequest(
            workflow_id=str(task.workflow_id) if task.workflow_id else None,
            workflow_goal=workflow_goal,
            task_id=str(task.task_id),
            task_name=task.task_name,
            task_description=task.description,
            agent_type=AgentType.WORKER,
            session_id=session_id,
            max_items=max_items,
            min_relevance_score=min_relevance_score,
            include_previous_tasks=True,
        )
        return await self.retrieve_context(req)

    async def get_context_for_healing(
        self,
        task_id: str,
        error_summary: str = "",
        max_items: int = 5,
        min_relevance_score: float = 0.0,
    ) -> ContextRetrievalResponse:
        """
        Convenience helper to retrieve context tailored for HealingAgent.
        """
        req = ContextRetrievalRequest(
            task_id=task_id,
            task_description=error_summary,
            agent_type=AgentType.HEALING,
            max_items=max_items,
            min_relevance_score=min_relevance_score,
            include_previous_tasks=True,
        )
        return await self.retrieve_context(req)


_context_retrieval_instance: ContextRetrievalService | None = None


def get_context_retrieval_service() -> ContextRetrievalService:
    """Returns global singleton ContextRetrievalService instance."""
    global _context_retrieval_instance
    if _context_retrieval_instance is None:
        _context_retrieval_instance = ContextRetrievalService()
    return _context_retrieval_instance


def reset_context_retrieval_service() -> ContextRetrievalService:
    """Resets and returns a fresh global ContextRetrievalService instance."""
    global _context_retrieval_instance
    _context_retrieval_instance = ContextRetrievalService()
    return _context_retrieval_instance
