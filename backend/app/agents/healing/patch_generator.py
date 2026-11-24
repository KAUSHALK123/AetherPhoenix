import copy
import logging
import os
import re
from typing import Any, Dict, Optional
from uuid import UUID

from shared.contracts.task import Task, TaskCategory

from app.core.permissions.models import ExecutionMode
from app.core.permissions.policies import (
    evaluate_task_risk_and_permissions,
    risk_rank,
)

logger = logging.getLogger(__name__)


class LLMParameterPatcher:
    """
    Bounded Parameter Repair Patcher for Self-Healing.

    Implements deterministic parameter sanitization followed by an asynchronous
    fallback LLM argument synthesizer constrained by:
    1. Explicit call budgets: K_llm = 1 call per task attempt.
    2. Monotonic privilege-invariance: repaired parameters MUST NOT escalate risk
       or introduce unapproved permissions beyond the original task baseline.
    """

    def __init__(
        self,
        permission_manager: Optional[Any] = None,
        max_llm_calls_per_attempt: int = 1,
    ):
        self.permission_manager = permission_manager
        self.max_llm_calls_per_attempt = max_llm_calls_per_attempt
        self._llm_call_count: Dict[UUID, int] = {}

    def repair_parameters(
        self,
        task: Task,
        error: Any,
        schema: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.AUTONOMOUS,
    ) -> Dict[str, Any]:
        """
        Synchronous/Deterministic repair entrypoint.
        Attempts rule-based repair first; falls back to bounded repair logic.
        """
        err_msg = str(
            getattr(error, "error_message", None)
            or getattr(error, "message", None)
            or str(error)
        ).lower()
        err_code = str(
            getattr(error, "error_code", None) or getattr(error, "code", None) or ""
        ).upper()

        patched_inputs = copy.deepcopy(getattr(task, "inputs", None) or {})

        # 1. Deterministic repair for File Not Found / Path Errors
        if (
            "file_not_found" in err_code
            or "file not found" in err_msg
            or "no such file" in err_msg
            or "path" in err_msg
        ):
            patched_inputs["path"] = "."
            patched_inputs["patched"] = True
            logger.info(
                "Deterministic patch applied: sanitized path to safe default '.'"
            )

        # 2. Deterministic repair for Syntax / Command Errors
        elif (
            "syntax_error" in err_code
            or "syntax" in err_msg
            or "command" in err_msg
            or "near '|'" in err_msg
        ):
            raw_cmd = str(patched_inputs.get("command", "") or "")
            # Strip invalid pipe symbols or corrupted flags
            cleaned_cmd = re.sub(r"\|\s*$", "", raw_cmd).strip()
            cleaned_cmd = re.sub(r"\|\s*\|", "|", cleaned_cmd)
            if not cleaned_cmd or cleaned_cmd == raw_cmd:
                # Fall back to safe diagnostic command matching task intent
                cleaned_cmd = (
                    "ipconfig"
                    if "ip" in task.task_name.lower() or "net" in task.task_name.lower()
                    else "whoami"
                )
            patched_inputs["command"] = cleaned_cmd
            patched_inputs["patched"] = True
            logger.info(
                "Deterministic patch applied: sanitized command syntax to '%s'",
                cleaned_cmd,
            )

        # 3. Deterministic repair for Invalid Arguments / Missing URLs
        elif (
            "invalid_arguments" in err_code
            or "malformed_input" in err_code
            or "invalid argument" in err_msg
            or "missing required parameter" in err_msg
            or "url" in err_msg
        ):
            if (
                task.category == TaskCategory.BROWSER
                or "browser" in str(task.required_tool).lower()
            ):
                patched_inputs["action"] = "navigate"
                patched_inputs["url"] = "http://localhost:8000/health"
            elif (
                task.category == TaskCategory.FILE_SYSTEM
                or "file" in str(task.required_tool).lower()
            ):
                patched_inputs["action"] = "detect_existence"
                patched_inputs["path"] = "."
            elif (
                task.category == TaskCategory.PPT_GENERATION
                or "ppt" in str(task.required_tool).lower()
            ):
                if "slides" not in patched_inputs or not patched_inputs["slides"]:
                    patched_inputs["slides"] = [
                        {
                            "title": "Overview",
                            "slide_type": "TITLE",
                            "bullets": ["Introduction"],
                        },
                        {
                            "title": "Details",
                            "slide_type": "CONTENT",
                            "bullets": ["Key points"],
                        },
                    ]
                if "title" not in patched_inputs:
                    patched_inputs["title"] = task.task_name
            patched_inputs["patched"] = True
            logger.info(
                "Deterministic patch applied: repaired missing arguments for %s",
                task.task_name,
            )

        else:
            patched_inputs["patched"] = True

        # Enforce Monotonic Privilege-Invariance
        orig_risk, orig_perms, _, _ = evaluate_task_risk_and_permissions(
            task, mode=mode
        )
        candidate_task = task.model_copy(deep=True)
        candidate_task.inputs = patched_inputs

        cand_risk, cand_perms, cand_decision, _ = evaluate_task_risk_and_permissions(
            candidate_task, mode=mode
        )
        if not cand_decision.allowed or risk_rank(cand_risk) > risk_rank(orig_risk):
            logger.warning(
                "Patched parameters rejected by monotonic privilege invariant. Reverting to original."
            )
            return getattr(task, "inputs", {}) or {}

        return patched_inputs

    async def synthesize_repaired_parameters(
        self,
        task: Task,
        error: Any,
        schema: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.AUTONOMOUS,
    ) -> Dict[str, Any]:
        """
        Asynchronous fallback LLM parameter repair method constrained by K_llm=1 budget.
        Invoked when deterministic repair is insufficient.
        """
        task_id = task.task_id
        current_calls = self._llm_call_count.get(task_id, 0)
        if current_calls >= self.max_llm_calls_per_attempt:
            logger.warning(
                "LLMParameterPatcher exhausted execution budget (K_llm=%d) for task %s",
                self.max_llm_calls_per_attempt,
                task_id,
            )
            return self.repair_parameters(task, error, schema, mode=mode)

        self._llm_call_count[task_id] = current_calls + 1

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                import httpx

                prompt = (
                    f"You are the AetherPhoenix Self-Healing Parameter Repair module.\n"
                    f"A task failed with an input/parameter error.\n"
                    f"Task Name: {task.task_name}\n"
                    f"Tool: {task.required_tool}\n"
                    f"Current Inputs: {task.inputs}\n"
                    f"Error: {error}\n"
                    f"Schema: {schema or {}}\n\n"
                    f"Synthesize corrected JSON parameters for the task inputs. Return ONLY valid JSON."
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"response_mime_type": "application/json"},
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        import json

                        data = resp.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        repaired = json.loads(raw_text)
                        if isinstance(repaired, dict):
                            repaired["patched"] = True
                            # Validate privilege invariance
                            candidate = task.model_copy(deep=True)
                            candidate.inputs = repaired
                            c_risk, _, c_dec, _ = evaluate_task_risk_and_permissions(
                                candidate, mode=mode
                            )
                            orig_risk, _, _, _ = evaluate_task_risk_and_permissions(
                                task, mode=mode
                            )
                            if c_dec.allowed and risk_rank(c_risk) <= risk_rank(
                                orig_risk
                            ):
                                return repaired
            except Exception as e:
                logger.warning("LLM parameter synthesis call failed: %s", e)

        # Fall back to deterministic repair if LLM unavailable or rejected
        return self.repair_parameters(task, error, schema, mode=mode)
