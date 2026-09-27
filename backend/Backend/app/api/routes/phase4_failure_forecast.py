from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import Role
from app.db.session import get_db
from app.models.phase4_failure_forecast import (
    FailureForecast,
    FailureForecastRun,
)
from app.models.user import User
from app.schemas.phase4_failure_forecast import (
    FailureForecastBatchRequest,
    FailureForecastBatchResponse,
    FailureForecastRead,
    FailureForecastRunRead,
    FailureForecastSummary,
    FailureForecastValidation,
)
from app.services.audit import log_action
from app.services.phase4_failure_forecast import (
    build_forecast_snapshot,
    build_forecast_summary,
    enrich_snapshot_with_llm,
    latest_forecast_query,
    persist_forecast,
    run_batch_forecasts,
)


router = APIRouter(tags=["Phase 4 - Prediction IA des pannes"])


@router.post(
    "/ai/failure-forecasts/equipments/{equipment_id}",
    response_model=FailureForecastRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_failure_forecast(
    equipment_id: int,
    horizon_days: int = Query(default=90, ge=30, le=365),
    use_llm: bool = Query(default=True),
    create_actions: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)
    ),
):
    if (
        create_actions
        and current_user.role
        not in {Role.ADMIN.value, Role.MANAGER.value}
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Seuls ADMIN et MANAGER peuvent creer "
                "les notifications et recommandations"
            ),
        )

    snapshot = build_forecast_snapshot(
        db,
        equipment_id=equipment_id,
        horizon_days=horizon_days,
    )
    if use_llm:
        snapshot = await enrich_snapshot_with_llm(snapshot)

    forecast, _, _ = persist_forecast(
        db,
        snapshot=snapshot,
        created_by_id=current_user.id,
        create_actions=create_actions,
    )
    db.commit()
    db.refresh(forecast)
    return forecast


@router.get(
    "/ai/failure-forecasts/equipments/{equipment_id}/latest",
    response_model=FailureForecastRead,
)
def latest_failure_forecast(
    equipment_id: int,
    horizon_days: int | None = Query(default=None, ge=30, le=365),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(FailureForecast)
        .where(FailureForecast.equipment_id == equipment_id)
        .order_by(FailureForecast.id.desc())
    )
    if horizon_days is not None:
        stmt = stmt.where(
            FailureForecast.horizon_days == horizon_days
        )

    forecast = db.scalar(stmt.limit(1))
    if forecast is None:
        raise HTTPException(
            status_code=404,
            detail="Aucune prevision disponible pour cet equipement",
        )
    return forecast


@router.get(
    "/ai/failure-forecasts/equipments/{equipment_id}/history",
    response_model=list[FailureForecastRead],
)
def failure_forecast_history(
    equipment_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.scalars(
        select(FailureForecast)
        .where(FailureForecast.equipment_id == equipment_id)
        .order_by(FailureForecast.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()


@router.post(
    "/ai/failure-forecasts/batch",
    response_model=FailureForecastBatchResponse,
)
def batch_failure_forecasts(
    payload: FailureForecastBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER)
    ),
):
    return run_batch_forecasts(
        db,
        payload=payload,
        actor=current_user,
    )


@router.get(
    "/ai/failure-forecasts/high-risk",
    response_model=list[FailureForecastRead],
)
def high_risk_failure_forecasts(
    horizon_days: int | None = Query(default=None, ge=30, le=365),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    latest_ids = latest_forecast_query(
        horizon_days=horizon_days
    ).subquery()

    return db.scalars(
        select(FailureForecast)
        .where(
            FailureForecast.id.in_(select(latest_ids.c.id)),
            FailureForecast.risk_level == "HIGH",
        )
        .order_by(
            FailureForecast.risk_score.desc(),
            FailureForecast.id.desc(),
        )
        .limit(limit)
    ).all()


@router.get(
    "/ai/failure-forecasts/summary",
    response_model=FailureForecastSummary,
)
def failure_forecasts_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return build_forecast_summary(db)


@router.patch(
    "/ai/failure-forecasts/{forecast_id}/validate",
    response_model=FailureForecastRead,
)
def validate_failure_forecast(
    forecast_id: int,
    payload: FailureForecastValidation,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)
    ),
):
    forecast = db.get(FailureForecast, forecast_id)
    if forecast is None:
        raise HTTPException(
            status_code=404,
            detail="Prevision introuvable",
        )

    forecast.validation_status = payload.validation_status
    forecast.validation_notes = (
        payload.notes.strip()
        if payload.notes
        else None
    )
    forecast.actual_failure_occurred = (
        payload.actual_failure_occurred
    )
    forecast.actual_failure_date = payload.actual_failure_date
    forecast.validated_by_id = current_user.id
    forecast.validated_at = datetime.now(timezone.utc)

    log_action(
        db,
        actor_id=current_user.id,
        action="VALIDATE_FAILURE_FORECAST",
        entity_type="FailureForecast",
        entity_id=forecast.id,
        details={
            "validation_status": forecast.validation_status,
            "actual_failure_occurred": (
                forecast.actual_failure_occurred
            ),
            "actual_failure_date": (
                forecast.actual_failure_date.isoformat()
                if forecast.actual_failure_date
                else None
            ),
        },
    )
    db.commit()
    db.refresh(forecast)
    return forecast


@router.get(
    "/ai/failure-forecast-runs",
    response_model=list[FailureForecastRunRead],
)
def list_failure_forecast_runs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.scalars(
        select(FailureForecastRun)
        .order_by(FailureForecastRun.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
