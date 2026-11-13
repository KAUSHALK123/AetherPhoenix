"""
Agent Factory — Singleton factory for PipelineOrchestrator and core agents.

Provides initialized singleton instances for:
- ToolRegistry (populated with all core tool adapters)
- WorkerAgent
- SupervisorAgent
- HealingAgent
- PipelineOrchestrator
"""
import logging
from typing import Optional

from app.core.events.bus import get_event_bus
from app.core.permissions.manager import get_permission_manager
from app.memory.task_history import get_task_history_service
from app.planner.llm_planner import get_default_tool_registry
from app.services.artifact_storage import get_artifact_storage_service

logger = logging.getLogger(__name__)

_orchestrator_instance = None
_worker_instance = None
_supervisor_instance = None
_healing_instance = None
_tool_registry_instance = None


def get_shared_tool_registry():
    """Returns the shared ToolRegistry with all core system tools."""
    global _tool_registry_instance
    if _tool_registry_instance is None:
        _tool_registry_instance = get_default_tool_registry()
    return _tool_registry_instance


def get_worker_agent():
    """Returns the WorkerAgent singleton."""
    global _worker_instance
    if _worker_instance is None:
        from app.agents.worker.agent import WorkerAgent

        tool_registry = get_shared_tool_registry()
        permission_manager = get_permission_manager()
        task_history = get_task_history_service()
        artifact_storage = get_artifact_storage_service()

        _worker_instance = WorkerAgent(
            tool_registry=tool_registry,
            permission_manager=permission_manager,
            task_history_service=task_history,
            artifact_storage_service=artifact_storage,
        )
    return _worker_instance


def get_supervisor_agent():
    """Returns the SupervisorAgent singleton."""
    global _supervisor_instance
    if _supervisor_instance is None:
        from app.agents.supervisor.agent import SupervisorAgent

        event_bus = get_event_bus()
        task_history = get_task_history_service()

        _supervisor_instance = SupervisorAgent(
            event_bus=event_bus,
            task_history_service=task_history,
        )
    return _supervisor_instance


def get_healing_agent():
    """Returns the HealingAgent singleton."""
    global _healing_instance
    if _healing_instance is None:
        from app.agents.healing.agent import HealingAgent

        event_bus = get_event_bus()
        _healing_instance = HealingAgent(event_bus=event_bus)
    return _healing_instance


def get_pipeline_orchestrator():
    """
    Returns the global singleton PipelineOrchestrator instance.
    All dependencies (WorkerAgent, SupervisorAgent, HealingAgent, ToolRegistry)
    are lazily instantiated and cached.
    """
    global _orchestrator_instance
    if _orchestrator_instance is not None:
        return _orchestrator_instance

    logger.info("Initializing PipelineOrchestrator and agent stack (first call)...")

    event_bus = get_event_bus()
    worker = get_worker_agent()
    supervisor = get_supervisor_agent()
    healing = get_healing_agent()

    from app.engine.orchestrator import PipelineOrchestrator

    _orchestrator_instance = PipelineOrchestrator(
        worker_agent=worker,
        supervisor_agent=supervisor,
        event_bus=event_bus,
        healing_agent=healing,
    )

    logger.info("PipelineOrchestrator singleton initialized successfully.")
    return _orchestrator_instance


def reset_orchestrator():
    """Resets all agent singletons (useful for clean test runs)."""
    global _orchestrator_instance, _worker_instance, _supervisor_instance, _healing_instance, _tool_registry_instance
    _orchestrator_instance = None
    _worker_instance = None
    _supervisor_instance = None
    _healing_instance = None
    _tool_registry_instance = None
