from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class FailureForecast(TimestampMixin, Base):
    __tablename__ = "failure_forecasts"
    __table_args__ = (
        Index(
            "ix_failure_forecasts_equipment_date",
            "equipment_id",
            "forecasted_at",
        ),
        Index(
            "ix_failure_forecasts_risk_level",
            "risk_level",
        ),
        Index(
            "ix_failure_forecasts_validation_status",
            "validation_status",
        ),
    )

    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipments.id"),
        nullable=False,
    )
    forecasted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    horizon_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    failure_probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    probability_calibrated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    evidence_confidence: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    predicted_failure_family: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    estimated_start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    estimated_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    factors: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )
    recommended_actions: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )
    evidence_summary: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    similar_references: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    methodology_version: Mapped[str] = mapped_column(
        String(80),
        default="HEURISTIC_HISTORY_V1",
        nullable=False,
    )
    llm_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    model_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    recommendation_id: Mapped[int | None] = mapped_column(
        ForeignKey("recommendations.id"),
        nullable=True,
    )
    notification_created: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    validation_status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
    )
    validated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    validation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    actual_failure_occurred: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    actual_failure_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )


class FailureForecastRun(TimestampMixin, Base):
    __tablename__ = "failure_forecast_runs"
    __table_args__ = (
        Index(
            "ix_failure_forecast_runs_started_at",
            "started_at",
        ),
        Index(
            "ix_failure_forecast_runs_status",
            "status",
        ),
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="RUNNING",
        nullable=False,
    )
    horizon_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    only_with_history: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    requested_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    processed_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    high_risk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    medium_risk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    low_risk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    notifications_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    recommendations_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_details: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    triggered_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
