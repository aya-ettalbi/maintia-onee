from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ForecastRiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
ForecastValidationStatus = Literal[
    "PENDING",
    "CONFIRMED",
    "PARTIAL",
    "REJECTED",
]


class FailureForecastNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=3000)
    risk_explanation: str = Field(min_length=1, max_length=5000)
    warnings: list[str] = Field(default_factory=list, max_length=10)


class FailureForecastRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    forecasted_at: datetime
    horizon_days: int
    risk_score: float
    failure_probability: float
    probability_calibrated: bool
    risk_level: str
    evidence_confidence: str
    predicted_failure_family: str | None
    estimated_start_date: date | None
    estimated_end_date: date | None
    factors: list
    recommended_actions: list
    evidence_summary: dict
    similar_references: list
    explanation: str
    methodology_version: str
    llm_used: bool
    model_name: str | None
    recommendation_id: int | None
    notification_created: bool
    validation_status: str
    validated_by_id: int | None
    validated_at: datetime | None
    validation_notes: str | None
    actual_failure_occurred: bool | None
    actual_failure_date: date | None
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime


class FailureForecastValidation(BaseModel):
    validation_status: Literal[
        "CONFIRMED",
        "PARTIAL",
        "REJECTED",
    ]
    notes: str | None = Field(default=None, max_length=5000)
    actual_failure_occurred: bool | None = None
    actual_failure_date: date | None = None


class FailureForecastBatchRequest(BaseModel):
    horizon_days: int = Field(default=90, ge=30, le=365)
    limit: int = Field(default=500, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)
    only_with_history: bool = True
    create_actions: bool = True


class FailureForecastBatchResponse(BaseModel):
    run_id: int
    status: str
    horizon_days: int
    processed_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    notifications_created: int
    recommendations_created: int
    error_count: int


class FailureForecastRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    ended_at: datetime | None
    status: str
    horizon_days: int
    only_with_history: bool
    requested_limit: int
    processed_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    notifications_created: int
    recommendations_created: int
    error_count: int
    error_details: list
    triggered_by_id: int | None
    created_at: datetime
    updated_at: datetime


class FailureForecastSummary(BaseModel):
    total_forecasts: int
    latest_forecasts: int
    high_risk: int
    medium_risk: int
    low_risk: int
    pending_validation: int
    confirmed: int
    partial: int
    rejected: int
    latest_run: FailureForecastRunRead | None
    warning: str
