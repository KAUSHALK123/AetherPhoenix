"""Runtime contracts for AI Desktop Assistant agents and components."""

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.capability import Capability
from shared.contracts.desktop import (
    MouseActionRequest,
    MouseActionResult,
    MouseActionType,
    MouseButton,
    MousePosition,
    ScreenResolution,
)
from shared.contracts.document import (
    DocumentElement,
    DocumentElementType,
    DocumentFormat,
    DocumentGenerationResult,
    DocumentSection,
    StructuredDocumentInput,
)
from shared.contracts.escalation import (
    EscalationReason,
    EscalationRequest,
    EscalationResult,
    EscalationSeverity,
)
from shared.contracts.event import EventSource, EventType, RuntimeEvent
from shared.contracts.execution import (
    ExecutionMetrics,
    ExecutionResult,
    FailureType,
    HealingResult,
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
from shared.contracts.feedback import (
    CapabilityFailureInfo,
    FailureSummary,
    HealingSummary,
    PlannerFeedback,
    ReplanningContext,
)
from shared.contracts.keyboard import (
    KeyboardActionRequest,
    KeyboardActionResult,
    KeyboardActionType,
    SpecialKey,
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
from shared.contracts.retry import (
    RetryRequest,
    RetryResult,
    RetryStatus,
)
from shared.contracts.risk import (
    Conflict,
    RiskAnalysisResult,
    RiskAssessment,
)
from shared.contracts.screenshot import (
    CaptureRegion,
    CaptureSource,
    ImageFormat,
    ScreenshotRequest,
    ScreenshotResult,
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
    PlannerOutput,
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
    "CapabilityFailureInfo",
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
    "EscalationReason",
    "EscalationRequest",
    "EscalationResult",
    "EscalationSeverity",
    "EventSource",
    # Event
    "EventType",
    # Execution
    "ExecutionMetrics",
    "ExecutionMode",
    "ExecutionPhase",
    "ExecutionResult",
    "ExecutionStatus",
    "FailureSummary",
    "FailureType",
    "Goal",
    "GoalExtractionResult",
    "GoalPriority",
    "HeadingElement",
    "HealingResult",
    "HealingSummary",
    "IntentCategory",
    "KeyboardActionRequest",
    "KeyboardActionResult",
    "KeyboardActionType",
    "ListElement",
    "MouseActionRequest",
    "MouseActionResult",
    "MouseActionType",
    "MouseButton",
    "MousePosition",
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
    # Feedback
    "PlannerFeedback",
    "PlannerOutput",
    # Planner
    "PlannerRequest",
    "PlannerResponse",
    "ProgressState",
    "RecoveryAction",
    "RecoveryPlan",
    "ReplanningContext",
    "RetryRequest",
    "RetryResult",
    "RetryStatus",
    "RiskAnalysisResult",
    # Risk
    "RiskAssessment",
    "RiskLevel",
    "RootCauseAnalysis",
    "ErrorParserOutput",
    "RollbackInfo",
    "RuntimeEvent",
    "CaptureRegion",
    "CaptureSource",
    "ImageFormat",
    "ScreenshotRequest",
    "ScreenshotResult",
    "ScreenResolution",
    "SharedWorkflowState",
    "SpecialKey",
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
    # Workflow
    "WorkflowStatus",
    "ExecutionMode",
    "WorkflowMetadata",
    "PlannerOutput",
    "ProgressState",
    "SharedWorkflowState",
    # Risk
    "RiskAssessment",
    "Conflict",
    "RiskAnalysisResult",
]
