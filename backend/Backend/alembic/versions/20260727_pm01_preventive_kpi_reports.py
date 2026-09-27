"""Ajoute la maintenance preventive, les KPI et les rapports.

Revision ID: 20260727_pm01
Revises: 20260726_ai01
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_pm01"
down_revision = "20260726_ai01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preventive_maintenance_plans",
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("frequency_days", sa.Integer(), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=30),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column("assigned_technician_id", sa.Integer(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column(
            "last_executed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
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
            ["assigned_technician_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_preventive_maintenance_plans_id",
        "preventive_maintenance_plans",
        ["id"],
    )
    op.create_index(
        "ix_preventive_maintenance_plans_equipment_id",
        "preventive_maintenance_plans",
        ["equipment_id"],
    )
    op.create_index(
        "ix_preventive_maintenance_plans_assigned_technician_id",
        "preventive_maintenance_plans",
        ["assigned_technician_id"],
    )
    op.create_index(
        "ix_preventive_maintenance_plans_next_due_date",
        "preventive_maintenance_plans",
        ["next_due_date"],
    )

    op.create_table(
        "preventive_maintenance_executions",
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("intervention_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "status",
            sa.String(length=40),
            nullable=False,
            server_default="INTERVENTION_CREATED",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("triggered_by_id", sa.Integer(), nullable=False),
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
            ["intervention_id"],
            ["interventions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["preventive_maintenance_plans.id"],
        ),
        sa.ForeignKeyConstraint(["triggered_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intervention_id"),
    )
    op.create_index(
        "ix_preventive_maintenance_executions_id",
        "preventive_maintenance_executions",
        ["id"],
    )
    op.create_index(
        "ix_preventive_maintenance_executions_plan_id",
        "preventive_maintenance_executions",
        ["plan_id"],
    )
    op.create_index(
        "ix_preventive_maintenance_executions_intervention_id",
        "preventive_maintenance_executions",
        ["intervention_id"],
    )

    op.create_table(
        "generated_maintenance_reports",
        sa.Column(
            "report_type",
            sa.String(length=50),
            nullable=False,
            server_default="MONTHLY",
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "llm_used",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("generated_by_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["generated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generated_maintenance_reports_id",
        "generated_maintenance_reports",
        ["id"],
    )
    op.create_index(
        "ix_generated_maintenance_reports_period_start",
        "generated_maintenance_reports",
        ["period_start"],
    )
    op.create_index(
        "ix_generated_maintenance_reports_period_end",
        "generated_maintenance_reports",
        ["period_end"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generated_maintenance_reports_period_end",
        table_name="generated_maintenance_reports",
    )
    op.drop_index(
        "ix_generated_maintenance_reports_period_start",
        table_name="generated_maintenance_reports",
    )
    op.drop_index(
        "ix_generated_maintenance_reports_id",
        table_name="generated_maintenance_reports",
    )
    op.drop_table("generated_maintenance_reports")

    op.drop_index(
        "ix_preventive_maintenance_executions_intervention_id",
        table_name="preventive_maintenance_executions",
    )
    op.drop_index(
        "ix_preventive_maintenance_executions_plan_id",
        table_name="preventive_maintenance_executions",
    )
    op.drop_index(
        "ix_preventive_maintenance_executions_id",
        table_name="preventive_maintenance_executions",
    )
    op.drop_table("preventive_maintenance_executions")

    op.drop_index(
        "ix_preventive_maintenance_plans_next_due_date",
        table_name="preventive_maintenance_plans",
    )
    op.drop_index(
        "ix_preventive_maintenance_plans_assigned_technician_id",
        table_name="preventive_maintenance_plans",
    )
    op.drop_index(
        "ix_preventive_maintenance_plans_equipment_id",
        table_name="preventive_maintenance_plans",
    )
    op.drop_index(
        "ix_preventive_maintenance_plans_id",
        table_name="preventive_maintenance_plans",
    )
    op.drop_table("preventive_maintenance_plans")
