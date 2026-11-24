import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from shared.contracts.task import Task, TaskCategory, TaskPriority, TaskStatus
from shared.contracts.workflow import (
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

from app.agents.healing.self_healing_loop import SelfHealingLoop
from app.core.tracing import (
    flush_trace_buffer,
    get_trace_buffer,
    is_trace_enabled,
    record_trace,
)


def test_tracing_disabled_by_default(monkeypatch):
    monkeypatch.delenv("PHOENIX_TRACE", raising=False)
    assert not is_trace_enabled()

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_file = str(Path(tmpdir) / "trace.jsonl")
        res = record_trace("task_dispatch", trace_file=trace_file)
        assert res is None
        assert not Path(trace_file).exists()


def test_tracing_records_all_required_fields(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_file = str(Path(tmpdir) / "trace.jsonl")
        monkeypatch.setenv("PHOENIX_TRACE", "1")
        monkeypatch.setenv("PHOENIX_TRACE_FILE", trace_file)
        monkeypatch.setenv("PHOENIX_RUN_ID", "test-run-123")
        monkeypatch.setenv("PHOENIX_SEED", "99")
        monkeypatch.setenv("PHOENIX_CONFIG", "healing")

        wf_id = uuid4()
        t_id = uuid4()

        entry = record_trace(
            stage="stage1_error_parsing_start",
            workflow_id=wf_id,
            task_id=t_id,
            attempt=2,
            fault_class="TIMEOUT",
        )

        assert entry is not None
        assert entry["run_id"] == "test-run-123"
        assert entry["seed"] == 99
        assert entry["config"] == "healing"
        assert entry["workflow_id"] == str(wf_id)
        assert entry["task_id"] == str(t_id)
        assert entry["fault_class"] == "TIMEOUT"
        assert entry["attempt"] == 2
        assert entry["stage"] == "stage1_error_parsing_start"
        assert isinstance(entry["timestamp_ns"], int)
        assert entry["timestamp_ns"] > 0

        # Memory buffer holds entry before flush, file does not exist yet
        assert len(get_trace_buffer()) == 1
        assert not Path(trace_file).exists()

        # Flush buffer to file outside timed region
        flushed = flush_trace_buffer(trace_file)
        assert flushed == 1
        assert len(get_trace_buffer()) == 0

        # Check file content
        assert Path(trace_file).exists()
        lines = Path(trace_file).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["stage"] == "stage1_error_parsing_start"
        assert data["run_id"] == "test-run-123"


@pytest.mark.asyncio
async def test_self_healing_loop_tracing_integration(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_file = str(Path(tmpdir) / "trace.jsonl")
        monkeypatch.setenv("PHOENIX_TRACE", "1")
        monkeypatch.setenv("PHOENIX_TRACE_FILE", trace_file)

        wf_id = uuid4()
        t_id = uuid4()
        task = Task(
            task_id=t_id,
            workflow_id=wf_id,
            task_name="Test Task",
            description="Testing tracing",
            category=TaskCategory.WEB_SCRAPING,
            priority=TaskPriority.HIGH,
            status=TaskStatus.FAILED,
            required_tool="test_tool",
            expected_output="done",
        )
        metadata = WorkflowMetadata(
            workflow_id=wf_id,
            goal="Tracing goal",
            status=WorkflowStatus.RUNNING,
        )
        state = SharedWorkflowState(metadata=metadata, tasks={t_id: task})

        loop = SelfHealingLoop()
        await loop.process_failure(task, "TimeoutException: Request timed out", state)

        # Flush buffered events to disk
        flush_trace_buffer(trace_file)

        # Check trace lines written
        assert Path(trace_file).exists()
        lines = [
            json.loads(line)
            for line in Path(trace_file).read_text(encoding="utf-8").splitlines()
        ]
        stages = [line["stage"] for line in lines]

        assert "failure_detected" in stages
        assert "stage1_error_parsing_start" in stages
        assert "stage1_error_parsing_end" in stages
        assert "stage2_root_cause_analysis_start" in stages
        assert "stage2_root_cause_analysis_end" in stages
        assert "stage3_strategy_selection_start" in stages
        assert "stage3_strategy_selection_end" in stages
        assert "stage4_plan_validation_start" in stages
        assert "stage4_plan_validation_end" in stages

        # Also test compute_trace_latencies
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from experiments.compute_trace_latencies import compute_latencies

        stats = compute_latencies(trace_file)
        assert "T_R" in stats
