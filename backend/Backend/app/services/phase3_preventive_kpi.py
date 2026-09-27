from __future__ import annotations

import calendar
import json
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import (
    EquipmentStatus,
    InterventionStatus,
    MaintenanceType,
    RequestStatus,
    Role,
)
from app.models.equipment import Equipment
from app.models.maintenance import (
    Intervention,
    InterventionStatusHistory,
    MaintenanceRequest,
)
from app.models.phase3_preventive import (
    GeneratedMaintenanceReport,
    PreventiveMaintenanceExecution,
    PreventiveMaintenancePlan,
)
from app.models.stock import SparePart
from app.models.user import User
from app.schemas.phase3_preventive_kpi import (
    EquipmentKpiResponse,
    MaintenanceKpiResponse,
    MonthlyReportMetrics,
)
from app.services.audit import create_notification, log_action
from app.services.references import generate_reference


logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def month_bounds(year: int, month: int) -> tuple[date, date]:
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="Annee invalide")
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="Mois invalide")

    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    return start, end


def date_to_start_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def date_to_end_exclusive(value: date) -> datetime:
    return datetime.combine(
        value + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )


def period_start_for_months(months: int) -> date:
    today = date.today()
    total_month = today.year * 12 + today.month - 1 - (months - 1)
    year = total_month // 12
    month = total_month % 12 + 1
    return date(year, month, 1)


def ensure_equipment(db: Session, equipment_id: int) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None or equipment.archived:
        raise HTTPException(status_code=404, detail="Equipement introuvable")
    return equipment


def ensure_technician(db: Session, technician_id: int | None) -> User | None:
    if technician_id is None:
        return None

    technician = db.get(User, technician_id)
    if technician is None or technician.role != Role.TECHNICIAN.value:
        raise HTTPException(status_code=400, detail="Technicien invalide")
    if technician.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Technicien inactif")
    return technician


def get_plan(db: Session, plan_id: int, *, lock: bool = False) -> PreventiveMaintenancePlan:
    stmt = select(PreventiveMaintenancePlan).where(
        PreventiveMaintenancePlan.id == plan_id
    )
    if lock:
        stmt = stmt.with_for_update()

    plan = db.scalar(stmt)
    if plan is None:
        raise HTTPException(
            status_code=404,
            detail="Plan de maintenance preventive introuvable",
        )
    return plan


def calculate_mttr(interventions: list[Intervention]) -> float | None:
    durations: list[float] = []

    for item in interventions:
        if item.started_at is None or item.ended_at is None:
            continue
        duration = (item.ended_at - item.started_at).total_seconds() / 3600
        if duration >= 0:
            durations.append(duration)

    if not durations:
        return None
    return round(sum(durations) / len(durations), 2)


def calculate_mtbf(interventions: list[Intervention]) -> float | None:
    by_equipment: dict[int, list[datetime]] = defaultdict(list)

    for item in interventions:
        if (
            item.maintenance_type == MaintenanceType.CORRECTIVE.value
            and item.ended_at is not None
        ):
            by_equipment[item.equipment_id].append(item.ended_at)

    gaps: list[float] = []

    for ended_values in by_equipment.values():
        values = sorted(ended_values)
        for previous, current in zip(values, values[1:]):
            gap = (current - previous).total_seconds() / 3600
            if gap >= 0:
                gaps.append(gap)

    if not gaps:
        return None
    return round(sum(gaps) / len(gaps), 2)


def calculate_maintenance_kpis(
    db: Session,
    *,
    period_start: date,
    period_end: date,
) -> MaintenanceKpiResponse:
    start_dt = date_to_start_datetime(period_start)
    end_dt = date_to_end_exclusive(period_end)

    interventions = db.scalars(
        select(Intervention).where(
            Intervention.created_at >= start_dt,
            Intervention.created_at < end_dt,
        )
    ).all()

    completed = [
        item
        for item in interventions
        if item.status == InterventionStatus.COMPLETED.value
    ]
    corrective = [
        item
        for item in interventions
        if item.maintenance_type == MaintenanceType.CORRECTIVE.value
    ]
    preventive = [
        item
        for item in interventions
        if item.maintenance_type == MaintenanceType.PREVENTIVE.value
    ]

    mttr = calculate_mttr(completed)
    mtbf = calculate_mtbf(completed)

    availability = None
    if mttr is not None and mtbf is not None and mttr + mtbf > 0:
        availability = round(mtbf / (mtbf + mttr) * 100, 2)

    total_cost = round(
        float(sum(Decimal(item.actual_cost or 0) for item in completed)),
        2,
    )

    active_plans = int(
        db.scalar(
            select(func.count())
            .select_from(PreventiveMaintenancePlan)
            .where(PreventiveMaintenancePlan.active.is_(True))
        )
        or 0
    )
    due_plans = int(
        db.scalar(
            select(func.count())
            .select_from(PreventiveMaintenancePlan)
            .where(
                PreventiveMaintenancePlan.active.is_(True),
                PreventiveMaintenancePlan.next_due_date <= period_end,
            )
        )
        or 0
    )
    overdue_plans = int(
        db.scalar(
            select(func.count())
            .select_from(PreventiveMaintenancePlan)
            .where(
                PreventiveMaintenancePlan.active.is_(True),
                PreventiveMaintenancePlan.next_due_date < date.today(),
            )
        )
        or 0
    )

    preventive_ratio = (
        round(len(preventive) / len(interventions) * 100, 2)
        if interventions
        else 0.0
    )

    return MaintenanceKpiResponse(
        period_start=period_start,
        period_end=period_end,
        total_interventions=len(interventions),
        completed_interventions=len(completed),
        corrective_interventions=len(corrective),
        preventive_interventions=len(preventive),
        preventive_ratio_percent=preventive_ratio,
        mttr_hours=mttr,
        mtbf_hours=mtbf,
        estimated_availability_percent=availability,
        total_actual_cost=total_cost,
        active_preventive_plans=active_plans,
        due_preventive_plans=due_plans,
        overdue_preventive_plans=overdue_plans,
    )


def calculate_equipment_kpis(
    db: Session,
    equipment_id: int,
) -> EquipmentKpiResponse:
    equipment = ensure_equipment(db, equipment_id)

    interventions = db.scalars(
        select(Intervention)
        .where(Intervention.equipment_id == equipment_id)
        .order_by(Intervention.created_at.asc())
    ).all()

    completed = [
        item
        for item in interventions
        if item.status == InterventionStatus.COMPLETED.value
    ]
    corrective = [
        item
        for item in interventions
        if item.maintenance_type == MaintenanceType.CORRECTIVE.value
    ]
    preventive = [
        item
        for item in interventions
        if item.maintenance_type == MaintenanceType.PREVENTIVE.value
    ]

    last_intervention = max(
        (
            item.ended_at or item.started_at or item.created_at
            for item in interventions
        ),
        default=None,
    )

    active_plans = db.scalars(
        select(PreventiveMaintenancePlan).where(
            PreventiveMaintenancePlan.equipment_id == equipment_id,
            PreventiveMaintenancePlan.active.is_(True),
        )
    ).all()

    next_due = min(
        (item.next_due_date for item in active_plans),
        default=None,
    )

    total_cost = round(
        float(sum(Decimal(item.actual_cost or 0) for item in completed)),
        2,
    )

    return EquipmentKpiResponse(
        equipment_id=equipment.id,
        equipment_code=equipment.code,
        total_interventions=len(interventions),
        completed_interventions=len(completed),
        corrective_interventions=len(corrective),
        preventive_interventions=len(preventive),
        mttr_hours=calculate_mttr(completed),
        mtbf_hours=calculate_mtbf(completed),
        total_actual_cost=total_cost,
        last_intervention_at=last_intervention,
        next_preventive_due_date=next_due,
        active_preventive_plans=len(active_plans),
    )


def execute_preventive_plan(
    db: Session,
    *,
    plan: PreventiveMaintenancePlan,
    technician_id: int | None,
    estimated_cost: float,
    notes: str | None,
    current_user: User,
) -> PreventiveMaintenanceExecution:
    if not plan.active:
        raise HTTPException(status_code=409, detail="Le plan est inactif")

    equipment = ensure_equipment(db, plan.equipment_id)

    if current_user.role == Role.TECHNICIAN.value:
        if (
            plan.assigned_technician_id is not None
            and plan.assigned_technician_id != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="Ce plan ne vous est pas affecte",
            )
        effective_technician_id = current_user.id
    else:
        effective_technician_id = technician_id or plan.assigned_technician_id

    technician = ensure_technician(db, effective_technician_id)
    if technician is None:
        raise HTTPException(
            status_code=422,
            detail="technician_id est obligatoire pour executer le plan",
        )

    active_execution = db.scalar(
        select(PreventiveMaintenanceExecution)
        .join(
            Intervention,
            Intervention.id
            == PreventiveMaintenanceExecution.intervention_id,
        )
        .where(
            PreventiveMaintenanceExecution.plan_id == plan.id,
            Intervention.status.not_in(
                [
                    InterventionStatus.COMPLETED.value,
                    InterventionStatus.CANCELLED.value,
                ]
            ),
        )
    )
    if active_execution is not None:
        raise HTTPException(
            status_code=409,
            detail="Une intervention preventive est deja ouverte pour ce plan",
        )

    intervention = Intervention(
        reference=generate_reference("INT"),
        request_id=None,
        equipment_id=equipment.id,
        technician_id=technician.id,
        maintenance_type=MaintenanceType.PREVENTIVE.value,
        estimated_cost=Decimal(str(estimated_cost)),
        actual_cost=Decimal("0"),
        status=InterventionStatus.PLANNED.value,
    )
    db.add(intervention)
    db.flush()

    db.add(
        InterventionStatusHistory(
            intervention_id=intervention.id,
            old_status=None,
            new_status=InterventionStatus.PLANNED.value,
            changed_by_id=current_user.id,
            comment=f"Intervention generee depuis le plan preventif {plan.id}",
        )
    )

    execution = PreventiveMaintenanceExecution(
        plan_id=plan.id,
        intervention_id=intervention.id,
        scheduled_date=plan.next_due_date,
        status="INTERVENTION_CREATED",
        notes=notes,
        triggered_by_id=current_user.id,
    )
    db.add(execution)

    now = utc_now()
    plan.last_executed_at = now
    plan.next_due_date = max(
        date.today(),
        plan.next_due_date,
    ) + timedelta(days=plan.frequency_days)

    equipment.status = EquipmentStatus.IN_MAINTENANCE.value

    create_notification(
        db,
        user_id=technician.id,
        title="Maintenance preventive planifiee",
        message=(
            f"Une intervention preventive {intervention.reference} "
            f"vous a ete affectee pour l'equipement {equipment.code}."
        ),
    )
    log_action(
        db,
        actor_id=current_user.id,
        action="EXECUTE_PREVENTIVE_PLAN",
        entity_type="PreventiveMaintenancePlan",
        entity_id=plan.id,
        details={
            "intervention_id": intervention.id,
            "equipment_id": equipment.id,
            "technician_id": technician.id,
            "next_due_date": plan.next_due_date.isoformat(),
        },
    )
    return execution


def build_monthly_metrics(
    db: Session,
    *,
    year: int,
    month: int,
) -> MonthlyReportMetrics:
    period_start, period_end = month_bounds(year, month)
    start_dt = date_to_start_datetime(period_start)
    end_dt = date_to_end_exclusive(period_end)

    submitted_requests = int(
        db.scalar(
            select(func.count())
            .select_from(MaintenanceRequest)
            .where(
                MaintenanceRequest.submitted_at >= start_dt,
                MaintenanceRequest.submitted_at < end_dt,
            )
        )
        or 0
    )
    resolved_requests = int(
        db.scalar(
            select(func.count())
            .select_from(MaintenanceRequest)
            .where(
                MaintenanceRequest.closed_at >= start_dt,
                MaintenanceRequest.closed_at < end_dt,
                MaintenanceRequest.status.in_(
                    [
                        RequestStatus.RESOLVED.value,
                        RequestStatus.CLOSED.value,
                    ]
                ),
            )
        )
        or 0
    )

    interventions = db.scalars(
        select(Intervention).where(
            Intervention.created_at >= start_dt,
            Intervention.created_at < end_dt,
        )
    ).all()
    completed = [
        item
        for item in interventions
        if item.status == InterventionStatus.COMPLETED.value
    ]

    equipment_failures = int(
        db.scalar(
            select(func.count())
            .select_from(Equipment)
            .where(
                Equipment.archived.is_(False),
                Equipment.status.in_(
                    [
                        EquipmentStatus.IN_FAILURE.value,
                        EquipmentStatus.OUT_OF_SERVICE.value,
                    ]
                ),
            )
        )
        or 0
    )
    low_stock = int(
        db.scalar(
            select(func.count())
            .select_from(SparePart)
            .where(
                SparePart.active.is_(True),
                SparePart.quantity <= SparePart.minimum_threshold,
            )
        )
        or 0
    )
    due_plans = int(
        db.scalar(
            select(func.count())
            .select_from(PreventiveMaintenancePlan)
            .where(
                PreventiveMaintenancePlan.active.is_(True),
                PreventiveMaintenancePlan.next_due_date <= period_end,
            )
        )
        or 0
    )
    overdue_plans = int(
        db.scalar(
            select(func.count())
            .select_from(PreventiveMaintenancePlan)
            .where(
                PreventiveMaintenancePlan.active.is_(True),
                PreventiveMaintenancePlan.next_due_date < date.today(),
            )
        )
        or 0
    )

    return MonthlyReportMetrics(
        year=year,
        month=month,
        period_start=period_start,
        period_end=period_end,
        submitted_requests=submitted_requests,
        resolved_requests=resolved_requests,
        created_interventions=len(interventions),
        completed_interventions=len(completed),
        corrective_interventions=sum(
            1
            for item in interventions
            if item.maintenance_type == MaintenanceType.CORRECTIVE.value
        ),
        preventive_interventions=sum(
            1
            for item in interventions
            if item.maintenance_type == MaintenanceType.PREVENTIVE.value
        ),
        mttr_hours=calculate_mttr(completed),
        total_actual_cost=round(
            float(sum(Decimal(item.actual_cost or 0) for item in completed)),
            2,
        ),
        current_equipment_failures=equipment_failures,
        current_low_stock_parts=low_stock,
        due_preventive_plans=due_plans,
        overdue_preventive_plans=overdue_plans,
    )


def deterministic_monthly_summary(metrics: MonthlyReportMetrics) -> str:
    mttr_text = (
        f"{metrics.mttr_hours:.2f} heures"
        if metrics.mttr_hours is not None
        else "non calculable faute de donnees completes"
    )
    return (
        f"Rapport de maintenance pour {metrics.month:02d}/{metrics.year}. "
        f"{metrics.submitted_requests} demandes ont ete soumises et "
        f"{metrics.resolved_requests} demandes ont ete resolues ou cloturees. "
        f"{metrics.created_interventions} interventions ont ete creees, dont "
        f"{metrics.preventive_interventions} preventives et "
        f"{metrics.corrective_interventions} correctives. "
        f"Le MTTR est {mttr_text}. "
        f"Le cout reel cumule des interventions terminees est de "
        f"{metrics.total_actual_cost:.2f} MAD. "
        f"Le parc compte actuellement {metrics.current_equipment_failures} "
        f"equipements en panne ou hors service et "
        f"{metrics.current_low_stock_parts} pieces sous le seuil minimal. "
        f"{metrics.overdue_preventive_plans} plans preventifs sont en retard."
    )


def generate_openrouter_summary(
    metrics: MonthlyReportMetrics,
) -> tuple[str, bool, str | None]:
    fallback = deterministic_monthly_summary(metrics)
    api_key = getattr(settings, "OPENROUTER_API_KEY", "")
    model_name = getattr(settings, "OPENROUTER_MODEL", "")
    base_url = getattr(
        settings,
        "OPENROUTER_BASE_URL",
        "https://openrouter.ai/api/v1",
    ).rstrip("/")

    if not api_key or not model_name:
        return fallback, False, None

    exact_data = metrics.model_dump(mode="json")
    prompt = (
        "Redige une synthese professionnelle en francais pour le responsable "
        "de l'atelier de maintenance ONEE. Utilise exclusivement les valeurs "
        "JSON fournies. N'invente aucun nombre, cout, date, pourcentage ou "
        "cause. Mentionne les points positifs, les alertes et trois actions "
        "prioritaires. Maximum 250 mots.\n\nDONNEES EXACTES:\n"
        + json.dumps(exact_data, ensure_ascii=False, indent=2)
    )

    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://127.0.0.1:8000",
                    "X-Title": "MaintIA ONEE",
                },
                json={
                    "model": model_name,
                    "temperature": 0.1,
                    "max_tokens": 700,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Tu es un assistant de reporting de maintenance. "
                                "Tous les chiffres doivent provenir du JSON."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                },
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            content = (
                payload.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if isinstance(content, str) and content.strip():
                return content.strip(), True, model_name
    except Exception as error:
        logger.exception(
            "Echec OpenRouter pour le rapport mensuel, fallback utilise: %s",
            error,
        )

    return fallback, False, model_name


def save_generated_report(
    db: Session,
    *,
    metrics: MonthlyReportMetrics,
    summary: str,
    llm_used: bool,
    model_name: str | None,
    current_user: User,
) -> GeneratedMaintenanceReport:
    report = GeneratedMaintenanceReport(
        report_type="MONTHLY",
        period_start=metrics.period_start,
        period_end=metrics.period_end,
        metrics=metrics.model_dump(mode="json"),
        summary=summary,
        llm_used=llm_used,
        model_name=model_name,
        generated_by_id=current_user.id,
    )
    db.add(report)
    db.flush()

    log_action(
        db,
        actor_id=current_user.id,
        action="GENERATE_MONTHLY_REPORT",
        entity_type="GeneratedMaintenanceReport",
        entity_id=report.id,
        details={
            "period_start": metrics.period_start.isoformat(),
            "period_end": metrics.period_end.isoformat(),
            "llm_used": llm_used,
            "model_name": model_name,
        },
    )
    return report
