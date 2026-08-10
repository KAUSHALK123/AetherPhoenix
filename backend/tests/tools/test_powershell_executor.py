import pytest
import asyncio

from app.tools.powershell.models import PowerShellCommand
from app.tools.powershell.executor import PowerShellExecutor
from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from shared.contracts.permission import PermissionType

class MockPermissionManager(PermissionManager):
    def __init__(self, should_approve=True):
        self.should_approve = should_approve
        
    async def check_permission(self, action: str, permission_type: PermissionType) -> bool:
        return self.should_approve

@pytest.fixture
def executor():
    return PowerShellExecutor(permission_manager=MockPermissionManager(should_approve=True))

@pytest.fixture
def denied_executor():
    return PowerShellExecutor(permission_manager=MockPermissionManager(should_approve=False))

@pytest.mark.asyncio
async def test_safe_command_execution(executor):
    cmd = PowerShellCommand(command="Write-Output 'Hello World'")
    result = await executor.execute(cmd)
    
    assert result.exit_code == 0
    assert "Hello World" in result.stdout
    assert not result.timeout_occurred

@pytest.mark.asyncio
async def test_command_failure(executor):
    cmd = PowerShellCommand(command="Exit 1")
    result = await executor.execute(cmd)
    
    assert result.exit_code == 1

@pytest.mark.asyncio
async def test_invalid_command_validation(executor):
    cmd = PowerShellCommand(command="Invoke-WebRequest https://example.com")
    with pytest.raises(PermissionDeniedException) as excinfo:
        await executor.execute(cmd)
        
    assert "prohibited patterns" in str(excinfo.value)

@pytest.mark.asyncio
async def test_permission_denial(denied_executor):
    cmd = PowerShellCommand(command="Write-Output 'Denied'", require_approval=True)
    with pytest.raises(PermissionDeniedException) as excinfo:
        await denied_executor.execute(cmd)
        
    assert "Permission denied" in str(excinfo.value)

@pytest.mark.asyncio
async def test_timeout_handling(executor):
    # Sleep for 3 seconds, but timeout is 1 second
    cmd = PowerShellCommand(command="Start-Sleep -Seconds 3", timeout_seconds=1)
    result = await executor.execute(cmd)
    
    assert result.timeout_occurred is True
    # The exact exit code after kill might vary by OS, but timeout_occurred is the key flag.

@pytest.mark.asyncio
async def test_capture_stderr(executor):
    # Output to stderr
    cmd = PowerShellCommand(command="Write-Error 'Test Error'")
    result = await executor.execute(cmd)
    
    assert result.exit_code == 0 or result.exit_code == 1 # Write-Error sets $LASTEXITCODE in some PS versions but not always.
    assert "Test Error" in result.stderr
