from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator, field_validator

from shared.contracts.task import Task


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
