from __future__ import annotations

import re
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.historical import (
    HistoricalITSupply,
    HistoricalOfficeSupply,
    HistoricalRequest,
    HistoricalSecurityIncident,
    HistoricalTask,
)
from app.models.maintenance import Intervention, MaintenanceRequest
from app.models.user import User
from app.schemas.historical import (
    HistoricalAnalytics,
    HistoricalCountItem,
    HistoricalDiagnosticRequest,
    HistoricalDiagnosticSuggestion,
    HistoricalMonthlyItem,
    HistoricalSummary,
    ITSupplyPage,
    OfficeSupplyPage,
    RequestPage,
    SecurityIncidentPage,
    TaskPage,
)


router = APIRouter(prefix="/historical", tags=["Historique ONEE"])


def count_for(db: Session, model, *filters) -> int:
    stmt = select(func.count()).select_from(model)
    if filters:
        stmt = stmt.where(*filters)
    return db.scalar(stmt) or 0


def grouped_counts(db: Session, column, limit: int = 12) -> list[HistoricalCountItem]:
    rows = db.execute(
        select(column, func.count())
        .where(column.is_not(None), func.trim(column) != "")
        .group_by(column)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    return [
        HistoricalCountItem(name=str(name), value=int(value))
        for name, value in rows
    ]


@router.get("/summary", response_model=HistoricalSummary)
def summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    requests_count = count_for(db, HistoricalRequest)
    tasks_count = count_for(db, HistoricalTask)
    it_count = count_for(db, HistoricalITSupply)
    office_count = count_for(db, HistoricalOfficeSupply)
    security_count = count_for(db, HistoricalSecurityIncident)

    operational_requests_count = count_for(db, MaintenanceRequest)
    operational_interventions_count = count_for(db, Intervention)

    return HistoricalSummary(
        requests_count=requests_count,
        tasks_count=tasks_count,
        it_supplies_count=it_count,
        office_supplies_count=office_count,
        security_incidents_count=security_count,
        total_historical_rows=(
            requests_count + tasks_count + it_count + office_count + security_count
        ),
        operational_requests_count=operational_requests_count,
        combined_requests_count=requests_count + operational_requests_count,
        operational_interventions_count=operational_interventions_count,
        combined_interventions_count=tasks_count + operational_interventions_count,
    )


@router.get("/requests", response_model=RequestPage)
def list_requests(
    q: str | None = None,
    request_status: str | None = None,
    classification: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    filters = []

    if q:
        like = f"%{q.strip()}%"
        filters.append(
            or_(
                HistoricalRequest.numero_demande.ilike(like),
                HistoricalRequest.description_demande.ilike(like),
                HistoricalRequest.classification.ilike(like),
                HistoricalRequest.detail_classification.ilike(like),
                HistoricalRequest.demandeur.ilike(like),
                HistoricalRequest.nom_demandeur.ilike(like),
                HistoricalRequest.prenom_demandeur.ilike(like),
                HistoricalRequest.adresse_mail.ilike(like),
                HistoricalRequest.dernier_intervenant.ilike(like),
                HistoricalRequest.symptome.ilike(like),
                HistoricalRequest.cause.ilike(like),
                HistoricalRequest.solution.ilike(like),
            )
        )

    if request_status:
        filters.append(HistoricalRequest.statut == request_status)

    if classification:
        filters.append(HistoricalRequest.classification == classification)

    stmt = select(HistoricalRequest)
    if filters:
        stmt = stmt.where(*filters)

    total = count_for(db, HistoricalRequest, *filters)
    items = db.scalars(
        stmt.order_by(HistoricalRequest.id.desc()).offset(skip).limit(limit)
    ).all()

    return RequestPage(total=total, skip=skip, limit=limit, items=items)


@router.get("/tasks", response_model=TaskPage)
def list_tasks(
    q: str | None = None,
    task_status: str | None = None,
    numero_demande: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    filters = []

    if q:
        like = f"%{q.strip()}%"
        filters.append(
            or_(
                HistoricalTask.numero_tache.ilike(like),
                HistoricalTask.numero_demande.ilike(like),
                HistoricalTask.description_tache.ilike(like),
                HistoricalTask.intervenant.ilike(like),
                HistoricalTask.groupe_intervenant.ilike(like),
                HistoricalTask.classification_tache.ilike(like),
                HistoricalTask.detail_demande.ilike(like),
                HistoricalTask.demandeur.ilike(like),
            )
        )

    if task_status:
        filters.append(HistoricalTask.statut_tache == task_status)

    if numero_demande:
        filters.append(HistoricalTask.numero_demande == numero_demande)

    stmt = select(HistoricalTask)
    if filters:
        stmt = stmt.where(*filters)

    total = count_for(db, HistoricalTask, *filters)
    items = db.scalars(
        stmt.order_by(HistoricalTask.id.desc()).offset(skip).limit(limit)
    ).all()

    return TaskPage(total=total, skip=skip, limit=limit, items=items)


@router.get("/it-supplies", response_model=ITSupplyPage)
def list_it_supplies(
    q: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    filters = []
    if q:
        like = f"%{q.strip()}%"
        filters.append(
            or_(
                HistoricalITSupply.numero_demande.ilike(like),
                HistoricalITSupply.initiateur.ilike(like),
                HistoricalITSupply.nom_recepteur.ilike(like),
                HistoricalITSupply.motif_demande.ilike(like),
                HistoricalITSupply.articles.ilike(like),
            )
        )

    stmt = select(HistoricalITSupply)
    if filters:
        stmt = stmt.where(*filters)

    total = count_for(db, HistoricalITSupply, *filters)
    items = db.scalars(
        stmt.order_by(HistoricalITSupply.id.desc()).offset(skip).limit(limit)
    ).all()

    return ITSupplyPage(total=total, skip=skip, limit=limit, items=items)


@router.get("/office-supplies", response_model=OfficeSupplyPage)
def list_office_supplies(
    q: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    filters = []
    if q:
        like = f"%{q.strip()}%"
        filters.append(
            or_(
                HistoricalOfficeSupply.reference.ilike(like),
                HistoricalOfficeSupply.reference_consolidee.ilike(like),
                HistoricalOfficeSupply.expediteur.ilike(like),
                HistoricalOfficeSupply.direction.ilike(like),
            )
        )

    stmt = select(HistoricalOfficeSupply)
    if filters:
        stmt = stmt.where(*filters)

    total = count_for(db, HistoricalOfficeSupply, *filters)
    items = db.scalars(
        stmt.order_by(HistoricalOfficeSupply.id.desc()).offset(skip).limit(limit)
    ).all()

    return OfficeSupplyPage(total=total, skip=skip, limit=limit, items=items)


@router.get("/security-incidents", response_model=SecurityIncidentPage)
def list_security_incidents(
    q: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    filters = []
    if q:
        like = f"%{q.strip()}%"
        filters.append(
            or_(
                HistoricalSecurityIncident.numero_fiche.ilike(like),
                HistoricalSecurityIncident.description_incident.ilike(like),
                HistoricalSecurityIncident.cause_incident.ilike(like),
                HistoricalSecurityIncident.impact_incident.ilike(like),
                HistoricalSecurityIncident.action_curative.ilike(like),
                HistoricalSecurityIncident.action_corrective.ilike(like),
            )
        )

    stmt = select(HistoricalSecurityIncident)
    if filters:
        stmt = stmt.where(*filters)

    total = count_for(db, HistoricalSecurityIncident, *filters)
    items = db.scalars(
        stmt.order_by(HistoricalSecurityIncident.id.desc()).offset(skip).limit(limit)
    ).all()

    return SecurityIncidentPage(total=total, skip=skip, limit=limit, items=items)


@router.get("/analytics", response_model=HistoricalAnalytics)
def analytics(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    month_expression = func.to_char(
        func.date_trunc("month", HistoricalRequest.date_creation_demande),
        "YYYY-MM",
    )

    monthly_rows = db.execute(
        select(month_expression, func.count())
        .where(HistoricalRequest.date_creation_demande.is_not(None))
        .group_by(month_expression)
        .order_by(month_expression.asc())
    ).all()

    average_resolution_hours = db.scalar(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    HistoricalRequest.date_resolution_demande
                    - HistoricalRequest.date_creation_demande,
                )
                / 3600.0
            )
        ).where(
            HistoricalRequest.date_creation_demande.is_not(None),
            HistoricalRequest.date_resolution_demande.is_not(None),
            HistoricalRequest.date_resolution_demande
            >= HistoricalRequest.date_creation_demande,
        )
    )

    return HistoricalAnalytics(
        request_statuses=grouped_counts(db, HistoricalRequest.statut),
        request_classifications=grouped_counts(
            db, HistoricalRequest.classification
        ),
        task_statuses=grouped_counts(db, HistoricalTask.statut_tache),
        top_technicians=grouped_counts(db, HistoricalTask.intervenant),
        monthly_requests=[
            HistoricalMonthlyItem(month=str(month), value=int(value))
            for month, value in monthly_rows
            if month
        ],
        requests_with_cause=count_for(
            db,
            HistoricalRequest,
            HistoricalRequest.cause.is_not(None),
            func.trim(HistoricalRequest.cause) != "",
        ),
        requests_with_solution=count_for(
            db,
            HistoricalRequest,
            HistoricalRequest.solution.is_not(None),
            func.trim(HistoricalRequest.solution) != "",
        ),
        average_resolution_hours=(
            round(float(average_resolution_hours), 2)
            if average_resolution_hours is not None
            else None
        ),
    )


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().split())


def candidate_score(query: str, item: HistoricalRequest) -> float:
    fields = [
        item.description_demande,
        item.symptome,
        item.cause,
        item.solution,
        item.classification,
        item.detail_classification,
    ]
    normalized_fields = [normalize_text(value) for value in fields if value]
    if not normalized_fields:
        return 0.0

    sequence_score = max(
        SequenceMatcher(None, query, field).ratio()
        for field in normalized_fields
    )

    query_tokens = set(re.findall(r"\w{3,}", query, flags=re.UNICODE))
    candidate_tokens = set(
        re.findall(
            r"\w{3,}",
            " ".join(normalized_fields),
            flags=re.UNICODE,
        )
    )
    overlap_score = (
        len(query_tokens & candidate_tokens) / len(query_tokens)
        if query_tokens
        else 0.0
    )

    return min(1.0, (sequence_score * 0.65) + (overlap_score * 0.35))


@router.post(
    "/diagnostic-suggestions",
    response_model=list[HistoricalDiagnosticSuggestion],
)
def diagnostic_suggestions(
    payload: HistoricalDiagnosticRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = normalize_text(payload.description)
    tokens = list(dict.fromkeys(re.findall(r"\w{3,}", query, flags=re.UNICODE)))[:8]

    conditions = []
    for token in tokens:
        like = f"%{token}%"
        conditions.extend(
            [
                HistoricalRequest.description_demande.ilike(like),
                HistoricalRequest.symptome.ilike(like),
                HistoricalRequest.cause.ilike(like),
                HistoricalRequest.solution.ilike(like),
                HistoricalRequest.classification.ilike(like),
                HistoricalRequest.detail_classification.ilike(like),
            ]
        )

    stmt = select(HistoricalRequest).where(
        or_(
            HistoricalRequest.description_demande.is_not(None),
            HistoricalRequest.symptome.is_not(None),
            HistoricalRequest.cause.is_not(None),
            HistoricalRequest.solution.is_not(None),
        )
    )

    if conditions:
        stmt = stmt.where(or_(*conditions))

    candidates = db.scalars(
        stmt.order_by(HistoricalRequest.id.desc()).limit(2000)
    ).all()

    if len(candidates) < payload.top_k:
        fallback = db.scalars(
            select(HistoricalRequest)
            .where(
                or_(
                    HistoricalRequest.cause.is_not(None),
                    HistoricalRequest.solution.is_not(None),
                )
            )
            .order_by(HistoricalRequest.id.desc())
            .limit(1000)
        ).all()

        known_ids = {item.id for item in candidates}
        candidates.extend(item for item in fallback if item.id not in known_ids)

    scored = sorted(
        (
            (candidate_score(query, item), item)
            for item in candidates
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )

    results = []
    for score, item in scored[: payload.top_k]:
        results.append(
            HistoricalDiagnosticSuggestion(
                intervention_id=item.id,
                similarity=round(score, 4),
                diagnosis=(
                    item.cause
                    or item.symptome
                    or item.classification
                    or item.detail_classification
                ),
                solution=item.solution,
            )
        )

    return results
