"""Runtime contracts for AI Desktop Assistant agents and components."""

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.capability import Capability
from shared.contracts.document import (
    DocumentElement,
    DocumentElementType,
    DocumentFormat,
    DocumentGenerationResult,
    DocumentSection,
    StructuredDocumentInput,
)
from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionMetrics,
    ExecutionResult,
    FailureType,
    HealingRequest,
    HealingResult,
    HealingState,
    RecoveryStrategyType,
    RootCauseCategory,
    SupervisorDecision,
    SupervisorValidation,
    TaskError,
    TaskFailureReport,
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
from shared.contracts.recovery_plan import (
    ErrorParserOutput,
    RecoveryAction,
    RecoveryPlan,
    RootCauseAnalysis,
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
    "ClarificationResult",
    "CodeBlockElement",
    "Conflict",
    "DependencyType",
    "DocumentElement",
    "DocumentElementType",
    # Document
    "DocumentFormat",
    "DocumentGenerationResult",
    "DocumentSection",
    "EventSource",
    # Event
    "EventType",
    # Execution
    "ExecutionMetrics",
    "ExecutionMode",
    "ExecutionPhase",
    "ExecutionResult",
    "ExecutionStatus",
    "FailureType",
    "Goal",
    "GoalExtractionResult",
    "GoalPriority",
    "HeadingElement",
    "HealingRequest",
    "HealingResult",
    "HealingState",
    "IntentCategory",
    "ListElement",
    "PDFDocumentInput",
    "PDFElement",
    # PDF
    "PDFElementType",
    "PDFGenerationResult",
    "ParagraphElement",
    "PermissionRequest",
    "PermissionStatus",
    # Permission
    "PermissionType",
    "PlanMetadata",
    "PlanVersion",
    "PlannerOutput",
    # Planner
    "PlannerRequest",
    "PlannerResponse",
    "ProgressState",
    "RecoveryStrategyType",
    "RiskAnalysisResult",
    # Risk
    "RiskAssessment",
    "Conflict",
    "ErrorParserOutput",
    "RecoveryAction",
    "RecoveryPlan",
    # Recovery Plan
    "RiskAnalysisResult",
    "RiskLevel",
    "RollbackInfo",
    "RootCauseAnalysis",
    "RootCauseCategory",
    "RuntimeEvent",
    "SharedWorkflowState",
    "StructuredDocumentInput",
    "SupervisorDecision",
    "SupervisorValidation",
    "TableElement",
    "Task",
    "TaskCategory",
    "TaskDecompositionPlan",
    "TaskDependency",
    "TaskError",
    "TaskFailureReport",
    "TaskPriority",
    # Task
    "TaskStatus",
    # Tool
    "Tool",
    "ToolHealth",
    "ToolState",
    "UserRequirement",
    "WorkerExecutionLog",
    "WorkflowMetadata",
    # Workflow
    "WorkflowStatus",
]
