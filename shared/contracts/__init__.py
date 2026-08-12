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
from shared.contracts.execution_log import (
    ExecutionPhase,
    ExecutionStatus,
    WorkerExecutionLog,
)
from shared.contracts.pdf import (
    CodeBlockElement,
    HeadingElement,
    ListElement,
    ParagraphElement,
    PDFDocumentInput,
    PDFElement,
    PDFElementType,
    PDFGenerationResult,
    TableElement,
)
from shared.contracts.permission import (
    PermissionRequest,
    PermissionStatus,
    PermissionType,
    RiskLevel,
)
from shared.contracts.planner import (
    ClarificationResult,
    Goal,
    GoalExtractionResult,
    GoalPriority,
    IntentCategory,
    PlanMetadata,
    PlannerOutput,
    PlannerRequest,
    PlannerResponse,
    PlanVersion,
    TaskDecompositionPlan,
    UserRequirement,
)
from shared.contracts.risk import (
    Conflict,
    RiskAnalysisResult,
    RiskAssessment,
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
    # PDF
    "PDFElementType",
    "HeadingElement",
    "ParagraphElement",
    "ListElement",
    "TableElement",
    "CodeBlockElement",
    "PDFElement",
    "PDFDocumentInput",
    "PDFGenerationResult",
    "ExecutionPhase",
    "ExecutionStatus",
    "WorkerExecutionLog",
    # Permission
    "PermissionType",
    "PermissionStatus",
    "RiskLevel",
    "PermissionRequest",
    # Planner
    "PlannerRequest",
    "PlannerResponse",
    "IntentCategory",
    "GoalPriority",
    "Goal",
    "GoalExtractionResult",
    "UserRequirement",
    "ClarificationResult",
    "TaskDecompositionPlan",
    "PlanVersion",
    "PlanMetadata",
    "PlannerOutput",
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
    # Workflow
    "WorkflowStatus",
    "ExecutionMode",
    "WorkflowMetadata",
    "ProgressState",
    "SharedWorkflowState",
    # Risk
    "RiskAssessment",
    "Conflict",
    "RiskAnalysisResult",
]
