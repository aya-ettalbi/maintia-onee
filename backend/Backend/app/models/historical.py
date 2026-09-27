from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HistoricalRequest(TimestampMixin, Base):
    __tablename__ = "historical_requests"
    __table_args__ = (
        Index("ix_historical_requests_numero_demande", "numero_demande"),
        Index("ix_historical_requests_statut", "statut"),
        Index("ix_historical_requests_date_creation", "date_creation_demande"),
    )

    source_key: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    numero_demande: Mapped[str] = mapped_column(String(100), nullable=False)

    date_creation_demande: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_resolution_demande: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    nature_demande: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description_demande: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail_classification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    statut: Mapped[str | None] = mapped_column(String(100), nullable=True)

    demandeur: Mapped[str | None] = mapped_column(String(255), nullable=True)
    matricule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nom_demandeur: Mapped[str | None] = mapped_column(String(150), nullable=True)
    prenom_demandeur: Mapped[str | None] = mapped_column(String(150), nullable=True)
    adresse_mail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sigle: Mapped[str | None] = mapped_column(String(100), nullable=True)

    beneficiaire: Mapped[str | None] = mapped_column(String(255), nullable=True)
    groupe_intervenants: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dernier_intervenant: Mapped[str | None] = mapped_column(String(255), nullable=True)

    symptome: Mapped[str | None] = mapped_column(Text, nullable=True)
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class HistoricalTask(TimestampMixin, Base):
    __tablename__ = "historical_tasks"
    __table_args__ = (
        Index("ix_historical_tasks_numero_tache", "numero_tache"),
        Index("ix_historical_tasks_numero_demande", "numero_demande"),
        Index("ix_historical_tasks_statut", "statut_tache"),
        Index("ix_historical_tasks_date_creation", "date_creation_tache"),
    )

    source_key: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    numero_tache: Mapped[str] = mapped_column(String(100), nullable=False)
    numero_demande: Mapped[str | None] = mapped_column(String(100), nullable=True)

    date_creation_tache: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_fin_tache: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    description_tache: Mapped[str | None] = mapped_column(Text, nullable=True)
    statut_tache: Mapped[str | None] = mapped_column(String(100), nullable=True)
    intervenant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    groupe_intervenant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    classification_tache: Mapped[str | None] = mapped_column(String(255), nullable=True)
    motif_rejet: Mapped[str | None] = mapped_column(Text, nullable=True)

    detail_demande: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_demande: Mapped[str | None] = mapped_column(String(255), nullable=True)
    demandeur: Mapped[str | None] = mapped_column(String(255), nullable=True)
    adresse_mail: Mapped[str | None] = mapped_column(String(255), nullable=True)

    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class HistoricalITSupply(TimestampMixin, Base):
    __tablename__ = "historical_it_supplies"
    __table_args__ = (
        Index("ix_historical_it_supplies_numero_demande", "numero_demande"),
        Index("ix_historical_it_supplies_date_initiation", "date_initiation"),
    )

    source_key: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    numero_demande: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_initiation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_traitement: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    etape_en_cours: Mapped[str | None] = mapped_column(String(255), nullable=True)
    initiateur: Mapped[str | None] = mapped_column(String(255), nullable=True)
    login_initiateur: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    motif_demande: Mapped[str | None] = mapped_column(Text, nullable=True)
    nom_recepteur: Mapped[str | None] = mapped_column(String(255), nullable=True)
    matricule_recepteur: Mapped[str | None] = mapped_column(String(100), nullable=True)
    articles: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class HistoricalOfficeSupply(TimestampMixin, Base):
    __tablename__ = "historical_office_supplies"
    __table_args__ = (
        Index("ix_historical_office_supplies_reference", "reference"),
        Index("ix_historical_office_supplies_date_initiation", "date_initiation"),
    )

    source_key: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    reference_consolidee: Mapped[str | None] = mapped_column(String(150), nullable=True)
    date_initiation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_traitement: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expediteur: Mapped[str | None] = mapped_column(String(255), nullable=True)
    etape_en_cours: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    code_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class HistoricalSecurityIncident(TimestampMixin, Base):
    __tablename__ = "historical_security_incidents"
    __table_args__ = (
        Index("ix_historical_security_incidents_numero_fiche", "numero_fiche"),
        Index("ix_historical_security_incidents_statut", "statut"),
    )

    source_key: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    numero_fiche: Mapped[str | None] = mapped_column(String(150), nullable=True)
    statut: Mapped[str | None] = mapped_column(String(100), nullable=True)
    etape_en_cours: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_initiation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_traitement: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_cloture: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nom_initiateur: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sigle_initiateur: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description_incident: Mapped[str | None] = mapped_column(Text, nullable=True)
    cause_incident: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_incident: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_curative: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_corrective: Mapped[str | None] = mapped_column(Text, nullable=True)
    criticite: Mapped[str | None] = mapped_column(String(100), nullable=True)
    groupe_traitement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
