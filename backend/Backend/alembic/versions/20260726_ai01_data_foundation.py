"""Ajoute la fondation des données IA.

Revision ID: 20260726_ai01
Revises:
Create Date: 2026-07-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260726_ai01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "equipment_historical_links",
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("historical_request_id", sa.Integer(), nullable=False),
        sa.Column("link_method", sa.String(length=80), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("validation_status", sa.String(length=30), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("validated_by_id", sa.Integer(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["historical_request_id"],
            ["historical_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["validated_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "equipment_id",
            "historical_request_id",
            name="uq_equipment_historical_link",
        ),
    )
    op.create_index(
        "ix_equipment_historical_links_id",
        "equipment_historical_links",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_equipment_historical_links_equipment",
        "equipment_historical_links",
        ["equipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_equipment_historical_links_request",
        "equipment_historical_links",
        ["historical_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_equipment_historical_links_validation",
        "equipment_historical_links",
        ["validation_status"],
        unique=False,
    )

    op.create_table(
        "rag_sync_queue",
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("operation", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rag_sync_queue_id",
        "rag_sync_queue",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_sync_queue_status_created",
        "rag_sync_queue",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_sync_queue_source",
        "rag_sync_queue",
        ["source_type", "source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rag_sync_queue_source",
        table_name="rag_sync_queue",
    )
    op.drop_index(
        "ix_rag_sync_queue_status_created",
        table_name="rag_sync_queue",
    )
    op.drop_index(
        "ix_rag_sync_queue_id",
        table_name="rag_sync_queue",
    )
    op.drop_table("rag_sync_queue")

    op.drop_index(
        "ix_equipment_historical_links_validation",
        table_name="equipment_historical_links",
    )
    op.drop_index(
        "ix_equipment_historical_links_request",
        table_name="equipment_historical_links",
    )
    op.drop_index(
        "ix_equipment_historical_links_equipment",
        table_name="equipment_historical_links",
    )
    op.drop_index(
        "ix_equipment_historical_links_id",
        table_name="equipment_historical_links",
    )
    op.drop_table("equipment_historical_links")
