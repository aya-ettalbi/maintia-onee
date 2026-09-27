"""Ajoute la prevision IA des futures pannes.

Revision ID: 20260728_ai02
Revises: 20260727_pm01
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_ai02"
down_revision = "20260727_pm01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "failure_forecast_runs",
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="RUNNING",
        ),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column(
            "only_with_history",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("requested_limit", sa.Integer(), nullable=False),
        sa.Column(
            "processed_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "high_risk_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "medium_risk_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "low_risk_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "notifications_created",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "recommendations_created",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "error_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "error_details",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("triggered_by_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_failure_forecast_runs_id",
        "failure_forecast_runs",
        ["id"],
    )
    op.create_index(
        "ix_failure_forecast_runs_started_at",
        "failure_forecast_runs",
        ["started_at"],
    )
    op.create_index(
        "ix_failure_forecast_runs_status",
        "failure_forecast_runs",
        ["status"],
    )

    op.create_table(
        "failure_forecasts",
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column(
            "forecasted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("failure_probability", sa.Float(), nullable=False),
        sa.Column(
            "probability_calibrated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("risk_level", sa.String(length=30), nullable=False),
        sa.Column(
            "evidence_confidence",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "predicted_failure_family",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("estimated_start_date", sa.Date(), nullable=True),
        sa.Column("estimated_end_date", sa.Date(), nullable=True),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column("recommended_actions", sa.JSON(), nullable=False),
        sa.Column("evidence_summary", sa.JSON(), nullable=False),
        sa.Column("similar_references", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "methodology_version",
            sa.String(length=80),
            nullable=False,
            server_default="HEURISTIC_HISTORY_V1",
        ),
        sa.Column(
            "llm_used",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("recommendation_id", sa.Integer(), nullable=True),
        sa.Column(
            "notification_created",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "validation_status",
            sa.String(length=30),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("validated_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "validated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.Column(
            "actual_failure_occurred",
            sa.Boolean(),
            nullable=True,
        ),
        sa.Column("actual_failure_date", sa.Date(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["validated_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_failure_forecasts_id",
        "failure_forecasts",
        ["id"],
    )
    op.create_index(
        "ix_failure_forecasts_equipment_date",
        "failure_forecasts",
        ["equipment_id", "forecasted_at"],
    )
    op.create_index(
        "ix_failure_forecasts_risk_level",
        "failure_forecasts",
        ["risk_level"],
    )
    op.create_index(
        "ix_failure_forecasts_validation_status",
        "failure_forecasts",
        ["validation_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_failure_forecasts_validation_status",
        table_name="failure_forecasts",
    )
    op.drop_index(
        "ix_failure_forecasts_risk_level",
        table_name="failure_forecasts",
    )
    op.drop_index(
        "ix_failure_forecasts_equipment_date",
        table_name="failure_forecasts",
    )
    op.drop_index(
        "ix_failure_forecasts_id",
        table_name="failure_forecasts",
    )
    op.drop_table("failure_forecasts")

    op.drop_index(
        "ix_failure_forecast_runs_status",
        table_name="failure_forecast_runs",
    )
    op.drop_index(
        "ix_failure_forecast_runs_started_at",
        table_name="failure_forecast_runs",
    )
    op.drop_index(
        "ix_failure_forecast_runs_id",
        table_name="failure_forecast_runs",
    )
    op.drop_table("failure_forecast_runs")
