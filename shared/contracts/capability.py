from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from shared.contracts.task import TaskCategory


class Capability(BaseModel):
    """
    Capability contract defining an abstract skill that a worker can perform.
    """

    capability_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Unique string identifier for the capability")
    description: str = Field(
        ..., description="Human-readable description of what it does"
    )
    version: str = Field(default="1.0.0")
    enabled: bool = Field(default=True)
    category: TaskCategory = Field(..., description="Broad classification category")
    risk_level: str = Field(default="LOW", description="LOW, MEDIUM, HIGH, CRITICAL")
    required_permissions: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    supported_platforms: list[str] = Field(default_factory=lambda: ["ALL"])
