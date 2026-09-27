from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import Priority, Role
from app.db.session import get_db
from app.models.phase3_preventive import (
    GeneratedMaintenanceReport,
    PreventiveMaintenanceExecution,
    PreventiveMaintenancePlan,
)
from app.models.user import User
from app.schemas.common import Message
from app.schemas.phase3_preventive_kpi import (
    EquipmentKpiResponse,
    GeneratedReportRead,
    MaintenanceKpiResponse,
    MonthlyReportResponse,
    PreventiveExecutionCreate,
    PreventiveExecutionRead,
    PreventivePlanCreate,
    PreventivePlanRead,
    PreventivePlanUpdate,
)
from app.services.audit import log_action
from app.services.phase3_preventive_kpi import (
    build_monthly_metrics,
    calculate_equipment_kpis,
    calculate_maintenance_kpis,
    ensure_equipment,
    ensure_technician,
    execute_preventive_plan,
    generate_openrouter_summary,
    get_plan,
    month_bounds,
    period_start_for_months,
    save_generated_report,
)


router = APIRouter(tags=["Phase 3 - Preventif, KPI et Rapports"])


@router.get(
    "/preventive-maintenance/plans",
    response_model=list[PreventivePlanRead],
)
def list_preventive_plans(
    active: bool | None = None,
    equipment_id: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(PreventiveMaintenancePlan).order_by(
        PreventiveMaintenancePlan.next_due_date.asc(),
        PreventiveMaintenancePlan.id.desc(),
    )
    if active is not None:
        stmt = stmt.where(PreventiveMaintenancePlan.active == active)
    if equipment_id is not None:
        stmt = stmt.where(
            PreventiveMaintenancePlan.equipment_id == equipment_id
        )
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post(
    "/preventive-maintenance/plans",
    response_model=PreventivePlanRead,
    status_code=status.HTTP_201_CREATED,
)
def create_preventive_plan(
    payload: PreventivePlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER)
    ),
):
    ensure_equipment(db, payload.equipment_id)
    ensure_technician(db, payload.assigned_technician_id)

    plan = PreventiveMaintenancePlan(
        equipment_id=payload.equipment_id,
        title=payload.title.strip(),
        description=(
            payload.description.strip()
            if payload.description
            else None
        ),
        frequency_days=payload.frequency_days,
        priority=payload.priority.value,
        assigned_technician_id=payload.assigned_technician_id,
        active=True,
        next_due_date=payload.next_due_date,
        created_by_id=current_user.id,
    )
    db.add(plan)
    db.flush()

    log_action(
        db,
        actor_id=current_user.id,
        action="CREATE",
        entity_type="PreventiveMaintenancePlan",
        entity_id=plan.id,
        details={"equipment_id": plan.equipment_id},
    )
    db.commit()
    db.refresh(plan)
    return plan


@router.get(
    "/preventive-maintenance/plans/{plan_id}",
    response_model=PreventivePlanRead,
)
def read_preventive_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return get_plan(db, plan_id)


@router.patch(
    "/preventive-maintenance/plans/{plan_id}",
    response_model=PreventivePlanRead,
)
def update_preventive_plan(
    plan_id: int,
    payload: PreventivePlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER)
    ),
):
    plan = get_plan(db, plan_id, lock=True)
    data = payload.model_dump(exclude_unset=True)

    if "assigned_technician_id" in data:
        ensure_technician(db, data["assigned_technician_id"])
    if "priority" in data and data["priority"] is not None:
        data["priority"] = data["priority"].value

    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(plan, key, value)

    log_action(
        db,
        actor_id=current_user.id,
        action="UPDATE",
        entity_type="PreventiveMaintenancePlan",
        entity_id=plan.id,
        details={"fields": sorted(data.keys())},
    )
    db.commit()
    db.refresh(plan)
    return plan


@router.post(
    "/preventive-maintenance/plans/{plan_id}/activate",
    response_model=PreventivePlanRead,
)
def activate_preventive_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER)
    ),
):
    plan = get_plan(db, plan_id, lock=True)
    plan.active = True
    log_action(
        db,
        actor_id=current_user.id,
        action="ACTIVATE",
        entity_type="PreventiveMaintenancePlan",
        entity_id=plan.id,
    )
    db.commit()
    db.refresh(plan)
    return plan


@router.post(
    "/preventive-maintenance/plans/{plan_id}/deactivate",
    response_model=PreventivePlanRead,
)
def deactivate_preventive_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER)
    ),
):
    plan = get_plan(db, plan_id, lock=True)
    plan.active = False
    log_action(
        db,
        actor_id=current_user.id,
        action="DEACTIVATE",
        entity_type="PreventiveMaintenancePlan",
        entity_id=plan.id,
    )
    db.commit()
    db.refresh(plan)
    return plan


@router.get(
    "/preventive-maintenance/due",
    response_model=list[PreventivePlanRead],
)
def due_preventive_plans(
    days_ahead: int = Query(default=30, ge=0, le=365),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cutoff = date.today().fromordinal(
        date.today().toordinal() + days_ahead
    )
    return db.scalars(
        select(PreventiveMaintenancePlan)
        .where(
            PreventiveMaintenancePlan.active.is_(True),
            PreventiveMaintenancePlan.next_due_date <= cutoff,
        )
        .order_by(PreventiveMaintenancePlan.next_due_date.asc())
        .limit(limit)
    ).all()


@router.post(
    "/preventive-maintenance/plans/{plan_id}/execute",
    response_model=PreventiveExecutionRead,
    status_code=status.HTTP_201_CREATED,
)
def execute_plan_endpoint(
    plan_id: int,
    payload: PreventiveExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)
    ),
):
    plan = get_plan(db, plan_id, lock=True)
    execution = execute_preventive_plan(
        db,
        plan=plan,
        technician_id=payload.technician_id,
        estimated_cost=payload.estimated_cost,
        notes=payload.notes,
        current_user=current_user,
    )
    db.commit()
    db.refresh(execution)
    return execution


@router.get(
    "/preventive-maintenance/executions",
    response_model=list[PreventiveExecutionRead],
)
def list_preventive_executions(
    plan_id: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(PreventiveMaintenanceExecution).order_by(
        PreventiveMaintenanceExecution.id.desc()
    )
    if plan_id is not None:
        stmt = stmt.where(
            PreventiveMaintenanceExecution.plan_id == plan_id
        )
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.get(
    "/kpi/maintenance",
    response_model=MaintenanceKpiResponse,
)
def maintenance_kpis(
    months: int = Query(default=12, ge=1, le=120),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return calculate_maintenance_kpis(
        db,
        period_start=period_start_for_months(months),
        period_end=date.today(),
    )


@router.get(
    "/kpi/equipments/{equipment_id}",
    response_model=EquipmentKpiResponse,
)
def equipment_kpis(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return calculate_equipment_kpis(db, equipment_id)


@router.get(
    "/reports/monthly",
    response_model=MonthlyReportResponse,
)
def monthly_report(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    metrics = build_monthly_metrics(db, year=year, month=month)
    from app.services.phase3_preventive_kpi import (
        deterministic_monthly_summary,
    )

    return MonthlyReportResponse(
        metrics=metrics,
        summary=deterministic_monthly_summary(metrics),
        llm_used=False,
        model_name=None,
    )


@router.post(
    "/reports/monthly/generate",
    response_model=MonthlyReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_monthly_report(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER)
    ),
):
    metrics = build_monthly_metrics(db, year=year, month=month)
    summary, llm_used, model_name = generate_openrouter_summary(metrics)

    save_generated_report(
        db,
        metrics=metrics,
        summary=summary,
        llm_used=llm_used,
        model_name=model_name,
        current_user=current_user,
    )
    db.commit()

    return MonthlyReportResponse(
        metrics=metrics,
        summary=summary,
        llm_used=llm_used,
        model_name=model_name,
    )


@router.get(
    "/reports",
    response_model=list[GeneratedReportRead],
)
def list_generated_reports(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.scalars(
        select(GeneratedMaintenanceReport)
        .order_by(GeneratedMaintenanceReport.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
