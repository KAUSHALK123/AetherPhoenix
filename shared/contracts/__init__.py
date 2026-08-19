"""Runtime contracts for AI Desktop Assistant agents and components."""

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.capability import Capability
from shared.contracts.context_retrieval import (
    AgentType,
    ContextRetrievalRequest,
    ContextRetrievalResponse,
)
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
from shared.contracts.memory import (
    ConversationMemoryEntry,
    MemoryCategory,
    MemoryQuery,
    sanitize_memory_content,
    sanitize_memory_metadata,
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
from shared.contracts.rag import (
    RAGContext,
    RAGSourceType,
    RetrievalQuery,
    RetrievedContextItem,
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
from shared.contracts.task_history import (
    TaskHistoryRecord,
    WorkflowHistoryRecord,
)
from shared.contracts.tool import Tool, ToolHealth, ToolState
from shared.contracts.vector import VectorRecord, VectorSearchResult
from shared.contracts.workflow import (
    ExecutionMode,
    ProgressState,
    SharedWorkflowState,
    WorkflowMetadata,
    WorkflowStatus,
)

__all__ = [
    "AgentType",
    # Artifact
    "Artifact",
    "ArtifactType",
    # Capability
    "Capability",
    "CapabilityFailureInfo",
    "CaptureRegion",
    "CaptureSource",
    "ClarificationResult",
    "CodeBlockElement",
    "Conflict",
    "ContextRetrievalRequest",
    "ContextRetrievalResponse",
    "ConversationMemoryEntry",
    "DependencyType",
    "DocumentElement",
    "DocumentElementType",
    # Document
    "DocumentFormat",
    "DocumentGenerationResult",
    "DocumentSection",
    "ErrorParserOutput",
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
    "ImageFormat",
    "IntentCategory",
    "KeyboardActionRequest",
    "KeyboardActionResult",
    "KeyboardActionType",
    "ListElement",
    "MemoryCategory",
    "MemoryQuery",
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
    # RAG
    "RAGContext",
    "RAGSourceType",
    "RecoveryAction",
    "RecoveryPlan",
    "ReplanningContext",
    "RetrievalQuery",
    "RetrievedContextItem",
    "RetryRequest",
    "RetryResult",
    "RetryStatus",
    "RiskAnalysisResult",
    # Risk
    "RiskAssessment",
    "RiskLevel",
    "RollbackInfo",
    "RootCauseAnalysis",
    "RuntimeEvent",
    "ScreenResolution",
    "ScreenshotRequest",
    "ScreenshotResult",
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
    "TaskHistoryRecord",
    "TaskPriority",
    # Task
    "TaskStatus",
    # Tool
    "Tool",
    "ToolHealth",
    "ToolState",
    "UserRequirement",
    "VectorRecord",
    "VectorSearchResult",
    "WorkerExecutionLog",
    "WorkflowHistoryRecord",
    "WorkflowMetadata",
    "WorkflowStatus",
    "sanitize_memory_content",
    "sanitize_memory_metadata",
]
