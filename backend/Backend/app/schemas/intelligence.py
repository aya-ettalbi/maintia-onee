from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RecommendationStatus


class DiagnosticRequest(BaseModel):
    description: str = Field(min_length=5)
    top_k: int = Field(default=5, ge=1, le=10)


class DiagnosticSuggestion(BaseModel):
    intervention_id: int
    similarity: float
    diagnosis: str | None
    solution: str | None


class RiskScoreResponse(BaseModel):
    equipment_id: int
    score: float
    level: str
    factors: list[str]
    recommended_action: str


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int | None
    part_id: int | None
    recommendation_type: str
    priority: str
    title: str
    observation: str
    justification: str
    recommended_action: str
    risk_score: float
    risk_level: str
    status: str
    due_date: date | None
    generated_at: datetime
    validated_by_id: int | None
    created_at: datetime
    updated_at: datetime


class RecommendationUpdate(BaseModel):
    status: RecommendationStatus
    due_date: date | None = None
