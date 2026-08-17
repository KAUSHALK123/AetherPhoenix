from uuid import uuid4

import pytest
from shared.contracts.execution_log import ExecutionPhase, ExecutionStatus
from shared.contracts.task import Task, TaskCategory
from shared.contracts.tool import Tool, ToolHealth, ToolState

from app.agents.worker.executor import WorkerTaskExecutor
from app.core.exceptions import PermissionDeniedException, ToolExecutionException
from app.core.logging.execution_logger import WorkerExecutionLogger
from app.core.logging.sanitizer import sanitize_log_data
from app.tools.registry import ToolRegistry


class TestExecutionLogger:
    """Test suite for structured Worker execution logging system."""

    def test_worker_execution_logger_lifecycle(self):
        workflow_id = uuid4()
        task_id = uuid4()
        corr_id = "corr_trace_12345"

        exec_logger = WorkerExecutionLogger(
            workflow_id=workflow_id,
            task_id=task_id,
            task_name="Process Data",
            tool_name="data_tool",
            correlation_id=corr_id,
        )

        assert exec_logger.correlation_id == corr_id
        assert exec_logger.context_data["correlation_id"] == corr_id

        # 1. Task Start
        start_event = exec_logger.log_task_start(inputs={"input_param": "value1"})
        assert start_event.phase == ExecutionPhase.TASK_START
        assert start_event.status == ExecutionStatus.STARTED
        assert start_event.correlation_id == corr_id
        assert start_event.inputs == {"input_param": "value1"}

        # 2. Tool Selected
        select_event = exec_logger.log_tool_selected(tool_name="custom_tool")
        assert select_event.phase == ExecutionPhase.TOOL_SELECTION
        assert select_event.status == ExecutionStatus.IN_PROGRESS
        assert exec_logger.tool_name == "custom_tool"

        # 3. Tool Execution Start & Complete
        tool_start_event = exec_logger.log_tool_start(inputs={"query": "select *"})
        assert tool_start_event.status == ExecutionStatus.TOOL_STARTED

        tool_comp_event = exec_logger.log_tool_complete(
            duration_ms=45.6, outputs={"rows": 10}
        )
        assert tool_comp_event.status == ExecutionStatus.TOOL_COMPLETED
        assert tool_comp_event.duration_ms == 45.6
        assert tool_comp_event.outputs == {"rows": 10}

        # 4. Task Complete
        task_comp_event = exec_logger.log_task_complete(
            duration_ms=120.5, artifacts_count=2
        )
        assert task_comp_event.phase == ExecutionPhase.TASK_COMPLETE
        assert task_comp_event.status == ExecutionStatus.COMPLETED
        assert task_comp_event.duration_ms == 120.5
        assert task_comp_event.metadata["artifacts_count"] == 2

    def test_worker_execution_logger_failures(self):
        workflow_id = uuid4()
        task_id = uuid4()

        exec_logger = WorkerExecutionLogger(
            workflow_id=workflow_id,
            task_id=task_id,
            task_name="Failing Task",
            tool_name="faulty_tool",
        )

        # Tool failure
        tf_event = exec_logger.log_tool_failure(
            duration_ms=30.0,
            error_code="TIMEOUT_ERROR",
            error_message="Tool connection timed out after 30ms",
        )
        assert tf_event.status == ExecutionStatus.TOOL_FAILED
        assert tf_event.error_code == "TIMEOUT_ERROR"
        assert tf_event.error_message == "Tool connection timed out after 30ms"

        # Task failure
        task_fail_event = exec_logger.log_task_failure(
            duration_ms=50.0,
            error_code="TASK_FAILED",
            error_message="Execution chain broken",
        )
        assert task_fail_event.phase == ExecutionPhase.TASK_FAILED
        assert task_fail_event.status == ExecutionStatus.FAILED
        assert task_fail_event.error_code == "TASK_FAILED"

    def test_sensitive_data_sanitizer(self):
        raw_data = {
            "user": "admin",
            "password": "SuperSecretPassword123!",
            "api_key": "sk-proj-1234567890abcdef",
            "access_token": "bearer_jwt_token_payload",
            "nested": {
                "secret": "hidden_value",
                "normal_field": "public_data",
            },
            "long_content": "A" * 600,
        }

        sanitized = sanitize_log_data(raw_data, max_string_len=500)

        assert sanitized["user"] == "admin"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["access_token"] == "***REDACTED***"
        assert sanitized["nested"]["secret"] == "***REDACTED***"
        assert sanitized["nested"]["normal_field"] == "public_data"
        assert "<Truncated 100 chars>" in sanitized["long_content"]

    def test_track_execution_context_manager(self):
        workflow_id = uuid4()
        task_id = uuid4()

        exec_logger = WorkerExecutionLogger(
            workflow_id=workflow_id,
            task_id=task_id,
            task_name="Context Managed Task",
            tool_name="test_tool",
        )

        with exec_logger.track_execution(inputs={"param": 1}):
            # Simulate work inside block
            pass

        # Test exception tracking in track_execution
        with pytest.raises(ToolExecutionException):
            with exec_logger.track_execution():
                raise ToolExecutionException(
                    message="Simulated failure inside context manager",
                    code="SIMULATED_FAIL",
                )

    def test_correlation_id_propagation(self):
        shared_correlation_id = "wf_trace_98765"
        workflow_id = uuid4()

        # Task 1
        logger1 = WorkerExecutionLogger(
            workflow_id=workflow_id,
            task_id=uuid4(),
            task_name="Task 1",
            tool_name="tool_1",
            correlation_id=shared_correlation_id,
        )
        e1 = logger1.log_task_start()

        # Task 2 inheriting correlation ID
        logger2 = WorkerExecutionLogger(
            workflow_id=workflow_id,
            task_id=uuid4(),
            task_name="Task 2",
            tool_name="tool_2",
            correlation_id=shared_correlation_id,
        )
        e2 = logger2.log_task_start()

        assert e1.correlation_id == shared_correlation_id
        assert e2.correlation_id == shared_correlation_id
        assert e1.correlation_id == e2.correlation_id

    def test_worker_task_executor_successful_execution(self):
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="test_tool",
                status=ToolState.READY,
                health=ToolHealth.HEALTHY,
                adapter="test_adapter",
            )
        )
        executor = WorkerTaskExecutor(tool_registry=registry)

        workflow_id = uuid4()
        task = Task(
            workflow_id=workflow_id,
            task_name="Run Test Tool",
            description="Executes test_tool with payload",
            required_tool="test_tool",
            category=TaskCategory.PYTHON,
            expected_output="Result data",
        )

        def mock_tool_func(inputs):
            return {"result": f"processed {inputs.get('val')}"}

        result = executor.execute_task(
            task=task,
            payload={"val": 42},
            tool_fn=mock_tool_func,
            correlation_id="trace_001",
        )

        assert result.success is True
        assert result.output == {"result": "processed 42"}
        assert result.metrics.execution_time_ms > 0
        assert any("started" in log for log in result.logs)
        assert any("completed" in log for log in result.logs)

    def test_worker_task_executor_missing_tool_log(self):
        empty_registry = ToolRegistry()
        executor = WorkerTaskExecutor(tool_registry=empty_registry)

        workflow_id = uuid4()
        task = Task(
            workflow_id=workflow_id,
            task_name="Missing Tool Task",
            description="Task requiring missing tool",
            required_tool="non_existent_tool",
            category=TaskCategory.OTHER,
            expected_output="Output",
        )

        result = executor.execute_task(task=task)

        assert result.success is False
        assert result.error is not None
        assert result.error.error_code == "TOOL_NOT_FOUND"

    def test_worker_task_executor_disabled_tool_log(self):
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="disabled_tool",
                status=ToolState.DISABLED,
                health=ToolHealth.WARNING,
                adapter="disabled_adapter",
            )
        )
        executor = WorkerTaskExecutor(tool_registry=registry)

        workflow_id = uuid4()
        task = Task(
            workflow_id=workflow_id,
            task_name="Disabled Tool Task",
            description="Task with disabled tool",
            required_tool="disabled_tool",
            category=TaskCategory.OTHER,
            expected_output="Output",
        )

        result = executor.execute_task(task=task)

        assert result.success is False
        assert result.error is not None
        assert result.error.error_code == "TOOL_DISABLED"

    def test_worker_task_executor_permission_denial_log(self):
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="restricted_tool",
                status=ToolState.READY,
                health=ToolHealth.HEALTHY,
                adapter="restricted_adapter",
            )
        )

        class MockPermissionManager:
            def enforce_permission(self, permission_type, workflow_id):
                raise PermissionDeniedException(
                    message="Permission FILE_SYSTEM denied for workflow."
                )

        permission_manager = MockPermissionManager()
        executor = WorkerTaskExecutor(
            tool_registry=registry, permission_manager=permission_manager
        )

        workflow_id = uuid4()
        task = Task(
            workflow_id=workflow_id,
            task_name="Restricted Task",
            description="Task with denied permission",
            required_tool="restricted_tool",
            category=TaskCategory.FILE_SYSTEM,
            expected_output="Output",
        )

        result = executor.execute_task(task=task)

        assert result.success is False
        assert result.error is not None
        assert result.error.error_code == "PERMISSION_DENIED"

    def test_worker_task_executor_tool_failure_log(self):
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="faulty_tool",
                status=ToolState.READY,
                health=ToolHealth.HEALTHY,
                adapter="faulty_adapter",
            )
        )
        executor = WorkerTaskExecutor(tool_registry=registry)

        workflow_id = uuid4()
        task = Task(
            workflow_id=workflow_id,
            task_name="Faulty Execution Task",
            description="Task whose tool function raises exception",
            required_tool="faulty_tool",
            category=TaskCategory.PYTHON,
            expected_output="Result",
        )

        def failing_tool_func(inputs):
            raise ToolExecutionException(
                message="Tool internal computation failure",
                code="TOOL_INTERNAL_ERROR",
            )

        result = executor.execute_task(
            task=task,
            payload={"key": "val"},
            tool_fn=failing_tool_func,
            correlation_id="trace_faulty_001",
        )

        assert result.success is False
        assert result.error is not None
        assert result.error.error_code == "TOOL_INTERNAL_ERROR"
        assert "failed" in result.logs[-1]

    def test_worker_task_executor_multiple_tasks_correlation_tracking(self):
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="step_tool",
                status=ToolState.READY,
                health=ToolHealth.HEALTHY,
                adapter="step_adapter",
            )
        )
        executor = WorkerTaskExecutor(tool_registry=registry)

        shared_correlation_id = "multi_task_workflow_trace_777"
        workflow_id = uuid4()

        task1 = Task(
            workflow_id=workflow_id,
            task_name="Step 1 Task",
            description="First step",
            required_tool="step_tool",
            category=TaskCategory.PYTHON,
            expected_output="Step 1 Output",
        )

        task2 = Task(
            workflow_id=workflow_id,
            task_name="Step 2 Task",
            description="Second step",
            required_tool="step_tool",
            category=TaskCategory.PYTHON,
            expected_output="Step 2 Output",
        )

        r1 = executor.execute_task(
            task=task1,
            correlation_id=shared_correlation_id,
        )
        r2 = executor.execute_task(
            task=task2,
            correlation_id=shared_correlation_id,
        )

        assert r1.success is True
        assert r2.success is True
        assert r1.workflow_id == workflow_id
        assert r2.workflow_id == workflow_id
