"""Runtime contracts for AI Desktop Assistant agents and components."""

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.capability import Capability
from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionMetrics,
    ExecutionResult,
    HealingResult,
    SupervisorValidation,
    TaskError,
)
from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)
from shared.contracts.task import (
    DependencyType,
    RollbackInfo,
    Task,
    TaskCategory,
    TaskDependency,
    TaskPriority,
    TaskStatus,
)
from shared.contracts.tool import Tool, ToolHealth, ToolState
from shared.contracts.planner import (
    PlanVersion,
    PlanMetadata,
    PlannerOutput,
)
from shared.contracts.workflow import (
    ExecutionMode,
    ProgressState,
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

__all__ = [
    # Artifact
    "Artifact",
    "ArtifactType",
    # Capability
    "Capability",
    # Event
    "EventType",
    "EventSource",
    "RuntimeEvent",
    # Execution
    "ExecutionMetrics",
    "TaskError",
    "ExecutionResult",
    "SupervisorValidation",
    "HealingResult",
    # Permission
    "PermissionType",
    "PermissionStatus",
    "RiskLevel",
    "PermissionRequest",
    # Task
    "TaskStatus",
    "TaskPriority",
    "TaskCategory",
    "DependencyType",
    "TaskDependency",
    "RollbackInfo",
    "Task",
    # Tool
    "Tool",
    "ToolState",
    "ToolHealth",
    # Planner
    "PlanVersion",
    "PlanMetadata",
    "PlannerOutput",
    # Workflow
    "WorkflowStatus",
    "ExecutionMode",
    "WorkflowMetadata",
    "ProgressState",
    "SharedWorkflowState",
]
