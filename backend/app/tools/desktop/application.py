import os
import shutil
import subprocess
from typing import List, Optional

try:
    from pywinauto import Application
except (ImportError, Exception):
    Application = None

from app.core.logging.logger import get_logger
from app.tools.desktop.exceptions import (
    ApplicationLaunchError,
    ApplicationNotFoundError,
    ApplicationTerminationError,
    ApplicationUnavailableError,
)
from app.tools.desktop.models import ApplicationInfo

logger = get_logger(__name__)


class ApplicationActionError(ApplicationLaunchError):
    """Backwards-compatible error for application actions."""

    pass


class ApplicationController:
    """
    Controlled abstraction for desktop application execution, monitoring,
    and termination. Guarantees that applications are validated and tracked.
    """

    # Commonly allowed / standard desktop application names / binaries
    STANDARD_ALLOWED_APPS = {
        "notepad",
        "notepad.exe",
        "calc",
        "calc.exe",
        "calculator",
        "calculator.exe",
        "explorer",
        "explorer.exe",
        "mspaint",
        "mspaint.exe",
        "wordpad",
        "wordpad.exe",
        "winword",
        "winword.exe",
        "excel",
        "excel.exe",
        "powerpnt",
        "powerpnt.exe",
        "chrome",
        "chrome.exe",
        "msedge",
        "msedge.exe",
        "code",
        "code.cmd",
        "code.exe",
    }

    # Prohibited executable patterns to prevent arbitrary dangerous execution
    PROHIBITED_COMMANDS = {
        "powershell",
        "powershell.exe",
        "cmd",
        "cmd.exe",
        "bash",
        "sh",
        "wscript",
        "cscript",
        "mshta",
        "regsvr32",
        "rundll32",
        "certutil",
        "vssadmin",
        "format",
        "del",
        "rmdir",
    }

    @classmethod
    def validate_app_executable(
        cls, app_path_or_name: str, allowed_apps: Optional[List[str]] = None
    ) -> str:
        """
        Validates the application against prohibited commands and optional whitelist.
        Returns the resolved executable path or command.
        """
        raw_target = app_path_or_name.strip()
        if not raw_target:
            raise ApplicationNotFoundError("Application name or path cannot be empty.")

        base_name = os.path.basename(raw_target).lower()

        # Check prohibited commands
        if base_name in cls.PROHIBITED_COMMANDS:
            raise ApplicationUnavailableError(
                f"Execution of '{base_name}' is prohibited via Desktop Controller."
            )

        # Check optional allowlist
        if allowed_apps is not None:
            normalized_allowed = [os.path.basename(a).lower() for a in allowed_apps]
            if (
                base_name not in normalized_allowed
                and raw_target.lower() not in normalized_allowed
            ):
                raise ApplicationUnavailableError(
                    f"Application '{app_path_or_name}' is not in the permitted list."
                )

        # Check if full path exists or if executable can be found in PATH
        if os.path.isabs(raw_target):
            if not os.path.exists(raw_target):
                raise ApplicationNotFoundError(
                    f"Application executable not found at path: {raw_target}"
                )
            return raw_target
        else:
            # Check in PATH
            resolved = shutil.which(raw_target)
            if resolved:
                return resolved

            # If not in path, check if it's a known standard system app
            if base_name in cls.STANDARD_ALLOWED_APPS:
                return raw_target

            # Try common Windows paths if on Windows
            system_root = os.environ.get("SystemRoot", "C:\\Windows")
            candidate_paths = [
                os.path.join(system_root, "System32", raw_target),
                os.path.join(system_root, raw_target),
            ]
            for cp in candidate_paths:
                if os.path.exists(cp) or (
                    not cp.endswith(".exe") and os.path.exists(cp + ".exe")
                ):
                    return cp

            # If still unresolved and contains path separators, fail
            if os.path.sep in raw_target or "/" in raw_target:
                raise ApplicationNotFoundError(
                    f"Application not found at path: {raw_target}"
                )

            return raw_target

    @classmethod
    def launch_app(
        cls,
        app_path: str,
        args: Optional[List[str]] = None,
        timeout: float = 10.0,
        working_dir: Optional[str] = None,
        allowed_apps: Optional[List[str]] = None,
    ) -> ApplicationInfo:
        """
        Safely launches a permitted desktop application and returns ApplicationInfo.
        """
        resolved_path = cls.validate_app_executable(app_path, allowed_apps=allowed_apps)
        logger.info(f"Launching application: {resolved_path} with args: {args}")

        try:
            full_cmd = [resolved_path] + (args or [])
            if Application is not None:
                # Use pywinauto if available
                cmd_str = (
                    subprocess.list2cmdline(full_cmd)
                    if args
                    else (
                        f'"{resolved_path}"' if " " in resolved_path else resolved_path
                    )
                )
                app = Application(backend="uia").start(cmd_str, timeout=timeout)
                pid = getattr(app, "process", None)
                if pid is None and hasattr(app, "process_id"):
                    pid = app.process_id
                if pid is None:
                    # Fallback PID
                    pid = os.getpid()
            else:
                # Fallback to subprocess
                proc = subprocess.Popen(full_cmd, cwd=working_dir or os.getcwd())
                pid = proc.pid

            app_name = os.path.basename(resolved_path)
            return ApplicationInfo(
                process_id=pid,
                name=app_name,
                path=resolved_path,
                title=app_name,
                status="running",
            )
        except ApplicationNotFoundError:
            raise
        except ApplicationUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Failed to launch application '{app_path}': {e}")
            raise ApplicationActionError(f"Failed to launch {app_path}") from e

    @classmethod
    def terminate_app(
        cls,
        pid: Optional[int] = None,
        title: Optional[str] = None,
        force: bool = False,
        timeout: float = 5.0,
    ) -> bool:
        """
        Safely closes or terminates an application by Process ID or Title.
        """
        logger.info(
            f"Terminating application (PID: {pid}, Title: {title}, Force: {force})"
        )

        if pid is None and not title:
            raise ApplicationTerminationError("Either PID or Title must be provided.")

        try:
            terminated = False

            if pid is not None:
                # Try OS process termination
                try:
                    import psutil

                    if psutil.pid_exists(pid):
                        proc = psutil.Process(pid)
                        if force:
                            proc.kill()
                        else:
                            proc.terminate()
                        try:
                            proc.wait(timeout=timeout)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        terminated = True
                except ImportError:
                    # Fallback via os.kill or taskkill
                    if os.name == "nt":
                        cmd = ["taskkill", "/PID", str(pid)]
                        if force:
                            cmd.append("/F")
                        res = subprocess.run(
                            cmd,
                            capture_output=True,
                            timeout=timeout,
                        )
                        terminated = res.returncode == 0
                    else:
                        import signal

                        sig = signal.SIGKILL if force else signal.SIGTERM
                        os.kill(pid, sig)
                        terminated = True

            elif title:
                # Terminate by window title using pywinauto or taskkill
                if Application is not None:
                    try:
                        app = Application(backend="uia").connect(
                            title=title, timeout=timeout
                        )
                        if force:
                            app.kill()
                        else:
                            app.top_window().close()
                        terminated = True
                    except Exception as pywin_err:
                        logger.warning(
                            f"pywinauto termination by title failed: {pywin_err}"
                        )

                if not terminated and os.name == "nt":
                    cmd = ["taskkill", "/FI", f"WINDOWTITLE eq {title}"]
                    if force:
                        cmd.append("/F")
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=timeout,
                    )
                    terminated = res.returncode == 0

            if not terminated and pid is not None:
                raise ApplicationNotFoundError(f"Process with PID {pid} not found.")

            return True

        except ApplicationNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to terminate application (PID: {pid}, Title: {title}): {e}"
            )
            raise ApplicationTerminationError(
                f"Failed to terminate application: {e}"
            ) from e

    # Legacy methods for full backwards compatibility
    @staticmethod
    def launch(app_path: str):
        """Legacy helper matching existing signature."""
        logger.info(f"Launching application: {app_path}")
        try:
            if Application is not None:
                app = Application(backend="uia").start(app_path)
                return app
            else:
                proc = subprocess.Popen(app_path)
                return proc
        except Exception as e:
            logger.error(f"Failed to launch application: {e}")
            raise ApplicationActionError(f"Failed to launch {app_path}") from e

    @staticmethod
    def connect(title: str):
        """Legacy helper matching existing signature."""
        logger.info(f"Connecting to application with title: {title}")
        try:
            if Application is not None:
                app = Application(backend="uia").connect(title=title)
                return app
            else:
                raise ApplicationActionError(
                    f"Failed to connect to {title}: pywinauto not available"
                )
        except Exception as e:
            logger.error(f"Failed to connect to application: {e}")
            raise ApplicationActionError(f"Failed to connect to {title}") from e
