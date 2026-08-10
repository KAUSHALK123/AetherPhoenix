from typing import Optional
from pydantic import BaseModel, Field


class PowerShellCommand(BaseModel):
    """Command specification for the PowerShell executor."""
    
    command: str = Field(..., description="The PowerShell command string to execute")
    timeout_seconds: int = Field(default=30, description="Execution timeout in seconds")
    require_approval: bool = Field(default=True, description="Whether this command needs permission manager approval")


class ExecutionResult(BaseModel):
    """Result of a PowerShell command execution."""
    
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    timeout_occurred: bool = False
