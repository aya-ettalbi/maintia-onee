from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.enums import EquipmentStatus, InterventionStatus, RecommendationStatus, RequestStatus
from app.db.session import get_db
from app.models.equipment import Equipment
from app.models.intelligence import Recommendation
from app.models.maintenance import Intervention, MaintenanceRequest
from app.models.stock import SparePart
from app.models.user import User
from app.schemas.dashboard import DashboardSummary


router = APIRouter(prefix="/dashboard", tags=["Tableau de bord"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total_equipments = db.scalar(select(func.count()).select_from(Equipment).where(Equipment.archived.is_(False))) or 0
    in_service = db.scalar(select(func.count()).select_from(Equipment).where(Equipment.status == EquipmentStatus.IN_SERVICE.value, Equipment.archived.is_(False))) or 0
    in_failure = db.scalar(select(func.count()).select_from(Equipment).where(Equipment.status == EquipmentStatus.IN_FAILURE.value, Equipment.archived.is_(False))) or 0
    open_requests = db.scalar(select(func.count()).select_from(MaintenanceRequest).where(MaintenanceRequest.status.not_in([RequestStatus.CLOSED.value, RequestStatus.CANCELLED.value, RequestStatus.REJECTED.value]))) or 0
    active_interventions = db.scalar(select(func.count()).select_from(Intervention).where(Intervention.status.not_in([InterventionStatus.COMPLETED.value, InterventionStatus.CANCELLED.value]))) or 0
    low_stock_parts = db.scalar(select(func.count()).select_from(SparePart).where(SparePart.quantity <= SparePart.minimum_threshold, SparePart.active.is_(True))) or 0
    open_recommendations = db.scalar(select(func.count()).select_from(Recommendation).where(Recommendation.status.not_in([RecommendationStatus.APPLIED.value, RecommendationStatus.REJECTED.value, RecommendationStatus.EXPIRED.value]))) or 0

    completed = db.scalars(
        select(Intervention).where(
            Intervention.status == InterventionStatus.COMPLETED.value,
            Intervention.started_at.is_not(None),
            Intervention.ended_at.is_not(None),
        )
    ).all()
    hours = [
        (item.ended_at - item.started_at).total_seconds() / 3600
        for item in completed
        if item.started_at and item.ended_at
    ]
    average = round(sum(hours) / len(hours), 2) if hours else None

    return DashboardSummary(
        total_equipments=total_equipments,
        equipments_in_service=in_service,
        equipments_in_failure=in_failure,
        open_requests=open_requests,
        active_interventions=active_interventions,
        low_stock_parts=low_stock_parts,
        open_recommendations=open_recommendations,
        average_repair_hours=average,
    )
