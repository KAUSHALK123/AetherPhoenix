from uuid import uuid4

import pytest
from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import HealingResult, TaskError
from shared.contracts.memory import MemoryCategory, MemoryType
from shared.contracts.planner import PlannerRequest
from shared.contracts.task import Task, TaskCategory, TaskStatus

from app.memory.integration_hub import (
    MemoryIntegrationHub,
    get_memory_integration_hub,
    reset_memory_integration_hub,
)
from app.memory.manager import MemoryManager
from app.memory.rag_pipeline import RAGPipelineService
from app.memory.task_history import TaskHistoryService
from app.memory.vector_db import (
    DeterministicHashEmbeddingProvider,
    InMemoryVectorStoreProvider,
    VectorDatabaseService,
)


@pytest.fixture
def memory_hub():
    provider = InMemoryVectorStoreProvider()
    embedding = DeterministicHashEmbeddingProvider(dimension=64)
    vector_db = VectorDatabaseService(
        embedding_provider=embedding, vector_store_provider=provider
    )
    task_history = TaskHistoryService()
    rag_pipeline = RAGPipelineService(vector_db=vector_db, task_history=task_history)
    memory_manager = MemoryManager(
        vector_db=vector_db,
        embedding_provider=embedding,
    )

    return MemoryIntegrationHub(
        memory_manager=memory_manager,
        rag_pipeline=rag_pipeline,
        task_history=task_history,
    )


@pytest.mark.asyncio
async def test_full_agent_memory_lifecycle(memory_hub):
    # Step 1: Initial User Prompt to Planner
    req1 = PlannerRequest(
        session_id="session_dev_1",
        message="Create automated deployment pipeline with Docker and Kubernetes",
    )
    enriched_req1 = await memory_hub.prepare_planner_request(req1)
    assert enriched_req1 is not None
    assert "retrieved_knowledge" in enriched_req1.context

    # Step 2: Worker executes task and stores task result
    task_id = uuid4()
    wf_id = uuid4()
    worker_task = Task(
        task_id=task_id,
        workflow_id=wf_id,
        task_name="Deploy Kubernetes Cluster",
        description="Deploy and provision Kubernetes production cluster",
        category=TaskCategory.OTHER,
        required_tool="KubernetesTool",
        expected_output="Cluster endpoint URL",
        assigned_agent="WorkerAgent",
        inputs={"cluster_name": "prod-k8s"},
    )
    memory_hub.task_history.record_task_created(worker_task)

    # Worker completes and results are stored in memory
    saved_result_memory = await memory_hub.record_worker_result(
        task=worker_task,
        output_data={
            "cluster_status": "READY",
            "endpoint": "https://k8s.internal",
        },
        status=TaskStatus.COMPLETED,
        execution_summary="Successfully provisioned Kubernetes cluster.",
    )
    assert saved_result_memory is not None
    assert saved_result_memory.memory_type == MemoryType.TASK_RESULT
    assert "Kubernetes cluster" in saved_result_memory.content

    # Step 3: Supervisor captures milestone event
    sup_event = RuntimeEvent(
        event_type=EventType.WORKFLOW_COMPLETED,
        source_component=EventSource.SUPERVISOR,
        workflow_id=wf_id,
        payload={"summary": "Deployment pipeline successfully completed."},
    )
    sup_memory = await memory_hub.record_supervisor_event(sup_event)
    assert sup_memory is not None
    assert sup_memory.category == MemoryCategory.DECISION

    # Step 4: Similar User Request Submitted -> Planner retrieves previous knowledge
    req2 = PlannerRequest(
        session_id="session_dev_2",
        message="Query Kubernetes cluster endpoint and deployment status",
    )
    enriched_req2 = await memory_hub.prepare_planner_request(req2)
    assert enriched_req2 is not None
    rag_context = enriched_req2.context.get("rag_context", {})
    assert rag_context.get("total_retrieved", 0) >= 1
    retrieved_text = enriched_req2.context.get("retrieved_knowledge", "")
    assert "Kubernetes" in retrieved_text


@pytest.mark.asyncio
async def test_healing_integration(memory_hub):
    task_id = uuid4()
    wf_id = uuid4()
    task_error = TaskError(
        error_code="TIMEOUT_ERROR",
        error_message="Connection timed out while reaching database host.",
    )
    healing_result = HealingResult(
        task_id=task_id,
        workflow_id=wf_id,
        root_cause="Database unreachable",
        recovery_strategy="EXPONENTIAL_BACKOFF_RETRY",
        success=True,
    )

    healing_mem = await memory_hub.record_healing_result(
        task_id=task_id,
        workflow_id=wf_id,
        task_error=task_error,
        healing_result=healing_result,
    )

    assert healing_mem is not None
    assert healing_mem.memory_type == MemoryType.KNOWLEDGE
    assert "Healing Resolution" in healing_mem.content
    assert healing_mem.metadata["healing_success"] == "True"


@pytest.mark.asyncio
async def test_worker_task_enrichment(memory_hub):
    # Store relevant context first
    await memory_hub.memory_manager.create_memory(
        content="Always verify SSL certificates before connecting to API",
        category=MemoryCategory.INSTRUCTION,
        memory_type=MemoryType.KNOWLEDGE,
    )

    task = Task(
        task_id=uuid4(),
        workflow_id=uuid4(),
        task_name="Connect to External API Gateway",
        description="Establish secure connection with upstream API",
        category=TaskCategory.SEARCH,
        required_tool="HttpTool",
        expected_output="Valid JSON response",
        assigned_agent="WorkerAgent",
    )

    enriched_task = await memory_hub.prepare_worker_task(task)
    assert enriched_task is not None
    assert "retrieved_knowledge" in enriched_task.inputs


@pytest.mark.asyncio
async def test_graceful_failures(memory_hub):
    # Empty query graceful handling
    empty_req = PlannerRequest(
        session_id="empty_sess",
        message="",
    )
    res = await memory_hub.prepare_planner_request(empty_req)
    assert res is not None

    # Supervisor non-milestone event ignored gracefully
    ping_event = RuntimeEvent(
        event_type=EventType.TASK_STARTED,
        source_component=EventSource.WORKER,
        workflow_id=uuid4(),
        payload={"ping": "pong"},
    )
    ignored_mem = await memory_hub.record_supervisor_event(ping_event)
    assert ignored_mem is None


@pytest.mark.asyncio
async def test_singleton_hub():
    reset_memory_integration_hub()
    hub1 = get_memory_integration_hub()
    hub2 = get_memory_integration_hub()
    assert hub1 is hub2
    reset_memory_integration_hub()
