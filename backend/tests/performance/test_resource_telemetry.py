import json
from uuid import uuid4

from shared.contracts.execution import ExecutionMetrics
from shared.contracts.planner import PlanMetadata, PlannerRequest

from app.agents.planner.agent import PlannerAgent
from app.planner.llm_planner import LLMPlanner


def test_execution_metrics_telemetry_fields():
    metrics = ExecutionMetrics(
        execution_time_ms=125.5,
        memory_usage_mb=42.1,
        cpu_usage_percent=15.0,
        exit_code=0,
        prompt_tokens=450,
        completion_tokens=120,
        total_cost_usd=0.0012,
        memory_rss_mb=55.4,
        planning_strategy_used="decomposition_pipeline",
    )
    assert metrics.prompt_tokens == 450
    assert metrics.completion_tokens == 120
    assert metrics.total_cost_usd == 0.0012
    assert metrics.memory_rss_mb == 55.4
    assert metrics.planning_strategy_used == "decomposition_pipeline"

    dumped = metrics.model_dump()
    assert dumped["prompt_tokens"] == 450
    assert dumped["planning_strategy_used"] == "decomposition_pipeline"


def test_plan_metadata_telemetry_fields():
    meta = PlanMetadata(
        session_id="sess-100",
        workflow_id="wf-100",
        goal="Test telemetry",
        prompt_tokens=200,
        completion_tokens=80,
        total_cost_usd=0.0005,
        memory_rss_mb=48.2,
        planning_strategy_used="catalog_fallback",
    )
    assert meta.prompt_tokens == 200
    assert meta.completion_tokens == 80
    assert meta.memory_rss_mb == 48.2
    assert meta.planning_strategy_used == "catalog_fallback"


def test_llm_planner_resource_telemetry():
    planner = LLMPlanner()
    req = PlannerRequest(
        session_id="test-session-telemetry",
        message="list files in downloads",
    )
    wf_id = uuid4()
    resp = planner.plan(req, wf_id)
    assert resp.status == "ready"
    assert resp.reply is not None

    plan_json = json.loads(resp.reply)
    metadata = plan_json.get("metadata", {})
    assert "memory_rss_mb" in metadata
    assert metadata["memory_rss_mb"] is not None
    assert metadata["memory_rss_mb"] > 0
    assert metadata["planning_strategy_used"] == "catalog_fallback"
    assert metadata["prompt_tokens"] > 0
    assert metadata["completion_tokens"] > 0


def test_planner_agent_resource_telemetry():
    agent = PlannerAgent()
    req = PlannerRequest(
        session_id="sess-planner-agent-telemetry",
        message="Open folder and inspect logs",
    )
    resp = agent.process_request(req)
    assert resp.status == "ready"

    plan_json = json.loads(resp.reply)
    metadata = plan_json.get("metadata", {})
    assert "memory_rss_mb" in metadata
    assert metadata["memory_rss_mb"] is not None
    assert metadata["memory_rss_mb"] > 0
    assert metadata["planning_strategy_used"] == "decomposition_pipeline"
    assert metadata["prompt_tokens"] > 0
    assert metadata["completion_tokens"] > 0
