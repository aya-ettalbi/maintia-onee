from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SparePart(TimestampMixin, Base):
    __tablename__ = "spare_parts"

    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(150), nullable=True)
    quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    minimum_threshold: Mapped[int] = mapped_column(default=0, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    supplier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class StockMovement(TimestampMixin, Base):
    __tablename__ = "stock_movements"

    part_id: Mapped[int] = mapped_column(ForeignKey("spare_parts.id"), index=True, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    intervention_id: Mapped[int | None] = mapped_column(ForeignKey("interventions.id"), nullable=True)
    performed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class InterventionPart(TimestampMixin, Base):
    __tablename__ = "intervention_parts"
    __table_args__ = (UniqueConstraint("intervention_id", "part_id", name="uq_intervention_part"),)

    intervention_id: Mapped[int] = mapped_column(ForeignKey("interventions.id"), index=True, nullable=False)
    part_id: Mapped[int] = mapped_column(ForeignKey("spare_parts.id"), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
