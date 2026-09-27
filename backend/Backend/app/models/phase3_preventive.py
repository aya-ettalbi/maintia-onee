from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import Priority
from app.db.base import Base, TimestampMixin


class PreventiveMaintenancePlan(TimestampMixin, Base):
    __tablename__ = "preventive_maintenance_plans"

    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipments.id"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency_days: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(30),
        default=Priority.MEDIUM.value,
        nullable=False,
    )
    assigned_technician_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=True,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    last_executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )


class PreventiveMaintenanceExecution(TimestampMixin, Base):
    __tablename__ = "preventive_maintenance_executions"

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("preventive_maintenance_plans.id"),
        index=True,
        nullable=False,
    )
    intervention_id: Mapped[int] = mapped_column(
        ForeignKey("interventions.id"),
        unique=True,
        index=True,
        nullable=False,
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(40),
        default="INTERVENTION_CREATED",
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )


class GeneratedMaintenanceReport(TimestampMixin, Base):
    __tablename__ = "generated_maintenance_reports"

    report_type: Mapped[str] = mapped_column(
        String(50),
        default="MONTHLY",
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generated_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
