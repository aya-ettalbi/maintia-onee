from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import EquipmentStatus, InterventionStatus, Role, StockMovementType
from app.db.session import get_db
from app.models.equipment import Equipment
from app.models.maintenance import (
    Intervention,
    InterventionAction,
    InterventionStatusHistory,
    MaintenanceRequest,
)
from app.models.stock import InterventionPart, SparePart, StockMovement
from app.models.user import User
from app.schemas.maintenance import (
    InterventionActionCreate,
    InterventionActionRead,
    InterventionCreate,
    InterventionPartCreate,
    InterventionPartRead,
    InterventionRead,
    InterventionStatusChange,
    InterventionStatusHistoryRead,
    InterventionUpdate,
)
from app.services.audit import log_action
from app.services.references import generate_reference


router = APIRouter(prefix="/interventions", tags=["Interventions"])


@router.get("", response_model=list[InterventionRead])
def list_interventions(
    intervention_status: InterventionStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Intervention).order_by(Intervention.id.desc())
    if current_user.role == Role.TECHNICIAN.value:
        stmt = stmt.where(Intervention.technician_id == current_user.id)
    if intervention_status:
        stmt = stmt.where(Intervention.status == intervention_status.value)
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("", response_model=InterventionRead, status_code=status.HTTP_201_CREATED)
def create_intervention(
    payload: InterventionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
):
    equipment = db.get(Equipment, payload.equipment_id)
    if equipment is None or equipment.archived:
        raise HTTPException(status_code=400, detail="Équipement invalide")
    technician = db.get(User, payload.technician_id)
    if technician is None or technician.role != Role.TECHNICIAN.value:
        raise HTTPException(status_code=400, detail="Technicien invalide")
    if payload.request_id is not None and db.get(MaintenanceRequest, payload.request_id) is None:
        raise HTTPException(status_code=400, detail="Demande invalide")
    item = Intervention(
        reference=generate_reference("INT"),
        request_id=payload.request_id,
        equipment_id=payload.equipment_id,
        technician_id=payload.technician_id,
        maintenance_type=payload.maintenance_type.value,
        estimated_cost=payload.estimated_cost,
        status=InterventionStatus.PLANNED.value,
    )
    db.add(item)
    db.flush()
    db.add(
        InterventionStatusHistory(
            intervention_id=item.id,
            old_status=None,
            new_status=item.status,
            changed_by_id=current_user.id,
            comment="Création de l'intervention",
        )
    )
    equipment.status = EquipmentStatus.IN_MAINTENANCE.value
    log_action(db, actor_id=current_user.id, action="CREATE", entity_type="Intervention", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{intervention_id}", response_model=InterventionRead)
def get_intervention(intervention_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.get(Intervention, intervention_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Intervention introuvable")
    if current_user.role == Role.TECHNICIAN.value and item.technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès interdit")
    return item


@router.patch("/{intervention_id}", response_model=InterventionRead)
def update_intervention(
    intervention_id: int,
    payload: InterventionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(Intervention, intervention_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Intervention introuvable")
    if current_user.role == Role.TECHNICIAN.value and item.technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cette intervention ne vous est pas affectée")
    if current_user.role not in {Role.ADMIN.value, Role.MANAGER.value, Role.TECHNICIAN.value}:
        raise HTTPException(status_code=403, detail="Droits insuffisants")
    data = payload.model_dump(exclude_unset=True)
    if "maintenance_type" in data and data["maintenance_type"] is not None:
        data["maintenance_type"] = data["maintenance_type"].value
    for key, value in data.items():
        setattr(item, key, value)
    log_action(db, actor_id=current_user.id, action="UPDATE", entity_type="Intervention", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{intervention_id}/status", response_model=InterventionRead)
def change_intervention_status(
    intervention_id: int,
    payload: InterventionStatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)),
):
    item = db.get(Intervention, intervention_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Intervention introuvable")
    if current_user.role == Role.TECHNICIAN.value and item.technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cette intervention ne vous est pas affectée")

    old_status = item.status
    new_status = payload.status.value
    # PHASE2_TERMINAL_STATUS_GUARD
    if new_status == InterventionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=409,
            detail=(
                "Utilisez POST /interventions/{id}/close "
                "pour cloturer une intervention"
            ),
        )
    if new_status == InterventionStatus.CANCELLED.value:
        raise HTTPException(
            status_code=409,
            detail=(
                "Utilisez POST /interventions/{id}/cancel "
                "pour annuler une intervention"
            ),
        )
    if payload.status == InterventionStatus.COMPLETED:
        if not item.diagnosis or not item.solution or not item.test_result:
            raise HTTPException(
                status_code=400,
                detail="Diagnostic, solution et résultat du test sont obligatoires avant clôture",
            )
        item.ended_at = datetime.now(timezone.utc)
        item.closed_by_id = current_user.id
        equipment = db.get(Equipment, item.equipment_id)
        if equipment:
            equipment.status = EquipmentStatus.IN_SERVICE.value
    elif payload.status in {InterventionStatus.DIAGNOSING, InterventionStatus.REPAIRING}:
        if item.started_at is None:
            item.started_at = datetime.now(timezone.utc)
    elif payload.status == InterventionStatus.WAITING_FOR_PART:
        equipment = db.get(Equipment, item.equipment_id)
        if equipment:
            equipment.status = EquipmentStatus.WAITING_PART.value

    item.status = new_status
    db.add(
        InterventionStatusHistory(
            intervention_id=item.id,
            old_status=old_status,
            new_status=new_status,
            changed_by_id=current_user.id,
            comment=payload.comment,
        )
    )
    log_action(db, actor_id=current_user.id, action="STATUS_CHANGE", entity_type="Intervention", entity_id=item.id, details={"old": old_status, "new": new_status})
    db.commit()
    db.refresh(item)
    return item


@router.get("/{intervention_id}/status-history", response_model=list[InterventionStatusHistoryRead])
def status_history(intervention_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(
        select(InterventionStatusHistory)
        .where(InterventionStatusHistory.intervention_id == intervention_id)
        .order_by(InterventionStatusHistory.changed_at)
    ).all()


@router.post("/{intervention_id}/actions", response_model=InterventionActionRead, status_code=status.HTTP_201_CREATED)
def add_action(
    intervention_id: int,
    payload: InterventionActionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)),
):
    item = db.get(Intervention, intervention_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Intervention introuvable")
    if current_user.role == Role.TECHNICIAN.value and item.technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cette intervention ne vous est pas affectée")
    action = InterventionAction(
        intervention_id=intervention_id,
        description=payload.description,
        performed_by_id=current_user.id,
    )
    db.add(action)
    db.flush()
    log_action(db, actor_id=current_user.id, action="ADD_ACTION", entity_type="Intervention", entity_id=intervention_id)
    db.commit()
    db.refresh(action)
    return action


@router.get("/{intervention_id}/actions", response_model=list[InterventionActionRead])
def list_actions(intervention_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(
        select(InterventionAction)
        .where(InterventionAction.intervention_id == intervention_id)
        .order_by(InterventionAction.performed_at)
    ).all()


@router.post("/{intervention_id}/parts", response_model=InterventionPartRead, status_code=status.HTTP_201_CREATED)
def add_part_to_intervention(
    intervention_id: int,
    payload: InterventionPartCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN, Role.STOCK_MANAGER)),
):
    intervention = db.get(Intervention, intervention_id)
    part = db.get(SparePart, payload.part_id)
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervention introuvable")
    if (
        current_user.role == Role.TECHNICIAN.value
        and intervention.technician_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Cette intervention ne vous est pas affectee",
        )
    if intervention.status in {
        InterventionStatus.COMPLETED.value,
        InterventionStatus.CANCELLED.value,
    }:
        raise HTTPException(
            status_code=409,
            detail="Intervention terminee ou annulee",
        )
    if part is None or not part.active:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    if part.quantity < payload.quantity:
        raise HTTPException(status_code=400, detail="Stock insuffisant")

    existing = db.scalar(
        select(InterventionPart).where(
            InterventionPart.intervention_id == intervention_id,
            InterventionPart.part_id == payload.part_id,
        )
    )
    if existing:
        existing.quantity += payload.quantity
        link = existing
    else:
        link = InterventionPart(
            intervention_id=intervention_id,
            part_id=payload.part_id,
            quantity=payload.quantity,
            unit_price=part.unit_price,
        )
        db.add(link)

    part.quantity -= payload.quantity
    movement = StockMovement(
        part_id=part.id,
        movement_type=StockMovementType.OUT.value,
        quantity=payload.quantity,
        unit_cost=part.unit_price,
        intervention_id=intervention_id,
        performed_by_id=current_user.id,
        reason="Pièce utilisée dans une intervention",
    )
    db.add(movement)
    intervention.actual_cost = Decimal(intervention.actual_cost or 0) + (Decimal(part.unit_price) * payload.quantity)
    db.flush()
    log_action(db, actor_id=current_user.id, action="ADD_PART", entity_type="Intervention", entity_id=intervention_id, details={"part_id": part.id, "quantity": payload.quantity})
    db.commit()
    db.refresh(link)
    return link


@router.get("/{intervention_id}/parts", response_model=list[InterventionPartRead])
def list_intervention_parts(intervention_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(
        select(InterventionPart).where(InterventionPart.intervention_id == intervention_id)
    ).all()
