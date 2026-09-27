from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import Priority, RecommendationStatus, RecommendationType, RiskLevel, Role
from app.db.session import get_db
from app.models.intelligence import Recommendation
from app.models.user import User
from app.schemas.intelligence import RecommendationRead, RecommendationUpdate
from app.services.ai import equipment_risk_score
from app.services.audit import log_action


router = APIRouter(prefix="/recommendations", tags=["Recommandations"])


@router.get("", response_model=list[RecommendationRead])
def list_recommendations(
    recommendation_status: RecommendationStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Recommendation).order_by(Recommendation.id.desc())
    if recommendation_status:
        stmt = stmt.where(Recommendation.status == recommendation_status.value)
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("/generate/equipment/{equipment_id}", response_model=RecommendationRead, status_code=status.HTTP_201_CREATED)
def generate_equipment_recommendation(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
):
    risk = equipment_risk_score(db, equipment_id)
    if risk["level"] == RiskLevel.HIGH.value:
        priority = Priority.CRITICAL.value
        recommendation_type = RecommendationType.PREVENTIVE_MAINTENANCE.value
        due_date = date.today() + timedelta(days=15)
    elif risk["level"] == RiskLevel.MEDIUM.value:
        priority = Priority.HIGH.value
        recommendation_type = RecommendationType.PREVENTIVE_MAINTENANCE.value
        due_date = date.today() + timedelta(days=30)
    else:
        priority = Priority.LOW.value
        recommendation_type = RecommendationType.PREVENTIVE_MAINTENANCE.value
        due_date = date.today() + timedelta(days=90)

    item = Recommendation(
        equipment_id=equipment_id,
        recommendation_type=recommendation_type,
        priority=priority,
        title=f"Recommandation pour l'équipement {equipment_id}",
        observation=f"Score de risque calculé : {risk['score']}/100 ({risk['level']}).",
        justification="; ".join(risk["factors"]),
        recommended_action=risk["recommended_action"],
        risk_score=risk["score"],
        risk_level=risk["level"],
        due_date=due_date,
    )
    db.add(item)
    db.flush()
    log_action(db, actor_id=current_user.id, action="GENERATE", entity_type="Recommendation", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{recommendation_id}", response_model=RecommendationRead)
def update_recommendation(
    recommendation_id: int,
    payload: RecommendationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
):
    item = db.get(Recommendation, recommendation_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Recommandation introuvable")
    item.status = payload.status.value
    item.due_date = payload.due_date
    item.validated_by_id = current_user.id
    log_action(db, actor_id=current_user.id, action="UPDATE", entity_type="Recommendation", entity_id=item.id, details={"status": item.status})
    db.commit()
    db.refresh(item)
    return item
