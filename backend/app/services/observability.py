import logging
from collections import deque
from typing import Dict, List, Optional

from shared.contracts.workflow import SharedWorkflowState

from app.core.events.bus import EventBus, get_event_bus
from app.core.events.models import Event, EventType
from app.runtime.kernel import get_kernel

logger = logging.getLogger(__name__)


class EventObservabilityService:
    """
    Service for collecting, aggregating, and exposing events and execution states
    for the Event Dashboard and observability endpoints.
    """

    def __init__(self, event_bus: EventBus, max_events: int = 500) -> None:
        self.event_bus = event_bus
        self.recent_events: deque[Event] = deque(maxlen=max_events)
        # Store historical/completed workflows (workflow_id -> state dict)
        self.historical_workflows: Dict[str, dict] = {}
        # Subscribe to all events on the Event Bus
        self.event_bus.subscribe_all(self.on_event)

    async def on_event(self, event: Event) -> None:
        """Callback triggered on every published event."""
        self.recent_events.append(event)
        logger.debug(f"Observability service captured event: {event.event_type}")

        # If a workflow completes or fails, capture its final state from the kernel
        event_type_str = (
            event.event_type.value
            if isinstance(event.event_type, EventType)
            else str(event.event_type)
        )

        if event.workflow_id and event_type_str in (
            "WorkflowCompleted",
            "WorkflowFailed",
            "WorkflowCancelled",
            (
                EventType.WORKFLOW_COMPLETED.value
                if hasattr(EventType, "WORKFLOW_COMPLETED")
                else "WORKFLOW_COMPLETED"
            ),
            (
                EventType.WORKFLOW_FAILED.value
                if hasattr(EventType, "WORKFLOW_FAILED")
                else "WORKFLOW_FAILED"
            ),
            (
                EventType.WORKFLOW_CANCELLED.value
                if hasattr(EventType, "WORKFLOW_CANCELLED")
                else "WORKFLOW_CANCELLED"
            ),
        ):
            kernel = get_kernel()
            event_wf_id = str(event.workflow_id)
            for ctx in kernel.active_contexts.values():
                if str(ctx.shared_state.metadata.workflow_id) == event_wf_id:
                    serialized = self._serialize_state(ctx.shared_state)
                    self.historical_workflows[event_wf_id] = serialized
                    break

    def _serialize_state(self, state: SharedWorkflowState) -> dict:
        """Serializes the SharedWorkflowState into a dictionary for JSON response."""
        tasks_dict = {}
        for task_id, t in state.tasks.items():
            tasks_dict[str(task_id)] = {
                "task_id": str(t.task_id),
                "task_name": t.task_name,
                "description": t.description,
                "status": (
                    t.status.value if hasattr(t.status, "value") else str(t.status)
                ),
                "retry_count": getattr(t, "retry_count", 0),
                "dependencies": [str(d) for d in t.dependencies],
                "permissions": list(t.permissions) if t.permissions else [],
                "risk_level": getattr(t, "risk_level", "LOW"),
                "category": (
                    t.category.value
                    if hasattr(t.category, "value")
                    else str(t.category)
                ),
            }

        validations_dict = {}
        for task_id, val in state.validations.items():
            validations_dict[str(task_id)] = {
                "task_id": str(val.task_id),
                "workflow_id": str(val.workflow_id),
                "is_valid": val.is_valid,
                "decision": (
                    val.decision.value
                    if hasattr(val.decision, "value")
                    else str(val.decision)
                ),
                "checks": val.checks,
                "issues": val.issues,
            }

        return {
            "workflow_id": str(state.metadata.workflow_id),
            "goal": state.metadata.goal,
            "status": (
                state.metadata.status.value
                if hasattr(state.metadata.status, "value")
                else str(state.metadata.status)
            ),
            "progress_percentage": state.progress.overall_percentage,
            "tasks": tasks_dict,
            "validations": validations_dict,
            "running_tasks": [str(t_id) for t_id in state.running_tasks],
            "completed_tasks": [str(t_id) for t_id in state.completed_tasks],
            "failed_tasks": [str(t_id) for t_id in state.failed_tasks],
            "blocked_tasks": [
                str(t_id) for t_id in getattr(state, "blocked_tasks", [])
            ],
            "pending_tasks": [
                str(t_id) for t_id in getattr(state, "pending_tasks", [])
            ],
            "execution_duration": state.progress.execution_duration_seconds,
        }

    def get_workflows(self) -> List[dict]:
        """Returns list of active and historical workflows."""
        workflows = []

        # Get active workflows from RuntimeKernel
        kernel = get_kernel()
        active_ids = set()
        for ctx in kernel.active_contexts.values():
            serialized = self._serialize_state(ctx.shared_state)
            workflows.append(serialized)
            active_ids.add(serialized["workflow_id"])

        # Add historical workflows not currently active
        for w_id, w_state in self.historical_workflows.items():
            if w_id not in active_ids:
                workflows.append(w_state)

        return workflows

    def get_workflow_by_id(self, workflow_id: str) -> Optional[dict]:
        """Returns details for a single workflow by ID."""
        kernel = get_kernel()
        for ctx in kernel.active_contexts.values():
            if str(ctx.shared_state.metadata.workflow_id) == workflow_id:
                return self._serialize_state(ctx.shared_state)

        return self.historical_workflows.get(workflow_id)

    def get_recent_events(self, workflow_id: Optional[str] = None) -> List[dict]:
        """Returns rolling log of recent events."""
        events_list = []
        for e in self.recent_events:
            if workflow_id and str(e.workflow_id) != workflow_id:
                continue

            event_type_str = (
                e.event_type.value
                if isinstance(e.event_type, EventType)
                else str(e.event_type)
            )

            events_list.append(
                {
                    "id": str(e.id),
                    "workflow_id": str(e.workflow_id) if e.workflow_id else None,
                    "task_id": str(e.task_id) if e.task_id else None,
                    "event_type": event_type_str,
                    "source_component": str(e.source_component),
                    "target_component": (
                        str(e.target_component) if e.target_component else None
                    ),
                    "timestamp": e.timestamp.isoformat(),
                    "payload": e.payload,
                }
            )
        # Sort in reverse chronological order
        return sorted(events_list, key=lambda x: x["timestamp"], reverse=True)

    def get_stats(self) -> dict:
        """Returns aggregated dashboard stats."""
        workflows = self.get_workflows()
        total = len(workflows)
        running = sum(
            1
            for w in workflows
            if w["status"] == "RUNNING" or w["status"] == "WorkflowStatus.RUNNING"
        )
        completed = sum(
            1
            for w in workflows
            if w["status"] == "COMPLETED" or w["status"] == "WorkflowStatus.COMPLETED"
        )
        failed = sum(
            1
            for w in workflows
            if w["status"] == "FAILED" or w["status"] == "WorkflowStatus.FAILED"
        )

        total_retries = 0
        total_duration = 0.0
        for w in workflows:
            total_duration += w.get("execution_duration", 0.0) or 0.0
            for t in w.get("tasks", {}).values():
                total_retries += t.get("retry_count", 0)

        return {
            "total_workflows": total,
            "running_workflows": running,
            "completed_workflows": completed,
            "failed_workflows": failed,
            "total_retries": total_retries,
            "average_duration": total_duration / total if total > 0 else 0.0,
        }


_observability_service_instance: Optional[EventObservabilityService] = None


def get_observability_service() -> EventObservabilityService:
    """Returns the global singleton EventObservabilityService instance."""
    global _observability_service_instance
    if _observability_service_instance is None:
        _observability_service_instance = EventObservabilityService(
            event_bus=get_event_bus()
        )
    return _observability_service_instance
