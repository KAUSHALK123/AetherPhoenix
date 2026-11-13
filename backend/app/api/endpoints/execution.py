"""
Execution Bridge Endpoint — POST /api/v1/workflows/execute

Accepts a PlannerOutput JSON, builds SharedWorkflowState, registers a
RuntimeContext in the kernel, and fires PipelineOrchestrator.run_workflow()
as a non-blocking background asyncio.Task.

Returns workflow_id immediately so the frontend can poll
GET /api/v1/dashboard/workflows/{workflow_id} for live status.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class ExecuteWorkflowRequest(BaseModel):
    """Request body for triggering workflow execution."""

    plan_json: str
    session_id: Optional[str] = None
    execution_mode: str = "ASSISTED"


class ExecuteWorkflowResponse(BaseModel):
    """Immediate response returned to frontend so it can start polling."""

    workflow_id: str
    status: str = "RUNNING"
    message: str = (
        "Workflow execution started. Poll /api/v1/dashboard/workflows/{workflow_id} for status."
    )


@router.post("/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(request: ExecuteWorkflowRequest):
    """
    Starts a workflow execution from an approved PlannerOutput JSON plan.

    Non-blocking: fires the orchestrator as a background asyncio task and
    returns the workflow_id immediately for the frontend to poll.
    """
    # 1. Parse the plan JSON
    try:
        plan_data = json.loads(request.plan_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid plan JSON: {e}")

    # 2. Reconstruct workflow_id from plan metadata or generate fresh
    try:
        metadata_data = plan_data.get("metadata", {})
        raw_wf_id = metadata_data.get("workflow_id") or plan_data.get("workflow_id")
        workflow_id = uuid.UUID(raw_wf_id) if raw_wf_id else uuid.uuid4()
    except (ValueError, AttributeError):
        workflow_id = uuid.uuid4()

    goal = plan_data.get("metadata", {}).get("goal") or plan_data.get(
        "workflow_spec", "Autonomous Workflow"
    )
    session_id = request.session_id or str(workflow_id)

    # 3. Build SharedWorkflowState from the PlannerOutput JSON
    try:
        from shared.contracts.task import Task
        from shared.contracts.workflow import (
            ExecutionMode,
            SharedWorkflowState,
            WorkflowMetadata,
            WorkflowStatus,
        )

        tasks_dict = {}
        execution_queue = []

        for task_data in plan_data.get("tasks", []):
            try:
                task = Task.model_validate(task_data)
                tasks_dict[task.task_id] = task
                execution_queue.append(task.task_id)
            except Exception as te:
                logger.warning(f"Could not parse task from plan: {te} — {task_data}")
                continue

        try:
            exec_mode = ExecutionMode(request.execution_mode.upper())
        except ValueError:
            exec_mode = ExecutionMode.ASSISTED

        metadata = WorkflowMetadata(
            workflow_id=workflow_id,
            goal=goal,
            execution_mode=exec_mode,
            status=WorkflowStatus.RUNNING,
        )

        state = SharedWorkflowState(
            metadata=metadata,
            tasks=tasks_dict,
            execution_queue=execution_queue,
        )

    except Exception as e:
        logger.exception("Failed to build SharedWorkflowState")
        raise HTTPException(
            status_code=500, detail=f"Failed to build workflow state: {e}"
        )

    # 4. Register RuntimeContext in kernel
    try:
        from app.runtime.kernel import get_kernel

        kernel = get_kernel()
        context = kernel.create_context(
            session_id=session_id,
            shared_state=state,
        )
        logger.info(
            f"Created RuntimeContext {context.context_id} for workflow {workflow_id}"
        )
    except Exception as e:
        logger.exception("Failed to create RuntimeContext")
        raise HTTPException(
            status_code=500, detail=f"Failed to create runtime context: {e}"
        )

    # 5. Get orchestrator singleton
    try:
        from app.services.agent_factory import get_pipeline_orchestrator

        orchestrator = get_pipeline_orchestrator()
    except Exception as e:
        logger.exception("Failed to initialize PipelineOrchestrator")
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize orchestrator: {e}"
        )

    # 6. Fire workflow in background (non-blocking)
    async def run_workflow_background():
        try:
            logger.info(f"Background execution starting for workflow {workflow_id}")
            final_state = await orchestrator.run_workflow(state, max_retries=3)
            logger.info(
                f"Workflow {workflow_id} finished with status: "
                f"{final_state.metadata.status}"
            )
        except Exception as ex:
            logger.exception(
                f"Unhandled exception in background workflow {workflow_id}: {ex}"
            )

    asyncio.create_task(run_workflow_background())
    logger.info(f"Workflow {workflow_id} dispatched as background task.")

    return ExecuteWorkflowResponse(
        workflow_id=str(workflow_id),
        status="RUNNING",
        message=(
            f"Workflow '{goal}' started. "
            f"Poll /api/v1/dashboard/workflows/{workflow_id} for live status."
        ),
    )
