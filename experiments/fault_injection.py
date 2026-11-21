"""
Phoenix Agents: Dual-Mode Fault Injection Harness
=================================================
Supports both synthetic return-value injection and real-exception injection
for empirical evaluation and robustness validation.

Fault Classes:
1. TIMEOUT: asyncio.wait_for timeout
2. MISSING_RESOURCE: real FileNotFoundError
3. TOOL_ADAPTER_FAILURE: non-zero subprocess return (CalledProcessError)
4. INVALID_ACTION / PERMISSION_DENIED: real PermissionError on read-only resource
5. STATE_INCONSISTENCY / UNMAPPED: unmapped custom exception (UnmappedCustomException)
"""

import asyncio
import os
import random
import stat
import subprocess
import sys
import tempfile
import uuid
from typing import Any, Dict, Optional, Union

from shared.contracts.execution import ExecutionResult, TaskError
from shared.contracts.task import Task


class UnmappedCustomException(Exception):
    """Custom unmapped application-level exception for state/consistency fault tests."""
    pass


class FaultInjector:
    """
    Harness for injecting either synthetic error structures or real OS/runtime exceptions.
    Mode: "synthetic" | "real_exception"
    """

    def __init__(self, mode: str = "synthetic", seed: int = 42) -> None:
        if mode not in ("synthetic", "real_exception"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'synthetic' or 'real_exception'.")
        self.mode = mode
        self.seed = seed
        self.rng = random.Random(seed)

    def set_seed(self, seed: int) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    async def generate_fault(
        self,
        fault_class: str,
        task: Optional[Task] = None,
    ) -> Union[ExecutionResult, Exception, TaskError]:
        """
        Generates or triggers a fault matching the requested fault class.
        In 'synthetic' mode: returns an ExecutionResult / TaskError.
        In 'real_exception' mode: produces a real exception object or raises it.
        """
        fc = fault_class.upper()

        if self.mode == "synthetic":
            return self._generate_synthetic(fc, task)
        else:
            return await self._generate_real_exception(fc, task)

    def _generate_synthetic(self, fault_class: str, task: Optional[Task] = None) -> ExecutionResult:
        t_id = task.task_id if task else uuid.uuid4()
        wf_id = task.workflow_id if task else uuid.uuid4()

        if fault_class in ("TIMEOUT", "DEADLINE_EXCEEDED"):
            err = TaskError(
                error_code="TIMEOUT",
                error_message="Task execution exceeded deadline of 30.0s (synthetic timeout)",
                is_recoverable=True,
            )
        elif fault_class in ("MISSING_RESOURCE", "FILE_NOT_FOUND"):
            err = TaskError(
                error_code="FILE_NOT_FOUND",
                error_message="FileNotFoundError: [Errno 2] No such file or directory: 'synthetic_missing_file.txt'",
                is_recoverable=True,
            )
        elif fault_class in ("TOOL_ADAPTER_FAILURE", "COMMAND_FAILED"):
            err = TaskError(
                error_code="COMMAND_FAILED",
                error_message="Subprocess returned non-zero exit status 1: Command failed in adapter",
                is_recoverable=True,
            )
        elif fault_class in ("TOOL_UNAVAILABLE", "TOOL_NOT_FOUND"):
            err = TaskError(
                error_code="TOOL_UNAVAILABLE",
                error_message="ToolUnavailableException: browser_tool is not registered or unavailable on host",
                is_recoverable=True,
            )
        elif fault_class in ("INVALID_ACTION", "PERMISSION_DENIED"):
            err = TaskError(
                error_code="PERMISSION_DENIED",
                error_message="PermissionError: [Errno 13] Permission denied on protected system directory",
                is_recoverable=False,
            )
        else:  # UNMAPPED / STATE_INCONSISTENCY
            err = TaskError(
                error_code="UNMAPPED_ERROR",
                error_message="UnmappedCustomException: Arbitrary unmapped internal state fault",
                is_recoverable=False,
            )

        return ExecutionResult(
            task_id=t_id,
            workflow_id=wf_id,
            success=False,
            error=err,
            output={"mode": self.mode, "fault_class": fault_class, "seed": self.seed},
        )

    async def _generate_real_exception(self, fault_class: str, task: Optional[Task] = None) -> Exception:
        """Triggers and captures actual runtime / OS exceptions."""
        if fault_class in ("TIMEOUT", "DEADLINE_EXCEEDED"):
            try:
                # Real asyncio timeout
                await asyncio.wait_for(asyncio.sleep(1.0), timeout=0.0001)
            except Exception as e:
                return e

        elif fault_class in ("MISSING_RESOURCE", "FILE_NOT_FOUND"):
            try:
                # Real FileNotFoundError
                nonexistent = os.path.join(tempfile.gettempdir(), f"phoenix_missing_{uuid.uuid4().hex}.dat")
                with open(nonexistent, "r", encoding="utf-8") as f:
                    _ = f.read()
            except Exception as e:
                return e

        elif fault_class in ("TOOL_ADAPTER_FAILURE", "COMMAND_FAILED"):
            try:
                # Real non-zero subprocess return
                subprocess.run(
                    [sys.executable, "-c", "import sys; sys.exit(42)"],
                    check=True,
                    capture_output=True,
                )
            except Exception as e:
                return e

        elif fault_class in ("TOOL_UNAVAILABLE", "TOOL_NOT_FOUND"):
            from app.core.exceptions import ToolNotFoundException
            return ToolNotFoundException("ToolNotFoundException: browser_tool is not registered or unavailable on host")

        elif fault_class in ("INVALID_ACTION", "PERMISSION_DENIED"):
            temp_file = None
            try:
                # Real PermissionError on read-only temp file
                fd, temp_file = tempfile.mkstemp(prefix="phoenix_readonly_")
                os.close(fd)
                os.chmod(temp_file, stat.S_IREAD)
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write("disallowed write")
            except Exception as e:
                return e
            finally:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.chmod(temp_file, stat.S_IWRITE)
                        os.remove(temp_file)
                    except Exception:
                        pass

        else:  # STATE_INCONSISTENCY / UNMAPPED
            return UnmappedCustomException("Arbitrary unmapped internal state inconsistency fault")

        return RuntimeError("Failed to trigger real exception")
