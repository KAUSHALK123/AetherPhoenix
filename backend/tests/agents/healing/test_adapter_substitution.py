from uuid import uuid4

import pytest
from shared.contracts.execution import ExecutionResult, TaskError
from shared.contracts.permission import RiskLevel
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.tool import Tool, ToolHealth, ToolState
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.error_parser import ErrorParser
from app.agents.healing.models import ErrorCategory
from app.agents.healing.self_healing_loop import SelfHealingLoop
from app.core.exceptions import ToolExecutionException, ToolNotFoundException
from app.tools.browser_extension.controller import BrowserExtensionActionError
from app.tools.registry import ToolRegistry


def test_error_parser_classifies_real_adapter_signatures():
    parser = ErrorParser()

    # 1. Real adapter exception classes
    exc_list = [
        ToolNotFoundException("Tool not found: browser_tool"),
        ToolExecutionException("Tool execution crashed: terminal_tool"),
        BrowserExtensionActionError("Browser extension failed to connect"),
    ]
    for exc in exc_list:
        parsed = parser.parse(exc)
        assert (
            parsed.category == ErrorCategory.TOOL_UNAVAILABLE
        ), f"Expected {type(exc).__name__} to be TOOL_UNAVAILABLE, got {parsed.category}"

    # 2. Real adapter error codes emitted across tools
    adapter_codes = [
        "TOOL_UNAVAILABLE",
        "TOOL_NOT_FOUND",
        "TOOL_ERROR",
        "TOOL_EXECUTION_ERROR",
        "ADAPTER_ERROR",
        "TERMINAL_EXECUTION_ERROR",
        "GIT_EXECUTION_ERROR",
        "BROWSER_EXTENSION_ERROR",
        "OCR_EXTRACTION_FAILED",
        "PPT_GENERATION_FAILED",
        "WEB_RESEARCH_FAILED",
        "EXPORT_FAILED",
    ]
    for code in adapter_codes:
        exec_res = ExecutionResult(
            task_id=uuid4(),
            workflow_id=uuid4(),
            success=False,
            error=TaskError(
                error_code=code,
                error_message=f"Simulated adapter failure with code {code}",
                is_recoverable=True,
            ),
        )
        parsed = parser.parse(exec_res)
        assert (
            parsed.category == ErrorCategory.TOOL_UNAVAILABLE
        ), f"Expected code {code} to be TOOL_UNAVAILABLE, got {parsed.category}"


@pytest.mark.asyncio
async def test_adapter_substitution_end_to_end_through_registry():
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="browser_tool",
            status=ToolState.UNAVAILABLE,
            health=ToolHealth.FAILED,
            adapter="BrowserAdapter",
        )
    )
    registry.register(
        Tool(
            name="web_research_tool",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="WebResearchAdapter",
        )
    )

    loop = SelfHealingLoop(tool_registry=registry)
    wf_id = uuid4()
    t_id = uuid4()
    task = Task(
        task_id=t_id,
        workflow_id=wf_id,
        task_name="Scrape Documentation",
        description="Scrape and extract developer docs",
        category=TaskCategory.WEB_RESEARCH,
        priority=TaskPriority.HIGH,
        status=TaskStatus.FAILED,
        required_tool="browser_tool",
        inputs={"url": "https://docs.python.org"},
        risk_level=RiskLevel.LOW.value,
        expected_output="done",
    )
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=wf_id,
            goal="Test adapter substitution",
            status=WorkflowStatus.RUNNING,
        ),
        tasks={t_id: task},
    )

    fault = ExecutionResult(
        task_id=t_id,
        workflow_id=wf_id,
        success=False,
        error=TaskError(
            error_code="TOOL_UNAVAILABLE",
            error_message="ToolUnavailableException: browser_tool is unavailable",
            is_recoverable=True,
        ),
    )

    result = await loop.process_failure(task, fault, state)
    assert result.success is True
    assert result.recovery_strategy == "ALTERNATIVE_TOOL"
    assert len(result.replacement_tasks) == 1
    sub_task = result.replacement_tasks[0]
    assert sub_task.required_tool == "web_research_tool"
    assert sub_task.workflow_id == wf_id


@pytest.mark.asyncio
async def test_adapter_substitution_rejected_when_higher_risk():
    """Substitute adapter must never be higher risk than original (monotonic risk invariant)."""
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="web_research",
            status=ToolState.UNAVAILABLE,
            health=ToolHealth.FAILED,
            adapter="WebResearchAdapter",
        )
    )
    # Only available substitute in registry is terminal_tool, which has HIGH risk
    registry.register(
        Tool(
            name="terminal_tool",
            status=ToolState.READY,
            health=ToolHealth.HEALTHY,
            adapter="TerminalAdapter",
        )
    )

    loop = SelfHealingLoop(tool_registry=registry)
    wf_id = uuid4()
    t_id = uuid4()
    task = Task(
        task_id=t_id,
        workflow_id=wf_id,
        task_name="Safe Read Task",
        description="Read safe web content",
        category=TaskCategory.WEB_RESEARCH,
        priority=TaskPriority.LOW,
        status=TaskStatus.FAILED,
        required_tool="web_research",
        inputs={"query": "python"},
        risk_level=RiskLevel.LOW.value,
        expected_output="done",
    )
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=wf_id,
            goal="Test higher risk substitute rejection",
            status=WorkflowStatus.RUNNING,
        ),
        tasks={t_id: task},
    )

    fault = ToolExecutionException("Tool crashed: web_research")
    result = await loop.process_failure(task, fault, state)

    # Must be safely rejected, not substituted with high-risk terminal_tool
    assert result.success is False
    assert result.recovery_strategy in ("NO_VIABLE_RECOVERY", "ESCALATE_USER")
    assert len(result.replacement_tasks) == 0


@pytest.mark.asyncio
async def test_adapter_substitution_rejected_when_candidate_unhealthy():
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="browser_tool",
            status=ToolState.UNAVAILABLE,
            health=ToolHealth.FAILED,
            adapter="BrowserAdapter",
        )
    )
    # Substitute tool is registered but marked FAILED / DISABLED
    registry.register(
        Tool(
            name="web_research_tool",
            status=ToolState.DISABLED,
            health=ToolHealth.FAILED,
            adapter="WebResearchAdapter",
        )
    )

    loop = SelfHealingLoop(tool_registry=registry)
    wf_id = uuid4()
    t_id = uuid4()
    task = Task(
        task_id=t_id,
        workflow_id=wf_id,
        task_name="Search Web",
        description="Search web queries",
        category=TaskCategory.WEB_RESEARCH,
        priority=TaskPriority.HIGH,
        status=TaskStatus.FAILED,
        required_tool="browser_tool",
        inputs={"query": "test query"},
        risk_level=RiskLevel.LOW.value,
        expected_output="done",
    )
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=wf_id,
            goal="Test unhealthy candidate rejection",
            status=WorkflowStatus.RUNNING,
        ),
        tasks={t_id: task},
    )

    fault = ToolNotFoundException("Tool not found: browser_tool")
    result = await loop.process_failure(task, fault, state)

    assert result.success is False
    assert result.recovery_strategy == "ESCALATE_USER"
    assert len(result.replacement_tasks) == 0
