from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdminPasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class NotificationUnreadCount(BaseModel):
    unread_count: int


class TriageRequest(BaseModel):
    description: str = Field(min_length=5, max_length=4000)
    equipment_code: str | None = Field(default=None, max_length=100)


class TriageResponse(BaseModel):
    incident_type: str
    classification_group: str
    suggested_priority: str
    suggested_team: str
    confidence: str
    confidence_score: int
    matched_rules: list[str]
    equipment_code: str | None
    human_validation_required: bool = True


class RiskAssessmentResponse(BaseModel):
    equipment_id: int
    equipment_code: str
    score: int
    level: str
    factors: list[str]
    recommended_action: str
    calculation_version: str
    metrics: dict[str, int | float | str | None]
    calculated_at: datetime


class RecurrentFailureItem(BaseModel):
    classification: str
    occurrence_count: int
    latest_date: datetime | None


class RecurrentFailuresResponse(BaseModel):
    period_months: int
    minimum_occurrences: int
    total_groups: int
    items: list[RecurrentFailureItem]


class StockShortageRiskItem(BaseModel):
    part_id: int
    part_code: str
    part_name: str
    current_quantity: int
    minimum_threshold: int
    outgoing_quantity: int
    average_monthly_usage: float
    months_of_coverage: float | None
    suggested_order_quantity: int
    risk: str


class StockShortageRisksResponse(BaseModel):
    lookback_days: int
    total_at_risk: int
    items: list[StockShortageRiskItem]
