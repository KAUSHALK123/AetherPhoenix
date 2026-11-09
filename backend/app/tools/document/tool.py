import os
import time
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.document import DocumentGenerationResult, StructuredDocumentInput
from shared.contracts.execution import ExecutionMetrics, ExecutionResult, TaskError
from shared.contracts.permission import PermissionType
from shared.contracts.task import Task
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.core.config import get_config
from app.core.logging import get_logger
from app.core.permissions import PermissionManager
from app.services.artifact_storage import ArtifactStorageService, get_artifact_storage_service
from app.tools.adapter import BaseToolAdapter
from app.tools.document.generator import DocumentGenerator
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class _AwaitableDocResult(DocumentGenerationResult):
    """Allows sync return value to also be awaited if caller uses `await adapter.execute(...)`."""

    def __await__(self):
        async def _async_self():
            return self

        return _async_self().__await__()


class DocumentToolAdapter(BaseToolAdapter):
    """
    Tool Adapter wrapping DocumentGenerator for Worker Agent tool execution.
    Supports both Task-based asynchronous execution and raw dictionary payloads.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        artifact_storage_service: Optional[ArtifactStorageService] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.permission_manager = permission_manager
        self.artifact_storage_service = (
            artifact_storage_service or get_artifact_storage_service()
        )
        self.generator = DocumentGenerator(permission_manager=permission_manager)

    async def execute(
        self,
        payload_or_task: Any,
        workflow_id: Optional[UUID] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Executes document generation from a Task or dictionary payload.
        """
        if isinstance(payload_or_task, Task):
            return await self._execute_task(payload_or_task)

        # Synchronous / payload execution fallback
        payload = payload_or_task
        if isinstance(payload, StructuredDocumentInput):
            input_data = payload
        else:
            input_data = StructuredDocumentInput.model_validate(payload)

        if workflow_id and not input_data.workflow_id:
            input_data.workflow_id = workflow_id

        res = self.generator.generate(input_data)
        return _AwaitableDocResult(**res.model_dump())

    async def _execute_task(self, task: Task) -> ExecutionResult:
        start_time = time.time()
        logs_captured = [f"DocumentToolAdapter executing task '{task.task_name}'"]

        inputs = dict(task.inputs) if task.inputs else {}
        title = (
            inputs.get("title")
            or inputs.get("document_name")
            or task.task_name
            or "Document"
        )

        cfg = get_config()
        output_dir = Path(cfg.ARTIFACTS_DIR) / str(task.workflow_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        target_format = inputs.get("format", "markdown").lower()
        ext_map = {"markdown": ".md", "text": ".txt", "html": ".html", "json": ".json", "csv": ".csv"}
        ext = ext_map.get(target_format, ".md")

        filename = f"{title.lower().replace(' ', '_')}{ext}"
        output_path = inputs.get("output_path") or str(output_dir / filename)

        doc_input_dict = {
            "title": title,
            "format": target_format,
            "content": inputs.get("content", ""),
            "sections": inputs.get("sections", []),
            "elements": inputs.get("elements", []),
            "output_path": output_path,
            "overwrite": True,
            "workflow_id": task.workflow_id,
            "task_id": task.task_id,
        }

        try:
            doc_input = StructuredDocumentInput.model_validate(doc_input_dict)
            gen_result = self.generator.generate(doc_input)

            status_str = getattr(gen_result, "status", "")
            is_success = str(status_str).lower() in ("completed", "success")

            if not is_success:
                return ExecutionResult(
                    task_id=task.task_id,
                    workflow_id=task.workflow_id,
                    success=False,
                    error=TaskError(
                        error_code="DOCUMENT_GENERATION_FAILED",
                        error_message="Document generation failed",
                    ),
                    logs=logs_captured,
                    metrics=ExecutionMetrics(
                        execution_time_ms=(time.time() - start_time) * 1000.0
                    ),
                )

            task.artifact_location = output_path
            checksum = getattr(gen_result, "checksum_sha256", "") or ""
            saved_artifact = await self.artifact_storage_service.register_artifact(
                Artifact(
                    name=os.path.basename(output_path),
                    artifact_type=ArtifactType.REPORTS,
                    filepath=output_path,
                    workflow_id=task.workflow_id,
                    task_id=task.task_id,
                    size_bytes=gen_result.file_size_bytes or 0,
                    checksum=checksum,
                )
            )

            execution_time_ms = (time.time() - start_time) * 1000.0
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=True,
                output={
                    "file_path": output_path,
                    "output_path": output_path,
                    "artifact_location": output_path,
                    "checksum": checksum,
                    "file_size_bytes": gen_result.file_size_bytes,
                },
                artifacts=[saved_artifact],
                logs=logs_captured + [f"Document written successfully to {output_path}"],
                metrics=ExecutionMetrics(execution_time_ms=execution_time_ms),
            )
        except Exception as exc:
            logger.error(f"Document generation failed for task {task.task_id}: {exc}")
            return ExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                error=TaskError(
                    error_code="DOCUMENT_GENERATION_ERROR",
                    error_message=str(exc),
                ),
                logs=logs_captured,
                metrics=ExecutionMetrics(
                    execution_time_ms=(time.time() - start_time) * 1000.0
                ),
            )


def register_document_tool(registry: ToolRegistry) -> Tool:
    """
    Registers the Document Generator tool with the provided ToolRegistry.
    Also registers 'content_tool' alias for planner compatibility.
    """
    doc_tool = Tool(
        name="document_generator",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.document.tool.DocumentToolAdapter",
        dependencies=[],
        required_permissions=[PermissionType.FILE_SYSTEM.value],
    )
    registry.register(doc_tool)

    content_tool = Tool(
        name="content_tool",
        version="1.0.0",
        status=ToolState.READY,
        health=ToolHealth.HEALTHY,
        adapter="app.tools.document.tool.DocumentToolAdapter",
        dependencies=[],
        required_permissions=[PermissionType.FILE_SYSTEM.value],
    )
    registry.register(content_tool)

    logger.info("Successfully registered 'document_generator' and 'content_tool' in ToolRegistry.")
    return doc_tool
