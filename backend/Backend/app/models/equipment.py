from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import EquipmentStatus
from app.db.base import Base, TimestampMixin


class EquipmentCategory(TimestampMixin, Base):
    __tablename__ = "equipment_categories"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Equipment(TimestampMixin, Base):
    __tablename__ = "equipments"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("equipment_categories.id"), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(150), unique=True, nullable=True)
    acquisition_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    commissioning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(40), default=EquipmentStatus.IN_SERVICE.value, nullable=False
    )
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    current_service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    warranty_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class EquipmentAssignment(TimestampMixin, Base):
    __tablename__ = "equipment_assignments"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipments.id"), index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
