import asyncio
from typing import Any, Dict, Optional
from uuid import UUID

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import ExecutionResult, TaskError
from shared.contracts.task import TaskStatus
from shared.contracts.workflow import SharedWorkflowState, WorkflowStatus

from app.agents.healing.agent import HealingAgent
from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus
from app.core.logging import get_logger
from app.engine.workflow import WorkflowEngine

logger = get_logger(__name__)


class PipelineOrchestrator:
    """
    Central coordinator responsible for driving the execution of workflows.
    Orchestrates Planner -> WorkflowEngine -> Worker -> Supervisor loops,
    managing dependency resolution, concurrency, retries, and events.
    """

    def __init__(
        self,
        worker_agent: WorkerAgent,
        supervisor_agent: SupervisorAgent,
        event_bus: EventBus,
        healing_agent: Optional[HealingAgent] = None,
    ) -> None:
        self.worker = worker_agent
        self.supervisor = supervisor_agent
        self.event_bus = event_bus
        self.healing = healing_agent

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
        Loads tasks, runs execution loops driven by dependencies,
        runs worker/supervisor steps, handles retries, blocks failures,
        and updates workflow status.
        """
        workflow_id = state.metadata.workflow_id
        logger.info(
            f"Starting workflow execution for: {workflow_id} "
            f"(Goal: '{state.metadata.goal}')"
        )

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
            # Retrieve currently enqueued tasks (copying to avoid
            # mutation issues during iteration)
            queue_snapshot = list(state.execution_queue)

            # Start ready tasks
            for task_id in queue_snapshot:
                task = state.tasks.get(task_id)
                if not task:
                    continue

                # Evaluate dependencies / prerequisites
                prereq_status = (
                    self.supervisor.monitor.parallel_monitor.check_prerequisites(
                        task_id, state
                    )
                )
                logger.debug(
                    f"Task {task_id} ('{task.task_name}') "
                    f"dependency check: {prereq_status}"
                )

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
                            logger.exception(
                                f"Exception during worker execution of task {t.task_id}"
                            )
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
                        validation = await self.supervisor.execute(
                            t, result=res, state=state
                        )

                        # Publish TASK_COMPLETED / TASK_FAILED based on
                        # validation decision
                        if validation.is_valid:
                            t.status = TaskStatus.COMPLETED
                            engine.update_task_status(t.task_id, TaskStatus.COMPLETED)

                            # Persist task output and artifacts in SharedWorkflowState
                            if res.output is not None:
                                state.task_outputs[t.task_name] = res.output
                                state.task_outputs[str(t.task_id)] = res.output
                            if res.artifacts:
                                for art in res.artifacts:
                                    if art not in state.artifacts:
                                        state.artifacts.append(art)

                            await self._emit_orchestrator_event(
                                event_type=EventType.TASK_COMPLETED,
                                workflow_id=workflow_id,
                                task_id=t.task_id,
                                payload={
                                    "output": res.output,
                                    "output_keys": (
                                        list(res.output.keys()) if isinstance(res.output, dict) else []
                                    ),
                                    "artifacts": [
                                        a.model_dump(mode="json") if hasattr(a, "model_dump") else str(a)
                                        for a in res.artifacts
                                    ] if res.artifacts else [],
                                },
                            )
                        else:
                            t.status = TaskStatus.FAILED
                            engine.update_task_status(t.task_id, TaskStatus.FAILED)
                            if res.output is not None:
                                state.task_outputs[t.task_name] = res.output
                                state.task_outputs[str(t.task_id)] = res.output
                            await self._emit_orchestrator_event(
                                event_type=EventType.TASK_FAILED,
                                workflow_id=workflow_id,
                                task_id=t.task_id,
                                payload={
                                    "error_code": (
                                        res.error.error_code
                                        if res.error
                                        else "VALIDATION_FAILED"
                                    ),
                                    "issues": validation.issues,
                                },
                            )

                            # 3. If failed, evaluate and trigger retry
                            retried = await self.supervisor.execute(
                                t,
                                state=state,
                                error=res.error
                                or TaskError(
                                    error_code="VALIDATION_FAILED",
                                    error_message=(
                                        "Supervisor output validation failed."
                                    ),
                                ),
                                max_retries=max_retries,
                            )
                            if retried:
                                logger.info(
                                    f"Task {t.task_id} failed validation. "
                                    "Controlled retry triggered."
                                )
                                await self._emit_orchestrator_event(
                                    event_type=EventType.TASK_RETRIED,
                                    workflow_id=workflow_id,
                                    task_id=t.task_id,
                                    payload={"retry_count": t.retry_count},
                                )
                            else:
                                logger.info(
                                    f"Task {t.task_id} failed validation "
                                    "and is not retryable."
                                )
                                if t.retry_count >= max_retries:
                                    logger.error(
                                        f"Task '{t.task_name}' ({t.task_id}) exhausted maximum retry budget "
                                        f"(K_max={max_retries}). Halting retries and terminating workflow execution."
                                    )
                                    engine.update_task_status(t.task_id, TaskStatus.FAILED)
                                else:
                                    healing_res = None
                                    if self.healing:
                                        logger.info(
                                            f"Invoking Healing Agent for task {t.task_id}"
                                        )
                                        healing_res = await self.healing.execute(
                                            t, result=res, state=state
                                        )

                                    # Generate Planner Feedback
                                    from app.agents.planner.feedback import (
                                        PlannerFeedbackLoop,
                                    )

                                    feedback_loop = PlannerFeedbackLoop(self.event_bus)

                                    failure_report = (
                                        self.supervisor.failure_detector.check_failure(
                                            t, res, state
                                        )
                                    )

                                    feedback = (
                                        await feedback_loop.process_and_publish_feedback(
                                            state=state,
                                            failure_report=failure_report,
                                            healing_result=healing_res,
                                        )
                                    )
                                    state.feedback = feedback

                        return validation

                    # Spawn execution task concurrently
                    running_futures[task_id] = asyncio.create_task(
                        execute_task_with_supervision()
                    )

                elif prereq_status == "BLOCKED":
                    # Prerequisites failed. Set status to BLOCKED and remove from queue
                    state.execution_queue.remove(task_id)
                    engine.update_task_status(task_id, TaskStatus.BLOCKED)

                    # Update progress state to propagate blockages
                    # down the dependency tree
                    self.supervisor.monitor.update_progress_state(state)

                elif prereq_status == "PENDING":
                    # Prerequisites are still in progress. Leave in queue and wait.
                    pass

            # Check running tasks
            if running_futures:
                # Wait for at least one running task to complete
                done, _ = await asyncio.wait(
                    list(running_futures.values()), return_when=asyncio.FIRST_COMPLETED
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
                    # Deadlock check: items exist in queue but none
                    # can run (prereqs pending but no tasks running).
                    # This happens if there's a dependency cycle or
                    # all pending tasks are stuck.
                    logger.error(
                        f"Deadlock detected for workflow {workflow_id}. "
                        "execution_queue has items, but none are ready/running."
                    )
                    break

        # Final progress evaluation and state updates
        self.supervisor.monitor.update_progress_state(state)
        progress = state.progress

        if progress.failed_tasks > 0 or progress.blocked_tasks > 0:
            engine.fail()
            final_event = EventType.WORKFLOW_FAILED
            logger.error(
                f"Workflow {workflow_id} execution FAILED "
                f"(Completed: {progress.completed_tasks}, "
                f"Failed: {progress.failed_tasks}, "
                f"Blocked: {progress.blocked_tasks})"
            )
        else:
            engine.complete()
            final_event = EventType.WORKFLOW_COMPLETED
            logger.info(f"Workflow {workflow_id} execution COMPLETED successfully.")

        # Synthesize final response answering user's original goal
        final_response_payload = await self._generate_final_response(state)
        state.final_response = final_response_payload

        # Emit final workflow event
        await self._emit_orchestrator_event(
            event_type=final_event,
            workflow_id=workflow_id,
            payload={
                "goal": state.metadata.goal,
                "completed_tasks": progress.completed_tasks,
                "total_tasks": progress.total_tasks,
                "answer": final_response_payload.get("answer", ""),
                "raw_output": final_response_payload.get("raw_output", {}),
                "final_response": final_response_payload,
            },
        )

        return state

    def _truncate_for_llm(self, val: Any, max_chars: int = 2000) -> Any:
        """Truncates very large string or list payloads before feeding to LLM synthesis."""
        if isinstance(val, str):
            if len(val) > max_chars:
                return val[:max_chars] + f"\n... [truncated ({len(val) - max_chars} characters omitted)]"
            return val
        elif isinstance(val, list):
            if len(val) > 50:
                truncated_list = [self._truncate_for_llm(x, 500) for x in val[:50]]
                truncated_list.append(f"... [{len(val) - 50} more items truncated]")
                return truncated_list
            return [self._truncate_for_llm(x, 500) for x in val]
        elif isinstance(val, dict):
            return {k: self._truncate_for_llm(v, max_chars) for k, v in val.items()}
        return val

    async def _generate_final_response(self, state: SharedWorkflowState) -> Dict[str, Any]:
        """
        Collects task outputs and artifacts and synthesizes a concise, direct answer
        to the user's original goal, truncating large outputs before feeding to the LLM.
        Explicitly notes errors or unhelpful/empty tool returns.
        """
        import os
        original_goal = state.metadata.goal or "Workflow Execution"
        raw_outputs = state.task_outputs or {}

        clean_outputs: Dict[str, Any] = {}
        for k, v in raw_outputs.items():
            clean_outputs[k] = v

        truncated_outputs = self._truncate_for_llm(clean_outputs, max_chars=2000)

        # Check for task failures or explicit errors
        failed_tasks_info = []
        for fid in state.failed_tasks:
            t = state.tasks.get(fid)
            tname = t.task_name if t else str(fid)
            val = state.validations.get(fid)
            if val and val.issues:
                failed_tasks_info.append(f"Task '{tname}': {'; '.join(val.issues)}")
            else:
                failed_tasks_info.append(f"Task '{tname}' execution failed")

        # 1. Try LLM synthesis if API key is present
        gemini_key = os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if gemini_key or openai_key:
            try:
                import json
                import httpx

                artifacts_summary = [
                    {
                        "name": a.name,
                        "filepath": a.filepath,
                        "type": str(getattr(a, "artifact_type", "file")),
                    }
                    for a in state.artifacts
                ]

                prompt = (
                    f"You are the AetherPhoenix assistant delivering the final answer to the user.\n"
                    f"USER'S ORIGINAL QUESTION / GOAL: {original_goal}\n\n"
                    f"TOOL OUTPUTS:\n{json.dumps(truncated_outputs, default=str, indent=2)}\n\n"
                    f"ARTIFACTS GENERATED:\n{json.dumps(artifacts_summary, default=str, indent=2)}\n\n"
                    f"FAILURES / ISSUES (if any):\n{json.dumps(failed_tasks_info, indent=2)}\n\n"
                    f"INSTRUCTIONS:\n"
                    f"- Write a concise, factual, direct answer addressing the user's question.\n"
                    f"- If the user asked what folders or files exist, list them clearly with bullet points.\n"
                    f"- If a tool returned an error or nothing useful, say so clearly.\n"
                    f"- Do not hallucinate or add items not in the tool outputs."
                )

                if gemini_key:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(url, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            candidate = data.get("candidates", [{}])[0]
                            answer_text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                            if answer_text:
                                return {"answer": answer_text, "raw_output": clean_outputs}
                elif openai_key:
                    url = "https://api.openai.com/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                    }
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(url, headers=headers, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            answer_text = data["choices"][0]["message"]["content"].strip()
                            if answer_text:
                                return {"answer": answer_text, "raw_output": clean_outputs}
            except Exception as e:
                logger.warning(
                    f"LLM final response synthesis failed, falling back to deterministic extraction: {e}"
                )

        # 2. Deterministic Fallback Synthesis
        # Check if entire workflow failed or tasks failed without substantive output
        if failed_tasks_info and not state.artifacts and not any(
            isinstance(v, dict)
            and (v.get("items") or (isinstance(v.get("metadata"), dict) and v["metadata"].get("items")) or v.get("stdout"))
            for v in clean_outputs.values()
        ):
            answer = (
                f"The workflow encountered an error and could not complete your request '{original_goal}':\n"
                + "\n".join(f"- {msg}" for msg in failed_tasks_info)
            )
            return {"answer": answer, "raw_output": clean_outputs}

        # Check for file explorer / directory inspection outputs
        found_folders = []
        found_files = []
        target_path = None

        for out in clean_outputs.values():
            if isinstance(out, dict):
                items = None
                if isinstance(out.get("metadata"), dict) and "items" in out["metadata"]:
                    items = out["metadata"]["items"]
                elif "items" in out:
                    items = out["items"]

                if out.get("target_path"):
                    target_path = out.get("target_path")

                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get("name", "")
                            is_dir = item.get("is_dir") or item.get("type") == "folder"
                            if is_dir:
                                found_folders.append(name)
                            else:
                                found_files.append(name)
                        elif isinstance(item, str):
                            found_folders.append(item)

        lower_goal = original_goal.lower()
        if any(w in lower_goal for w in ["folder", "directory", "drive", "d:", "c:"]):
            if found_folders or found_files:
                path_display = f" in '{target_path}'" if target_path else ""
                lines = [f"Here are the folders found{path_display}:"]
                display_items = found_folders if found_folders else found_files
                for f in display_items:
                    lines.append(f"- {f}")
                if found_files and found_folders and "file" in lower_goal:
                    lines.append(f"\nFiles found{path_display}:")
                    for fl in found_files:
                        lines.append(f"- {fl}")
                return {"answer": "\n".join(lines), "raw_output": clean_outputs}
            elif any("file_explorer" in str(getattr(t, "required_tool", "")) for t in state.tasks.values()):
                path_display = f" in '{target_path}'" if target_path else ""
                return {
                    "answer": f"The directory inspection ran successfully, but found no folders or files{path_display}.",
                    "raw_output": clean_outputs,
                }

        # Check for stdout / terminal output
        for out in clean_outputs.values():
            if isinstance(out, dict) and "stdout" in out:
                stdout_text = str(out["stdout"]).strip()
                if stdout_text:
                    return {
                        "answer": f"Command executed successfully:\n```\n{stdout_text}\n```",
                        "raw_output": clean_outputs,
                    }
                else:
                    return {
                        "answer": "Command executed successfully with no output returned.",
                        "raw_output": clean_outputs,
                    }

        # Check for generated artifacts
        if state.artifacts:
            art_lines = [
                f"Workflow completed successfully. Generated {len(state.artifacts)} artifact(s):"
            ]
            for a in state.artifacts:
                art_lines.append(f"- {a.name} ({a.filepath})")
            return {"answer": "\n".join(art_lines), "raw_output": clean_outputs}

        # Check for tool errors in output dicts
        for out in clean_outputs.values():
            if isinstance(out, dict):
                if out.get("is_error") or out.get("error"):
                    err_val = out.get("error") or out.get("message") or "Unknown tool error"
                    return {
                        "answer": f"The tool executed, but returned an error: {err_val}",
                        "raw_output": clean_outputs,
                    }

        # If clean outputs is empty or has only empty values
        if not clean_outputs or all(not v for v in clean_outputs.values()):
            return {
                "answer": f"The workflow completed, but the tool returned no output or findings for '{original_goal}'.",
                "raw_output": clean_outputs,
            }

        return {
            "answer": f"Workflow completed successfully for '{original_goal}'.",
            "raw_output": clean_outputs,
        }
