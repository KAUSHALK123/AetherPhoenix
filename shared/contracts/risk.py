from uuid import UUID

from pydantic import BaseModel, Field

from shared.contracts.permission import RiskLevel


class RiskAssessment(BaseModel):
    task_id: UUID
    risk_level: RiskLevel
    score: int
    reasoning: str


class Conflict(BaseModel):
    tasks_involved: list[UUID]
    description: str


class RiskAnalysisResult(BaseModel):
    assessments: list[RiskAssessment] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    overall_risk_level: RiskLevel = RiskLevel.SAFE
    highest_score: int = 0
    safety_metadata: dict[str, list[str]] = Field(default_factory=dict)
