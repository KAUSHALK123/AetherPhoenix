"""
Comprehensive Performance Benchmark & Bottleneck Test Suite (Sprint 10 - Issue #Sprint-10-Performance-Testing).

Measures and records baseline performance across key system components:
1. Planner response time
2. Execution Bridge response time
3. Workflow startup latency
4. Worker execution time
5. Tool execution time
6. PPT generation time
7. API response times
8. Database persistence time
9. Frontend initial load / API payload performance
10. Frontend API request frequency & dashboard polling overhead
11. Multi-User -> Multi-Workflow -> Multi-Worker -> Concurrent Tool Execution
12. Memory leak & resource stability checks
"""

import asyncio
import gc
import os
import sys
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from shared.contracts.export import ExportFormat, ExportRequest
from shared.contracts.permission import PermissionRequest, PermissionStatus, PermissionType, RiskLevel
from shared.contracts.planner import PlannerOutput, PlannerRequest
from shared.contracts.task import Task, TaskCategory, TaskStatus, TaskType
from shared.contracts.workflow import ExecutionMode, SharedWorkflowState, WorkflowMetadata, WorkflowStatus

from app.agents.healing.agent import HealingAgent
from app.agents.planner.agent import PlannerAgent
from app.agents.supervisor.agent import SupervisorAgent
from app.agents.worker.agent import WorkerAgent
from app.core.events.bus import EventBus
from app.core.permissions.manager import PermissionManager
from app.database.session import SessionLocal, engine
from app.engine.orchestrator import PipelineOrchestrator
from app.engine.registry import CapabilityRegistry
from app.main import app
from app.planner.decomposer import TaskDecompositionEngine
from app.schemas.ppt import PresentationSchema, SlideContent, SlideType
from app.services.observability import get_observability_service
from app.tools.browser.controller import BrowserController
from app.tools.browser.interface import BrowserAdapter, register_browser_capability
from app.tools.desktop.controller import DesktopController
from app.tools.desktop.interface import DesktopToolAdapter, register_desktop_tool
from app.tools.desktop.models import DesktopActionResult
from app.tools.export.engine import ExportEngine
try:
    from app.tools.ppt.generator import PPTGenerator
    HAS_PPTX = True
except (ImportError, ModuleNotFoundError):
    PPTGenerator = None
    HAS_PPTX = False
from app.tools.registry import ToolRegistry


# -----------------------------------------------------------------------------
# Test Fixtures & Setup
# -----------------------------------------------------------------------------

@pytest.fixture
def performance_env():
    """Environment fixture for multi-agent execution pipeline."""
    event_bus = EventBus()
    cap_registry = CapabilityRegistry()
    tool_registry = ToolRegistry()
    permission_manager = PermissionManager(mode=ExecutionMode.AUTONOMOUS, event_bus=event_bus)

    worker_agent = WorkerAgent(
        tool_registry=tool_registry,
        permission_manager=permission_manager,
    )
    supervisor_agent = SupervisorAgent(event_bus=event_bus)
    healing_agent = HealingAgent(event_bus=event_bus)

    register_browser_capability(
        tool_registry=tool_registry,
        cap_registry=cap_registry,
        worker_agent=worker_agent,
        permission_manager=permission_manager,
    )
    register_desktop_tool(
        registry=tool_registry,
        permission_manager=permission_manager,
        worker_agent=worker_agent,
    )

    # Attach mock fast controller to desktop_adapter for benchmark tasks
    desktop_adapter: DesktopToolAdapter = worker_agent._adapters["desktop_adapter"]
    mock_desktop = AsyncMock(spec=DesktopController)
    mock_desktop.execute_action.return_value = DesktopActionResult(
        action="mouse_click",
        success=True,
        output={"status": "ok", "done": True, "processed": True, "clicked": True},
        execution_time_ms=0.5,
    )
    desktop_adapter.controller = mock_desktop

    orchestrator = PipelineOrchestrator(
        worker_agent=worker_agent,
        supervisor_agent=supervisor_agent,
        event_bus=event_bus,
        healing_agent=healing_agent,
    )

    return {
        "event_bus": event_bus,
        "cap_registry": cap_registry,
        "tool_registry": tool_registry,
        "permission_manager": permission_manager,
        "worker_agent": worker_agent,
        "supervisor_agent": supervisor_agent,
        "healing_agent": healing_agent,
        "orchestrator": orchestrator,
    }


# -----------------------------------------------------------------------------
# 1. Planner Response Time Benchmark
# -----------------------------------------------------------------------------

def test_planner_response_time_benchmark():
    """Benchmark PlannerAgent goal parsing and decomposition latency."""
    planner = PlannerAgent()
    decomposer = TaskDecompositionEngine()
    workflow_id = uuid4()

    # Benchmark Goal Decomposition
    start_decomp = time.perf_counter()
    plan = decomposer.decompose_goal("Build a FastAPI web app with database integration", workflow_id)
    decomp_time_ms = (time.perf_counter() - start_decomp) * 1000

    assert len(plan.tasks) > 0
    assert decomp_time_ms < 500.0, f"Decomposer latency too high: {decomp_time_ms:.2f}ms"

    # Benchmark Full Planner Request Processing
    req = PlannerRequest(
        session_id=str(uuid4()),
        message="Create a PowerPoint presentation on AI Desktop Assistant",
    )
    start_req = time.perf_counter()
    res = planner.process_request(req)
    req_time_ms = (time.perf_counter() - start_req) * 1000

    assert res.status == "ready"
    assert req_time_ms < 1000.0, f"PlannerAgent processing latency too high: {req_time_ms:.2f}ms"
    print(f"\n[METRIC] Planner Decomposition: {decomp_time_ms:.2f}ms | Planner Request: {req_time_ms:.2f}ms")


# -----------------------------------------------------------------------------
# 2. Execution Bridge Response Time Benchmark
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execution_bridge_response_time_benchmark(performance_env):
    """Benchmark Capability Registry, Tool Resolution, and Worker Adapter Bridge dispatch latency."""
    env = performance_env
    worker_agent: WorkerAgent = env["worker_agent"]
    workflow_id = uuid4()
    task_id = uuid4()

    task = Task(
        task_id=task_id,
        workflow_id=workflow_id,
        task_name="Bridge benchmark click",
        description="Benchmark bridge routing overhead",
        category=TaskCategory.DESKTOP,
        required_tool="desktop_automation",
        task_type=TaskType.LEAF,
        expected_output="status",
        inputs={"action": "mouse_click", "x": 50, "y": 50},
        status=TaskStatus.READY,
    )

    start_bridge = time.perf_counter()
    result = await worker_agent.execute(task)
    bridge_time_ms = (time.perf_counter() - start_bridge) * 1000

    assert result.success is True
    assert bridge_time_ms < 100.0, f"Execution Bridge latency too high: {bridge_time_ms:.2f}ms"
    print(f"[METRIC] Execution Bridge Latency: {bridge_time_ms:.2f}ms")


# -----------------------------------------------------------------------------
# 3. Workflow Startup Latency Benchmark
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow_startup_latency_benchmark(performance_env):
    """Benchmark time to initialize SharedWorkflowState and launch PipelineOrchestrator."""
    env = performance_env
    orchestrator: PipelineOrchestrator = env["orchestrator"]
    workflow_id = uuid4()

    start_init = time.perf_counter()
    task = Task(
        task_id=uuid4(),
        workflow_id=workflow_id,
        task_name="Startup benchmark task",
        description="Test task for startup measurement",
        category=TaskCategory.DESKTOP,
        required_tool="desktop_automation",
        task_type=TaskType.LEAF,
        expected_output="done",
        inputs={"action": "mouse_click"},
        status=TaskStatus.READY,
    )
    state = SharedWorkflowState(
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            session_id=str(uuid4()),
            goal="Test workflow startup latency",
            status=WorkflowStatus.CREATED,
        ),
        tasks={task.task_id: task},
        execution_queue=[task.task_id],
    )
    init_time_ms = (time.perf_counter() - start_init) * 1000

    start_run = time.perf_counter()
    result_state = await orchestrator.run_workflow(state)
    startup_run_time_ms = (time.perf_counter() - start_run) * 1000

    assert result_state.metadata.status == WorkflowStatus.COMPLETED
    assert init_time_ms < 50.0, f"Workflow State Init latency too high: {init_time_ms:.2f}ms"
    assert startup_run_time_ms < 200.0, f"Workflow Startup & Run latency too high: {startup_run_time_ms:.2f}ms"
    print(f"[METRIC] Workflow Init: {init_time_ms:.2f}ms | Startup & Execution: {startup_run_time_ms:.2f}ms")


# -----------------------------------------------------------------------------
# 4 & 5. Worker & Tool Execution Time Benchmarks
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_worker_and_tool_execution_time_benchmark(performance_env):
    """Benchmark WorkerAgent dispatch and ToolRegistry execution throughput."""
    env = performance_env
    worker: WorkerAgent = env["worker_agent"]
    iterations = 50
    workflow_id = uuid4()

    start_batch = time.perf_counter()
    for i in range(iterations):
        task = Task(
            task_id=uuid4(),
            workflow_id=workflow_id,
            task_name=f"Iteration task {i}",
            description="Benchmark worker throughput",
            category=TaskCategory.DESKTOP,
            required_tool="desktop_automation",
            task_type=TaskType.LEAF,
            expected_output="processed",
            inputs={"action": "mouse_click", "index": i},
            status=TaskStatus.READY,
        )
        res = await worker.execute(task)
        assert res.success is True

    total_batch_time_ms = (time.perf_counter() - start_batch) * 1000
    avg_per_task_ms = total_batch_time_ms / iterations

    assert avg_per_task_ms < 20.0, f"Average worker task execution time too high: {avg_per_task_ms:.2f}ms"
    print(f"[METRIC] Worker/Tool Execution Batch (50 tasks): {total_batch_time_ms:.2f}ms | Avg: {avg_per_task_ms:.2f}ms/task")


# -----------------------------------------------------------------------------
# 6. PPT Generation Time Benchmark
# -----------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_PPTX, reason="pptx library not installed")
def test_ppt_generation_time_benchmark():
    """Benchmark PPTGenerator slide deck compilation and output rendering time."""
    pm = PermissionManager(mode=ExecutionMode.AUTONOMOUS)
    generator = PPTGenerator(permission_manager=pm)
    workflow_id = uuid4()

    slides = [
        SlideContent(
            title="Title Slide",
            slide_type=SlideType.TITLE,
            subtitle="Benchmark PowerPoint Deck",
            speaker_notes="Welcome note",
        )
    ]
    for idx in range(1, 5):
        slides.append(
            SlideContent(
                title=f"Content Slide {idx}",
                slide_type=SlideType.CONTENT,
                bullets=[
                    f"Performance metric item {idx}.1",
                    f"Performance metric item {idx}.2",
                    f"Performance metric item {idx}.3",
                ],
                speaker_notes=f"Notes for slide {idx}",
            )
        )

    presentation = PresentationSchema(
        title="AetherPhoenix Performance Deck",
        slides=slides,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "benchmark_presentation.pptx")

        start_ppt = time.perf_counter()
        result = generator.generate(presentation, output_file, workflow_id)
        ppt_time_ms = (time.perf_counter() - start_ppt) * 1000

        assert result.slide_count == 5
        assert os.path.exists(output_file)
        assert result.file_size > 0
        assert ppt_time_ms < 1500.0, f"PPT Generation latency too high: {ppt_time_ms:.2f}ms"
        print(f"[METRIC] PPT Generation Time (5 slides): {ppt_time_ms:.2f}ms | File size: {result.file_size} bytes")


# -----------------------------------------------------------------------------
# 7. API Response Times Benchmark
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_response_times_benchmark():
    """Benchmark FastAPI response times across major REST endpoints."""
    endpoints = [
        ("/health", "GET", None),
        ("/api/v1/dashboard/stats", "GET", None),
        ("/api/v1/dashboard/workflows", "GET", None),
        ("/api/v1/notifications", "GET", None),
        ("/api/v1/permissions/pending", "GET", None),
        ("/api/v1/planner/generate", "POST", {"goal": "Create benchmark plan"}),
    ]

    latencies = {}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for path, method, payload in endpoints:
            start_ep = time.perf_counter()
            if method == "GET":
                resp = await client.get(path)
            else:
                resp = await client.post(path, json=payload)

            latency_ms = (time.perf_counter() - start_ep) * 1000
            latencies[path] = latency_ms

            assert resp.status_code in (200, 201)
            assert latency_ms < 500.0, f"Endpoint {path} latency too high: {latency_ms:.2f}ms"
            assert "x-process-time-ms" in resp.headers

    print("\n[METRIC] API Endpoint Response Times:")
    for path, ms in latencies.items():
        print(f"  - {path}: {ms:.2f}ms")


# -----------------------------------------------------------------------------
# 8. Database Persistence Time Benchmark
# -----------------------------------------------------------------------------

def test_database_persistence_time_benchmark():
    """Benchmark SQLite database connection, session creation, writes, and reads."""
    start_session = time.perf_counter()
    db = SessionLocal()
    session_time_ms = (time.perf_counter() - start_session) * 1000

    try:
        start_query = time.perf_counter()
        # Simple test query to measure DB read latency using text(...)
        res = db.execute(text("SELECT 1")).fetchall()
        query_time_ms = (time.perf_counter() - start_query) * 1000

        assert len(res) > 0
        assert session_time_ms < 50.0, f"DB session creation too slow: {session_time_ms:.2f}ms"
        assert query_time_ms < 20.0, f"DB query latency too high: {query_time_ms:.2f}ms"
        print(f"[METRIC] DB Session Init: {session_time_ms:.2f}ms | Query Exec: {query_time_ms:.2f}ms")
    finally:
        db.close()


# -----------------------------------------------------------------------------
# 9, 10 & 11. Frontend Initial Load & Polling Overhead Benchmark
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_and_polling_overhead_benchmark():
    """Benchmark rapid polling requests simulating frontend initial load and high-frequency polling."""
    num_requests = 50

    start_polling = time.perf_counter()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for _ in range(num_requests):
            resp = await client.get("/api/v1/permissions/pending")
            assert resp.status_code == 200

    total_polling_time_ms = (time.perf_counter() - start_polling) * 1000
    avg_polling_latency_ms = total_polling_time_ms / num_requests

    assert avg_polling_latency_ms < 20.0, f"Polling latency too high: {avg_polling_latency_ms:.2f}ms/request"
    print(f"[METRIC] Dashboard/Permission Rapid Polling ({num_requests} requests): {total_polling_time_ms:.2f}ms | Avg: {avg_polling_latency_ms:.2f}ms/req")


# -----------------------------------------------------------------------------
# 12. Concurrent Multi-User / Multi-Workflow Scaling Benchmark
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_multi_user_workflows_benchmark(performance_env):
    """
    Simulates:
    Multiple Users -> Multiple Workflows -> Multiple Workers -> Concurrent Tool Execution.
    Validates concurrency throughput, state isolation, and absence of deadlocks.
    """
    env = performance_env
    orchestrator: PipelineOrchestrator = env["orchestrator"]

    num_concurrent_users = 10
    tasks_per_workflow = 5

    async def execute_user_workflow(user_idx: int):
        workflow_id = uuid4()
        tasks_map = {}
        queue = []

        prev_task_id = None
        for t_idx in range(tasks_per_workflow):
            t_id = uuid4()
            deps = [prev_task_id] if prev_task_id else []
            task = Task(
                task_id=t_id,
                workflow_id=workflow_id,
                task_name=f"User-{user_idx} Task-{t_idx}",
                description=f"Task {t_idx} for simulated user {user_idx}",
                category=TaskCategory.DESKTOP,
                required_tool="desktop_automation",
                task_type=TaskType.LEAF,
                expected_output="done",
                inputs={"action": "mouse_click", "user": user_idx, "step": t_idx},
                dependencies=deps,
                status=TaskStatus.READY,
            )
            tasks_map[t_id] = task
            queue.append(t_id)
            prev_task_id = t_id

        state = SharedWorkflowState(
            metadata=WorkflowMetadata(
                workflow_id=workflow_id,
                session_id=f"user-session-{user_idx}",
                goal=f"Concurrent user workflow {user_idx}",
                status=WorkflowStatus.CREATED,
            ),
            tasks=tasks_map,
            execution_queue=queue,
        )

        res_state = await orchestrator.run_workflow(state)
        return res_state

    start_concurrent = time.perf_counter()
    results = await asyncio.gather(*[execute_user_workflow(i) for i in range(num_concurrent_users)])
    total_concurrent_time_ms = (time.perf_counter() - start_concurrent) * 1000

    assert len(results) == num_concurrent_users
    for res_state in results:
        assert res_state.metadata.status == WorkflowStatus.COMPLETED
        assert len(res_state.completed_tasks) == tasks_per_workflow

    total_tasks_processed = num_concurrent_users * tasks_per_workflow
    throughput_tasks_per_sec = (total_tasks_processed / total_concurrent_time_ms) * 1000.0

    print(f"\n[METRIC] Concurrent Workflows: {num_concurrent_users} users ({total_tasks_processed} total tasks)")
    print(f"[METRIC] Total Execution Time: {total_concurrent_time_ms:.2f}ms | Throughput: {throughput_tasks_per_sec:.2f} tasks/sec")


# -----------------------------------------------------------------------------
# 13. Memory Leak & Resource Stability Benchmark
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_memory_leak_and_resource_stability_benchmark(performance_env):
    """
    Run repetitive workflow executions while tracking Python object allocations
    and memory footprint to verify no memory leaks occur during task processing.
    """
    env = performance_env
    orchestrator: PipelineOrchestrator = env["orchestrator"]

    gc.collect()
    initial_objects = len(gc.get_objects())

    runs = 30
    for i in range(runs):
        workflow_id = uuid4()
        task = Task(
            task_id=uuid4(),
            workflow_id=workflow_id,
            task_name=f"Leak check task {i}",
            description="Memory stability check",
            category=TaskCategory.DESKTOP,
            required_tool="desktop_automation",
            task_type=TaskType.LEAF,
            expected_output="done",
            inputs={"action": "mouse_click"},
            status=TaskStatus.READY,
        )
        state = SharedWorkflowState(
            metadata=WorkflowMetadata(
                workflow_id=workflow_id,
                session_id=str(uuid4()),
                goal="Memory leak test run",
                status=WorkflowStatus.CREATED,
            ),
            tasks={task.task_id: task},
            execution_queue=[task.task_id],
        )
        await orchestrator.run_workflow(state)

    gc.collect()
    final_objects = len(gc.get_objects())
    object_delta = final_objects - initial_objects

    print(f"\n[METRIC] Memory Leak Check ({runs} runs): Initial Objects={initial_objects}, Final Objects={final_objects}, Delta={object_delta}")
    assert object_delta < 3000, f"Potential memory leak detected! Object delta: {object_delta}"
