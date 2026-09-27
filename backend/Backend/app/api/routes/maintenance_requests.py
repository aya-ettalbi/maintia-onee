from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import RequestStatus, Role
from app.db.session import get_db
from app.models.equipment import Equipment
from app.models.maintenance import MaintenanceRequest
from app.models.user import User
from app.schemas.maintenance import (
    MaintenanceRequestCreate,
    MaintenanceRequestRead,
    MaintenanceRequestStatusChange,
    MaintenanceRequestUpdate,
)
from app.services.audit import create_notification, log_action
from app.services.references import generate_reference


router = APIRouter(prefix="/maintenance-requests", tags=["Demandes de maintenance"])


@router.get("", response_model=list[MaintenanceRequestRead])
def list_requests(
    request_status: RequestStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(MaintenanceRequest).order_by(MaintenanceRequest.id.desc())
    if current_user.role == Role.REQUESTER.value:
        stmt = stmt.where(MaintenanceRequest.requester_id == current_user.id)
    elif current_user.role == Role.TECHNICIAN.value:
        stmt = stmt.where(MaintenanceRequest.assigned_technician_id == current_user.id)
    if request_status:
        stmt = stmt.where(MaintenanceRequest.status == request_status.value)
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("", response_model=MaintenanceRequestRead, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: MaintenanceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    equipment = db.get(Equipment, payload.equipment_id)
    if equipment is None or equipment.archived:
        raise HTTPException(status_code=400, detail="Équipement invalide ou archivé")
    item = MaintenanceRequest(
        reference=generate_reference("REQ"),
        equipment_id=payload.equipment_id,
        requester_id=current_user.id,
        description=payload.description,
        category=payload.category,
        priority=payload.priority.value,
        status=RequestStatus.SUBMITTED.value,
    )
    db.add(item)
    db.flush()
    log_action(db, actor_id=current_user.id, action="CREATE", entity_type="MaintenanceRequest", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{request_id}", response_model=MaintenanceRequestRead)
def get_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.get(MaintenanceRequest, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if current_user.role == Role.REQUESTER.value and item.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès interdit")
    if current_user.role == Role.TECHNICIAN.value and item.assigned_technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès interdit")
    return item


@router.patch("/{request_id}", response_model=MaintenanceRequestRead)
def update_request(
    request_id: int,
    payload: MaintenanceRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(MaintenanceRequest, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if current_user.role == Role.REQUESTER.value:
        if item.requester_id != current_user.id or item.status not in {RequestStatus.DRAFT.value, RequestStatus.SUBMITTED.value}:
            raise HTTPException(status_code=403, detail="Cette demande ne peut plus être modifiée")
    elif current_user.role not in {Role.ADMIN.value, Role.MANAGER.value}:
        raise HTTPException(status_code=403, detail="Droits insuffisants")
    data = payload.model_dump(exclude_unset=True)
    if "priority" in data and data["priority"] is not None:
        data["priority"] = data["priority"].value
    if data.get("assigned_technician_id"):
        item.assigned_at = datetime.now(timezone.utc)
    for key, value in data.items():
        setattr(item, key, value)
    log_action(db, actor_id=current_user.id, action="UPDATE", entity_type="MaintenanceRequest", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{request_id}/status", response_model=MaintenanceRequestRead)
def change_request_status(
    request_id: int,
    payload: MaintenanceRequestStatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)),
):
    item = db.get(MaintenanceRequest, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if current_user.role == Role.TECHNICIAN.value and item.assigned_technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cette demande ne vous est pas affectée")
    item.status = payload.status.value
    if payload.assigned_technician_id is not None:
        item.assigned_technician_id = payload.assigned_technician_id
        item.assigned_at = datetime.now(timezone.utc)
        create_notification(
            db,
            user_id=payload.assigned_technician_id,
            title="Nouvelle demande affectée",
            message=f"La demande {item.reference} vous a été affectée.",
        )
    if payload.status in {RequestStatus.RESOLVED, RequestStatus.CLOSED, RequestStatus.CANCELLED}:
        item.closed_at = datetime.now(timezone.utc)
    log_action(db, actor_id=current_user.id, action="STATUS_CHANGE", entity_type="MaintenanceRequest", entity_id=item.id, details={"new_status": item.status})
    db.commit()
    db.refresh(item)
    return item
