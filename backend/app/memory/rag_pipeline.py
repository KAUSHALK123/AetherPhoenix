import time
from typing import Any

from shared.contracts.memory import (
    MemoryCategory,
    sanitize_memory_content,
    sanitize_memory_metadata,
)
from shared.contracts.planner import PlannerRequest
from shared.contracts.rag import (
    RAGContext,
    RAGSourceType,
    RetrievalQuery,
    RetrievedContextItem,
)
from shared.contracts.task import Task

from app.core.logging import get_logger
from app.memory.conversation_memory import ConversationMemoryService
from app.memory.task_history import TaskHistoryService, get_task_history_service
from app.memory.vector_db import VectorDatabaseService, get_vector_db_service

logger = get_logger(__name__)


class RAGContextBuilder:
    """
    Utility for formatting retrieved context items into structured markdown context.
    """

    @staticmethod
    def build_formatted_context(
        items: list[RetrievedContextItem], query: str
    ) -> str:
        """
        Formats ranked context items into a clean Markdown block ready
        for agent prompt injection.
        """
        if not items:
            return ""

        header = (
            "### Relevant Context (Retrieved Knowledge)\n"
            "*Note: Retrieved information is provided for reference context. "
            "Verify all information during planning and execution.*\n\n"
        )

        blocks = []
        for idx, item in enumerate(items, start=1):
            source_str = (
                item.source_type.value
                if hasattr(item.source_type, "value")
                else str(item.source_type)
            )
            score_str = f"{item.score:.3f}"
            sid_str = f" | ID: {item.source_id}" if item.source_id else ""

            meta_parts = []
            if item.metadata:
                for k, v in item.metadata.items():
                    if k not in ("source_id", "memory_id", "vector"):
                        meta_parts.append(f"{k}={v}")
            meta_str = f" | Metadata: [{', '.join(meta_parts)}]" if meta_parts else ""

            blocks.append(
                f"#### Context Item {idx} (Source: {source_str} | "
                f"Score: {score_str}{sid_str}{meta_str})\n"
                f"{item.content.strip()}\n"
            )

        return header + "\n".join(blocks)


class RAGPipelineService:
    """
    Retrieval-Augmented Generation (RAG) Pipeline Service.

    Separates retrieval from agent reasoning. Interfaces with Vector Database,
    Conversation Memory, and Task History to retrieve relevant information, filter out
    low-relevance items, rank results, format context, and inject context into agents.
    """

    def __init__(
        self,
        vector_db: VectorDatabaseService | None = None,
        conversation_memory: ConversationMemoryService | None = None,
        task_history: TaskHistoryService | None = None,
    ) -> None:
        self.vector_db = vector_db or get_vector_db_service()
        self.conversation_memory = conversation_memory
        self.task_history = task_history or get_task_history_service()
        self.logger = logger

    async def retrieve(
        self,
        query: RetrievalQuery | str,
        top_k: int = 5,
        min_score: float = 0.0,
        session_id: str | None = None,
        category: str | MemoryCategory | None = None,
        source_types: list[RAGSourceType] | list[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> RAGContext:
        """
        Executes a RAG retrieval query across vector database and memory backends.
        Performs similarity search, relevance threshold filtering, context ranking,
        formatting, and metadata preservation.
        """
        start_time = time.time()

        # Parse query input
        if isinstance(query, str):
            if not query or not query.strip():
                self.logger.warning("RAG retrieve called with empty query string.")
                return RAGContext(
                    query="",
                    items=[],
                    formatted_context="",
                    total_retrieved=0,
                    retrieval_metadata={
                        "status": "empty_query",
                        "execution_time_ms": 0.0,
                    },
                )
            cat_val = (
                category.value if isinstance(category, MemoryCategory) else category
            )
            query_obj = RetrievalQuery(
                query_text=query,
                top_k=top_k,
                min_score=min_score,
                session_id=session_id,
                category=cat_val,
                source_types=source_types,
                metadata_filter=metadata_filter or {},
            )
        else:
            query_obj = query

        self.logger.info(
            f"RAG Pipeline executing query: '{query_obj.query_text}' "
            f"(top_k={query_obj.top_k}, min_score={query_obj.min_score})",
            extra_context={
                "query_text": query_obj.query_text,
                "top_k": query_obj.top_k,
                "min_score": query_obj.min_score,
                "session_id": query_obj.session_id,
            },
        )

        retrieved_items: list[RetrievedContextItem] = []
        sources_searched: list[str] = []

        try:
            # 1. Query Vector Database
            filter_meta = dict(query_obj.metadata_filter or {})
            sources_searched.append(RAGSourceType.VECTOR_DB.value)

            # Retrieve wider candidate pool before ranking
            candidate_top_k = query_obj.top_k * 2
            vector_results = await self.vector_db.search_similar(
                query_text=query_obj.query_text,
                top_k=candidate_top_k,
                filter_metadata=filter_meta if filter_meta else None,
                min_score=query_obj.min_score,
            )

            for vec_res in vector_results:
                sanitized_doc = sanitize_memory_content(vec_res.document)
                sanitized_meta = sanitize_memory_metadata(vec_res.metadata or {})
                item = RetrievedContextItem(
                    content=sanitized_doc,
                    score=vec_res.score,
                    source_type=RAGSourceType.VECTOR_DB,
                    source_id=str(vec_res.memory_id),
                    metadata=sanitized_meta,
                )
                retrieved_items.append(item)

            # 2. Query Conversation Memory if available and requested
            if self.conversation_memory and (
                not query_obj.source_types
                or RAGSourceType.CONVERSATION_MEMORY in query_obj.source_types
                or "conversation_memory" in query_obj.source_types
            ):
                sources_searched.append(RAGSourceType.CONVERSATION_MEMORY.value)
                memories = self.conversation_memory.get_relevant_memories(
                    session_id=query_obj.session_id,
                    category=query_obj.category,
                    min_relevance=query_obj.min_score,
                    query_text=query_obj.query_text,
                    limit=query_obj.top_k,
                )
                existing_ids = {
                    item.source_id for item in retrieved_items if item.source_id
                }
                for mem in memories:
                    if mem.memory_id in existing_ids:
                        continue
                    item = RetrievedContextItem(
                        content=sanitize_memory_content(mem.content),
                        score=mem.relevance_score,
                        source_type=RAGSourceType.CONVERSATION_MEMORY,
                        source_id=mem.memory_id,
                        metadata=sanitize_memory_metadata(
                            {
                                "session_id": mem.session_id,
                                "role": mem.role,
                                "category": mem.category.value,
                                **mem.metadata,
                            }
                        ),
                        created_at=mem.created_at,
                    )
                    retrieved_items.append(item)

            # 3. Query Task History if requested
            if self.task_history and (
                query_obj.source_types
                and (
                    RAGSourceType.TASK_HISTORY in query_obj.source_types
                    or "task_history" in query_obj.source_types
                )
            ):
                sources_searched.append(RAGSourceType.TASK_HISTORY.value)
                task_records = self.task_history.search_task_history(
                    query_text=query_obj.query_text,
                    limit=query_obj.top_k,
                )
                existing_ids = {
                    item.source_id for item in retrieved_items if item.source_id
                }
                for tr in task_records:
                    if str(tr.task_id) in existing_ids:
                        continue
                    content_str = (
                        f"Task '{tr.task_name}' (Status: {tr.status.value}). "
                        f"Agent: {tr.assigned_agent}. "
                        f"Output: {tr.output_summary or 'N/A'}"
                    )
                    item = RetrievedContextItem(
                        content=sanitize_memory_content(content_str),
                        score=1.0 if tr.status.value == "completed" else 0.5,
                        source_type=RAGSourceType.TASK_HISTORY,
                        source_id=str(tr.task_id),
                        metadata=sanitize_memory_metadata(
                            {
                                "workflow_id": str(tr.workflow_id),
                                "assigned_agent": tr.assigned_agent,
                                "status": tr.status.value,
                            }
                        ),
                    )
                    retrieved_items.append(item)

            # 4. Relevance Threshold Filtering & Context Ranking
            filtered_items = [
                item for item in retrieved_items if item.score >= query_obj.min_score
            ]
            # Deduplicate by content
            unique_items: list[RetrievedContextItem] = []
            seen_content = set()
            for item in sorted(filtered_items, key=lambda x: x.score, reverse=True):
                norm_content = item.content.strip().lower()
                if norm_content not in seen_content:
                    seen_content.add(norm_content)
                    unique_items.append(item)

            final_ranked_items = unique_items[: query_obj.top_k]

            # 5. Build Formatted Context Block
            formatted_context = RAGContextBuilder.build_formatted_context(
                items=final_ranked_items,
                query=query_obj.query_text,
            )

            execution_time_ms = (time.time() - start_time) * 1000.0

            result = RAGContext(
                query=query_obj.query_text,
                items=final_ranked_items,
                formatted_context=formatted_context,
                total_retrieved=len(final_ranked_items),
                retrieval_metadata={
                    "status": "success",
                    "execution_time_ms": round(execution_time_ms, 2),
                    "total_candidates_found": len(retrieved_items),
                    "total_returned": len(final_ranked_items),
                    "min_score_applied": query_obj.min_score,
                    "top_k_applied": query_obj.top_k,
                    "sources_searched": sources_searched,
                },
            )

            self.logger.info(
                f"RAG Pipeline retrieval finished: found "
                f"{len(final_ranked_items)} items in {execution_time_ms:.1f}ms",
                extra_context={
                    "total_retrieved": len(final_ranked_items),
                    "execution_time_ms": round(execution_time_ms, 2),
                },
            )
            return result

        except Exception as exc:
            execution_time_ms = (time.time() - start_time) * 1000.0
            self.logger.error(
                f"RAG Pipeline retrieval failed gracefully: {str(exc)}",
                exc_info=True,
            )
            return RAGContext(
                query=query_obj.query_text,
                items=[],
                formatted_context="",
                total_retrieved=0,
                retrieval_metadata={
                    "status": "error",
                    "error_message": str(exc),
                    "execution_time_ms": round(execution_time_ms, 2),
                    "sources_searched": sources_searched,
                },
            )

    async def enrich_planner_request(
        self,
        request: PlannerRequest,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> PlannerRequest:
        """
        Enriches a PlannerRequest with relevant RAG context retrieved from memory.
        """
        query_text = request.message
        session_id = request.session_id

        rag_context = await self.retrieve(
            query=query_text,
            top_k=top_k,
            min_score=min_score,
            session_id=session_id,
        )

        existing_context = dict(request.context or {})
        existing_context["rag_context"] = rag_context.model_dump()
        existing_context["retrieved_knowledge"] = rag_context.formatted_context

        return PlannerRequest(
            session_id=request.session_id,
            message=request.message,
            context=existing_context,
            feedback=request.feedback,
        )

    async def enrich_worker_task(
        self,
        task: Task,
        query_text: str | None = None,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> Task:
        """
        Enriches a Worker Task with relevant RAG context prior to execution.
        """
        search_query = query_text or f"{task.task_name} {task.description or ''}"

        rag_context = await self.retrieve(
            query=search_query,
            top_k=top_k,
            min_score=min_score,
        )

        task_inputs = dict(task.inputs or {})
        task_inputs["rag_context"] = rag_context.model_dump()
        task_inputs["retrieved_knowledge"] = rag_context.formatted_context
        task.inputs = task_inputs

        if hasattr(task, "context"):
            setattr(task, "context", task_inputs)

        return task


_rag_pipeline_instance: RAGPipelineService | None = None


def get_rag_pipeline() -> RAGPipelineService:
    """Returns global singleton RAGPipelineService instance."""
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        _rag_pipeline_instance = RAGPipelineService()
    return _rag_pipeline_instance


def reset_rag_pipeline() -> RAGPipelineService:
    """Resets and returns a fresh global RAGPipelineService instance."""
    global _rag_pipeline_instance
    _rag_pipeline_instance = RAGPipelineService()
    return _rag_pipeline_instance
