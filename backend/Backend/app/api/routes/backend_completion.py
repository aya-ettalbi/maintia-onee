from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import EquipmentStatus, RequestStatus, Role, UserStatus
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit import Notification
from app.models.equipment import Equipment
from app.models.maintenance import MaintenanceRequest
from app.models.user import User
from app.schemas.backend_completion import (
    AdminPasswordReset,
    NotificationUnreadCount,
    RecurrentFailuresResponse,
    RiskAssessmentResponse,
    StockShortageRisksResponse,
    TriageRequest,
    TriageResponse,
)
from app.schemas.common import Message
from app.schemas.maintenance import MaintenanceRequestRead
from app.schemas.user import UserRead
from app.services.audit import create_notification, log_action
from app.services.backend_completion import (
    equipment_risk_assessment,
    recurrent_failures,
    stock_shortage_risks,
    triage_request,
)


router = APIRouter(tags=["Compléments Backend"])
Admin = Depends(require_roles(Role.ADMIN))
ManagerWriter = Depends(require_roles(Role.ADMIN, Role.MANAGER))


def _inactive_user_status() -> str:
    for name in ("INACTIVE", "DISABLED", "SUSPENDED"):
        member = getattr(UserStatus, name, None)
        if member is not None:
            return str(member.value)
    return "INACTIVE"


def _active_user_status() -> str:
    member = getattr(UserStatus, "ACTIVE", None)
    return str(member.value) if member is not None else "ACTIVE"


@router.post("/users/{user_id}/activate", response_model=UserRead)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Admin,
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user.status = _active_user_status()
    log_action(
        db,
        actor_id=current_user.id,
        action="ACTIVATE",
        entity_type="User",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Admin,
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas désactiver votre propre compte",
        )

    user.status = _inactive_user_status()
    log_action(
        db,
        actor_id=current_user.id,
        action="DEACTIVATE",
        entity_type="User",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=Message)
def reset_user_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Admin,
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user.hashed_password = hash_password(payload.new_password)
    log_action(
        db,
        actor_id=current_user.id,
        action="RESET_PASSWORD",
        entity_type="User",
        entity_id=user.id,
        details={"password_exposed": False},
    )
    db.commit()
    return Message(message="Mot de passe réinitialisé avec succès")


@router.post("/equipments/{equipment_id}/activate", response_model=Message)
def activate_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = ManagerWriter,
):
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Équipement introuvable")

    equipment.archived = False
    equipment.status = EquipmentStatus.IN_SERVICE.value

    log_action(
        db,
        actor_id=current_user.id,
        action="ACTIVATE",
        entity_type="Equipment",
        entity_id=equipment.id,
    )
    db.commit()
    return Message(message="Équipement réactivé avec succès")


@router.post(
    "/maintenance-requests/{request_id}/cancel",
    response_model=MaintenanceRequestRead,
)
def cancel_maintenance_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(MaintenanceRequest, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    terminal_values = {
        RequestStatus.CANCELLED.value,
        RequestStatus.CLOSED.value,
        RequestStatus.RESOLVED.value,
        RequestStatus.REJECTED.value,
    }
    if item.status in terminal_values:
        raise HTTPException(status_code=409, detail="Cette demande est déjà terminée")

    manager_roles = {Role.ADMIN.value, Role.MANAGER.value}
    if current_user.role == Role.REQUESTER.value:
        if item.requester_id != current_user.id:
            raise HTTPException(status_code=403, detail="Droits insuffisants")
        draft_member = getattr(RequestStatus, "DRAFT", None)
        allowed_requester_statuses = {RequestStatus.SUBMITTED.value}
        if draft_member is not None:
            allowed_requester_statuses.add(draft_member.value)
        if item.status not in allowed_requester_statuses:
            raise HTTPException(
                status_code=403,
                detail="Cette demande ne peut plus être annulée par le demandeur",
            )
    elif current_user.role not in manager_roles:
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    item.status = RequestStatus.CANCELLED.value
    item.closed_at = datetime.now(timezone.utc)

    if item.assigned_technician_id is not None:
        create_notification(
            db,
            user_id=item.assigned_technician_id,
            title="Demande annulée",
            message=f"La demande {item.reference} a été annulée.",
        )

    log_action(
        db,
        actor_id=current_user.id,
        action="CANCEL",
        entity_type="MaintenanceRequest",
        entity_id=item.id,
        details={"new_status": item.status},
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/notifications/read-all", response_model=Message)
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    db.commit()
    return Message(message="Toutes les notifications ont été marquées comme lues")


@router.get("/notifications/unread-count", response_model=NotificationUnreadCount)
def unread_notifications_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = int(
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == current_user.id,
                Notification.read_at.is_(None),
            )
        ) or 0
    )
    return NotificationUnreadCount(unread_count=count)


@router.post("/ai/triage", response_model=TriageResponse)
def ai_triage(
    payload: TriageRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return triage_request(
        db,
        description=payload.description,
        equipment_code=payload.equipment_code,
    )


@router.get(
    "/ai/equipments/{equipment_id}/risk-assessment",
    response_model=RiskAssessmentResponse,
)
def ai_risk_assessment(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return equipment_risk_assessment(db, equipment_id)


@router.get(
    "/ai/analytics/recurrent-failures",
    response_model=RecurrentFailuresResponse,
)
def ai_recurrent_failures(
    period_months: int = Query(default=24, ge=1, le=120),
    minimum_occurrences: int = Query(default=3, ge=2, le=10000),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return recurrent_failures(
        db,
        period_months=period_months,
        minimum_occurrences=minimum_occurrences,
        limit=limit,
    )


@router.get(
    "/ai/stock/shortage-risks",
    response_model=StockShortageRisksResponse,
)
def ai_stock_shortage_risks(
    lookback_days: int = Query(default=90, ge=30, le=730),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return stock_shortage_risks(
        db,
        lookback_days=lookback_days,
        limit=limit,
    )
