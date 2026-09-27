from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    InterventionStatus,
    MaintenanceType,
    Priority,
    RequestStatus,
)
from app.db.base import Base, TimestampMixin


class MaintenanceRequest(TimestampMixin, Base):
    __tablename__ = "maintenance_requests"

    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipments.id"), index=True, nullable=False)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    assigned_technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(150), nullable=True)
    priority: Mapped[str] = mapped_column(String(30), default=Priority.MEDIUM.value, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), default=RequestStatus.SUBMITTED.value, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Intervention(TimestampMixin, Base):
    __tablename__ = "interventions"

    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("maintenance_requests.id"), nullable=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipments.id"), index=True, nullable=False)
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    maintenance_type: Mapped[str] = mapped_column(
        String(40), default=MaintenanceType.CORRECTIVE.value, nullable=False
    )
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(40), default=InterventionStatus.PLANNED.value, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    test_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class InterventionStatusHistory(TimestampMixin, Base):
    __tablename__ = "intervention_status_history"

    intervention_id: Mapped[int] = mapped_column(ForeignKey("interventions.id"), index=True, nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class InterventionAction(TimestampMixin, Base):
    __tablename__ = "intervention_actions"

    intervention_id: Mapped[int] = mapped_column(ForeignKey("interventions.id"), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    performed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
