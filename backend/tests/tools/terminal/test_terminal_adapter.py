import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from shared.contracts.task import Task, TaskCategory, TaskType
from app.tools.terminal.adapter import TerminalToolAdapter


@pytest.fixture
def terminal_adapter():
    return TerminalToolAdapter()


def create_terminal_task(command: str) -> Task:
    return Task(
        workflow_id=uuid4(),
        task_name="test_terminal",
        description="Test terminal",
        task_type=TaskType.LEAF,
        category=TaskCategory.TERMINAL,
        required_tool="terminal_tool",
        expected_output="Terminal output",
        inputs={"command": command},
    )


def test_terminal_risk_assessment(terminal_adapter):
    assert terminal_adapter._assess_risk("ls -la") == "LOW"
    assert terminal_adapter._assess_risk("python --version") == "LOW"
    assert terminal_adapter._assess_risk("npm install express") == "MEDIUM"
    assert terminal_adapter._assess_risk("rm -rf /") == "HIGH"
    assert terminal_adapter._assess_risk("del C:\\Windows\\System32") == "HIGH"


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_shell")
async def test_terminal_execute_success(mock_exec, terminal_adapter):
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"hello world\n", b"")
    mock_process.returncode = 0
    mock_exec.return_value = mock_process

    task = create_terminal_task("echo hello world")
    result = await terminal_adapter.execute(task)

    assert result.success is True
    assert result.output["output"] == "hello world"


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_shell")
async def test_terminal_execute_failure(mock_exec, terminal_adapter):
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"command not found: foobar")
    mock_process.returncode = 127
    mock_exec.return_value = mock_process

    task = create_terminal_task("foobar")
    result = await terminal_adapter.execute(task)

    assert result.success is False
    assert result.error.error_code == "TERMINAL_COMMAND_FAILED"
    assert result.error.error_message == "command not found: foobar"
