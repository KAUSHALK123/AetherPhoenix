# PowerShell Executor Module

The PowerShell Executor provides a controlled runtime environment for executing system-level PowerShell commands on behalf of the Worker Agent.

## Features
- **Execution Interface**: Validates and executes `PowerShellCommand` configurations.
- **Permission Integration**: Commands requiring approval are checked against the `PermissionManager`.
- **Validation**: Contains an internal blacklist of explicitly prohibited commands (e.g., silent process launching, untrusted web requests).
- **Timeouts**: Supports strict timeout thresholds.
- **Output Capture**: Fully captures `stdout`, `stderr`, and `exit_code`.

## Dependencies
- Integration with `app.core.permissions.manager.PermissionManager` for access control.
- Integration with `app.core.logging.logger` for execution telemetry.
