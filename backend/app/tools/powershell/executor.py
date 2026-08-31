import asyncio
import time
from typing import Optional

from shared.contracts.permission import PermissionType

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager

from .models import ExecutionResult, PowerShellCommand

logger = get_logger(__name__)


class PowerShellExecutor:
    """
    Executes PowerShell commands autonomously in a controlled environment.
    Integrates with Runtime Permission Manager for safety.
    """

    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        self.permission_manager = permission_manager

    def _validate(self, command: str) -> bool:
        """
        Validates the command for obvious prohibited patterns before execution.
        """
        prohibited = [
            "invoke-webrequest",
            "iwr",
            "invoke-restmethod",
            "irm",
            "start-process -nonewwindow",
            "rm -rf",
            "del /f",
            "remove-item",
            "format ",
            "format-volume",
            "clear-disk",
            "drop database",
            "reg delete",
            "stop-computer",
            "restart-computer",
            "set-executionpolicy",
        ]
        cmd_lower = command.lower()
        for p in prohibited:
            if p in cmd_lower:
                return False
        return True

    async def execute(self, cmd: PowerShellCommand) -> ExecutionResult:
        """
        Executes a PowerShell command, captures output, enforces timeout
        and permissions.
        """
        logger.info(f"Preparing to execute PowerShell command: {cmd.command}")

        # Permission check - always enforce if permission_manager configured
        if self.permission_manager:
            try:
                res = self.permission_manager.check_permission(
                    action=cmd.command,
                    permission_type=PermissionType.POWERSHELL,
                    context={"command": cmd.command},
                )
            except TypeError:
                res = self.permission_manager.check_permission(
                    action=cmd.command,
                    permission_type=PermissionType.POWERSHELL,
                )
            is_approved = await res if hasattr(res, "__await__") else bool(res)
            if not is_approved:
                logger.warning(f"Permission denied for command: {cmd.command}")
                raise PermissionDeniedException(
                    f"Permission denied for PowerShell execution: {cmd.command}"
                )

        # Validation check
        if not self._validate(cmd.command):
            logger.error(f"Command validation failed for: {cmd.command}")
            raise PermissionDeniedException("Command contains prohibited patterns.")

        start_time = time.time()
        timeout_occurred = False
        stdout_data, stderr_data = b"", b""
        exit_code = -1

        try:
            process = await asyncio.create_subprocess_exec(
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                cmd.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(), timeout=cmd.timeout_seconds
                )
                exit_code = process.returncode
            except asyncio.TimeoutError:
                timeout_occurred = True
                process.kill()
                stdout_data, stderr_data = await process.communicate()
                exit_code = process.returncode
                logger.warning(
                    f"PowerShell command timed out after {cmd.timeout_seconds}s"
                )

        except Exception as e:
            logger.error(f"Failed to execute PowerShell command: {str(e)}")
            stderr_data = str(e).encode()

        end_time = time.time()
        execution_time_ms = (end_time - start_time) * 1000

        result = ExecutionResult(
            stdout=stdout_data.decode(errors="replace").strip(),
            stderr=stderr_data.decode(errors="replace").strip(),
            exit_code=exit_code if exit_code is not None else -1,
            execution_time_ms=execution_time_ms,
            timeout_occurred=timeout_occurred,
        )

        logger.info(f"Command finished with exit code {result.exit_code}")
        return result
