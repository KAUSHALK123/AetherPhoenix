from enum import Enum
from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, Field

from shared.contracts.permission import RiskLevel



class RiskAssessment(BaseModel):
    task_id: UUID
    risk_level: RiskLevel
    score: int
    reasoning: str


class Conflict(BaseModel):
    tasks_involved: List[UUID]
    description: str


class RiskAnalysisResult(BaseModel):
    assessments: List[RiskAssessment] = Field(default_factory=list)
    conflicts: List[Conflict] = Field(default_factory=list)
    overall_risk_level: RiskLevel = RiskLevel.SAFE
    highest_score: int = 0
    safety_metadata: Dict[str, List[str]] = Field(default_factory=dict)
