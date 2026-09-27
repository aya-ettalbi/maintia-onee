from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import RecommendationStatus, RiskLevel
from app.db.base import Base, TimestampMixin


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"

    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipments.id"), nullable=True)
    part_id: Mapped[int | None] = mapped_column(ForeignKey("spare_parts.id"), nullable=True)
    recommendation_type: Mapped[str] = mapped_column(String(60), nullable=False)
    priority: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(30), default=RiskLevel.LOW.value, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), default=RecommendationStatus.NEW.value, nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    validated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
