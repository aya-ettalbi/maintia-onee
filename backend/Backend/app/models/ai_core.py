from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EquipmentHistoricalLink(TimestampMixin, Base):
    """
    Relie un équipement réel du parc à une demande historique.

    Le lien est séparé de HistoricalRequest afin de préserver les données
    importées et de permettre une validation progressive des rapprochements.
    """

    __tablename__ = "equipment_historical_links"
    __table_args__ = (
        UniqueConstraint(
            "equipment_id",
            "historical_request_id",
            name="uq_equipment_historical_link",
        ),
        Index(
            "ix_equipment_historical_links_equipment",
            "equipment_id",
        ),
        Index(
            "ix_equipment_historical_links_request",
            "historical_request_id",
        ),
        Index(
            "ix_equipment_historical_links_validation",
            "validation_status",
        ),
    )

    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipments.id", ondelete="CASCADE"),
        nullable=False,
    )
    historical_request_id: Mapped[int] = mapped_column(
        ForeignKey("historical_requests.id", ondelete="CASCADE"),
        nullable=False,
    )

    link_method: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    validation_status: Mapped[str] = mapped_column(
        String(30),
        default="AUTO",
        nullable=False,
    )

    source_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    validated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class RagSyncQueue(TimestampMixin, Base):
    """
    File persistante PostgreSQL -> Qdrant.

    Les enregistrements PENDING seront traités plus tard par un worker RAG.
    PostgreSQL reste la source officielle des données.
    """

    __tablename__ = "rag_sync_queue"
    __table_args__ = (
        Index(
            "ix_rag_sync_queue_status_created",
            "status",
            "created_at",
        ),
        Index(
            "ix_rag_sync_queue_source",
            "source_type",
            "source_id",
        ),
    )

    source_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    operation: Mapped[str] = mapped_column(
        String(20),
        default="UPSERT",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
