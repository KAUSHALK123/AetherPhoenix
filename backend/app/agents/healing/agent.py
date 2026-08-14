"""Healing Agent Core.

Coordinates failure analysis and root cause detection for workflow self-healing.
Integrates RootCauseAnalyzer and produces structured diagnostic results without
executing recovery actions directly.
"""

import logging
from typing import Any, Dict, List, Optional

from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionResult,
    TaskFailureReport,
)
from shared.contracts.healing import RootCauseResult
from shared.contracts.task import Task
from shared.contracts.workflow import SharedWorkflowState

from app.agents.healing.root_cause_analyzer import RootCauseAnalyzer
from app.core.events.bus import EventBus
from app.runtime.interfaces import AgentRegistration, BaseAgent

logger = logging.getLogger(__name__)


class HealingAgent(BaseAgent):
    """
    Healing Core Agent responsible for analyzing task execution failures,
    determining root causes, and publishing diagnostic reports.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        analyzer: Optional[RootCauseAnalyzer] = None,
    ) -> None:
        self.event_bus = event_bus
        self.analyzer = analyzer or RootCauseAnalyzer()

    @property
    def registration(self) -> AgentRegistration:
        """Returns registration metadata for Healing Agent."""
        return AgentRegistration(
            name="HealingAgent",
            version="1.0.0",
            description=(
                "Performs failure analysis and root cause diagnosis for "
                "failed task executions in the AetherPhoenix runtime."
            ),
        )

    async def initialize(self) -> None:
        """Lifecycle hook called when the agent is registered."""
        logger.info("HealingAgent initialized.")

    async def shutdown(self) -> None:
        """Lifecycle hook called when the kernel shuts down."""
        logger.info("HealingAgent shut down.")

    async def _emit_event(
        self,
        event_type: EventType,
        payload: dict,
        workflow_id: str,
        task_id: str | None = None,
    ) -> None:
        if self.event_bus:
            event = RuntimeEvent(
                workflow_id=workflow_id,
                task_id=task_id,
                event_type=event_type,
                source_component=EventSource.HEALING,
                payload=payload,
            )
            await self.event_bus.publish(event)

    async def analyze_failure(
        self,
        report: Optional[TaskFailureReport] = None,
        task: Optional[Task] = None,
        result: Optional[ExecutionResult] = None,
        state: Optional[SharedWorkflowState] = None,
        tool_info: Optional[Dict[str, Any]] = None,
        logs: Optional[List[str]] = None,
    ) -> RootCauseResult:
        """
        Runs root cause analysis on a failed task execution.
        """
        task_id_str = (
            str(report.task_id) if report else (str(task.task_id) if task else "")
        )
        workflow_id_str = (
            str(report.workflow_id)
            if report
            else (str(task.workflow_id) if task else "")
        )

        logger.info(f"HealingAgent analyzing failure for task: {task_id_str}")

        await self._emit_event(
            event_type=EventType.HEALING_STARTED,
            payload={"task_id": task_id_str, "status": "STARTED"},
            workflow_id=workflow_id_str,
            task_id=task_id_str,
        )

        analysis_result = self.analyzer.analyze(
            report=report,
            task=task,
            result=result,
            state=state,
            tool_info=tool_info,
            logs=logs,
        )

        await self._emit_event(
            event_type=EventType.HEALING_COMPLETED,
            payload={
                "task_id": str(analysis_result.task_id),
                "likely_root_cause": analysis_result.likely_root_cause,
                "category": analysis_result.category.value,
                "confidence_score": analysis_result.confidence_score,
                "is_confident": analysis_result.is_confident,
                "explanation": analysis_result.diagnostic_explanation,
            },
            workflow_id=str(analysis_result.workflow_id),
            task_id=str(analysis_result.task_id),
        )

        return analysis_result

    async def execute(
        self,
        task: Task,
        *args: Any,
        **kwargs: Any,
    ) -> RootCauseResult:
        """
        Main Agent execution entrypoint fulfilling BaseAgent contract interface.
        Delegates to analyze_failure.
        """
        report = kwargs.get("report") or (
            args[0] if args and isinstance(args[0], TaskFailureReport) else None
        )
        result = kwargs.get("result") or (
            args[1] if len(args) > 1 and isinstance(args[1], ExecutionResult) else None
        )
        state = kwargs.get("state") or (
            args[2]
            if len(args) > 2 and isinstance(args[2], SharedWorkflowState)
            else None
        )
        tool_info = kwargs.get("tool_info")
        logs = kwargs.get("logs")

        return await self.analyze_failure(
            report=report,
            task=task,
            result=result,
            state=state,
            tool_info=tool_info,
            logs=logs,
        )
