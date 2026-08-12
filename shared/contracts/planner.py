import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator, field_validator

from shared.contracts.task import Task, TaskType


class IntentCategory(str, Enum):
    DATA_RETRIEVAL = "data_retrieval"
    SYSTEM_MODIFICATION = "system_modification"
    CONTENT_GENERATION = "content_generation"
    UNKNOWN = "unknown"


class GoalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserRequirement(BaseModel):
    """
    Represents the parsed structure of a user's request.
    """

    intent: IntentCategory = Field(
        default=IntentCategory.UNKNOWN, description="The primary goal of the request."
    )
    requirements: List[str] = Field(
        default_factory=list, description="Specific things the user wants."
    )
    constraints: List[str] = Field(
        default_factory=list, description="Limitations or constraints on the request."
    )
    category: str = Field(default="general", description="General classification tag.")


class Goal(BaseModel):
    """
    Represents a structured goal node in the goal hierarchy.
    """

    goal_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the goal.",
    )
    title: str = Field(..., description="Short title describing the goal.")
    description: str = Field(..., description="Detailed description of the goal.")
    category: IntentCategory = Field(
        default=IntentCategory.UNKNOWN, description="Category of the goal intent."
    )
    priority: GoalPriority = Field(
        default=GoalPriority.MEDIUM, description="Priority level of the goal."
    )
    expected_outcomes: List[str] = Field(
        default_factory=list,
        description="Expected outcomes or artifacts from fulfilling this goal.",
    )
    sub_goals: List["Goal"] = Field(
        default_factory=list, description="Child sub-goals in the goal hierarchy."
    )
    parent_id: Optional[str] = Field(
        None, description="Optional ID of the parent goal."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata associated with this goal."
    )


Goal.model_rebuild()


class GoalExtractionResult(BaseModel):
    """
    Result of the Goal Extraction Engine analysis.
    """

    primary_goal: Optional[Goal] = Field(
        None, description="Root goal representing the main user objective."
    )
    goal_count: int = Field(
        0, description="Total number of goals identified (primary + sub-goals)."
    )
    confidence_score: float = Field(
        0.0, description="Confidence score of the goal extraction (0.0 to 1.0)."
    )
    is_valid: bool = Field(
        True, description="Whether the extracted goal structure is valid."
    )
    validation_messages: List[str] = Field(
        default_factory=list, description="Validation feedback or error messages."
    )
    extraction_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata about the extraction process."
    )


class ClarificationResult(BaseModel):
    """
    Result of the clarification engine's analysis.
    """

    needs_clarification: bool = Field(
        ..., description="True if the request is incomplete."
    )
    question: Optional[str] = Field(
        None, description="The follow-up question to ask the user."
    )
    missing_fields: List[str] = Field(
        default_factory=list, description="List of missing required fields."
    )


class PlannerRequest(BaseModel):
    """
    Represents a user request sent to the Planner Chat Interface.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the conversation session."
    )
    message: str = Field(..., description="The text message or goal from the user.")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional context such as file paths or metadata.",
    )


class PlannerResponse(BaseModel):
    """
    Represents the output from the Planner Chat Interface back to the user.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the conversation session."
    )
    status: str = Field(
        ...,
        description="Status of the request (e.g., 'clarifying', 'planning', 'ready').",
    )
    reply: Optional[str] = Field(
        None, description="A text reply, usually a clarification question."
    )
    action: Optional[str] = Field(None, description="The next action if applicable.")


class TaskDecompositionPlan(BaseModel):
    """
    Output model of the Task Decomposition Engine.
    Contains tasks, dependency graph, hierarchy mapping, and ordered execution plan.
    """
    workflow_id: UUID = Field(..., description="Unique ID of the workflow.")
    goal: str = Field(..., description="Original goal string.")
    tasks: List[Task] = Field(default_factory=list, description="Decomposed tasks.")
    dependency_graph: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Dependency mapping of task_id string -> list of prerequisite task_id strings."
    )
    task_hierarchy: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Task hierarchy mapping parent_task_id string -> list of child_task_id strings."
    )
    execution_order: List[UUID] = Field(
        default_factory=list,
        description="Topologically sorted execution order of task UUIDs."
    )
    estimated_total_duration_seconds: Optional[int] = Field(
        default=None,
        description="Estimated total duration in seconds."
    )
    unsupported_capabilities: List[str] = Field(
        default_factory=list,
        description="Capabilities identified but not supported."
    )


class PlanVersion(str, Enum):
    """Supported semantic versions for the Planner JSON Contract."""
    V1_0 = "1.0"


class PlanMetadata(BaseModel):
    """Contextual metadata about the generated plan."""
    version: PlanVersion = PlanVersion.V1_0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    planner_model: str = Field(default="gemini-pro", description="LLM used for planning")
    execution_mode: str = Field(default="ASSISTED", description="Execution mode requested")
    session_id: Optional[str] = None


class PlannerOutput(BaseModel):
    """
    Structured execution plan output produced by the Planner Agent.
    Serves as the rigorous JSON Contract for Workflow Engine consumption.
    """
    metadata: PlanMetadata = Field(default_factory=PlanMetadata)
    workflow_spec: str = Field(description="High-level description of the workflow logic")
    tasks: List[Task] = Field(default_factory=list, description="Ordered/unordered list of task executions")
    dependency_graph: Dict[UUID, List[UUID]] = Field(
        default_factory=dict, 
        description="Graph mapping task_id to a list of prerequisite task_ids"
    )
    estimated_time_seconds: int = Field(default=0, ge=0)
    risks: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    expected_outputs: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    execution_summary: str = Field(default="", description="Summary of the execution plan")
    parallel_groups: List[List[UUID]] = Field(default_factory=list, description="Groups of tasks that can run in parallel")

    @field_validator("dependency_graph")
    @classmethod
    def validate_acyclic_graph(cls, v: Dict[UUID, List[UUID]]) -> Dict[UUID, List[UUID]]:
        """Validates that the dependency graph contains no cycles."""
        visited = set()
        path = set()

        def visit(node: UUID):
            if node in path:
                raise ValueError(f"Cycle detected in dependency graph involving task {node}")
            if node in visited:
                return
            
            visited.add(node)
            path.add(node)
            for neighbor in v.get(node, []):
                visit(neighbor)
            path.remove(node)

        for task_id in v.keys():
            visit(task_id)

        return v

    @model_validator(mode="after")
    def validate_tasks_match_graph(self) -> "PlannerOutput":
        """Ensures all tasks referenced in the dependency graph exist in the tasks list."""
        task_ids = {task.task_id for task in self.tasks}
        
        for task_id, dependencies in self.dependency_graph.items():
            if task_id not in task_ids:
                raise ValueError(f"Task {task_id} in dependency graph is missing from tasks list")
            for dep in dependencies:
                if dep not in task_ids:
                    raise ValueError(f"Dependency {dep} for task {task_id} is missing from tasks list")
                    
        return self

    @model_validator(mode="after")
    def validate_tasks_tools(self) -> "PlannerOutput":
        """Ensures leaf tasks have tools and phase tasks do not."""
        for task in self.tasks:
            if task.task_type == TaskType.LEAF and not task.required_tool:
                raise ValueError(f"LEAF task {task.task_id} must have a non-empty required_tool")
            if task.task_type == TaskType.PHASE and task.required_tool:
                raise ValueError(f"PHASE task {task.task_id} must have an empty required_tool")
        return self
