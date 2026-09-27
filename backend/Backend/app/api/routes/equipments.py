from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import EquipmentStatus, Role
from app.db.session import get_db
from app.models.equipment import Equipment, EquipmentAssignment, EquipmentCategory
from app.models.maintenance import Intervention, MaintenanceRequest
from app.models.user import User
from app.schemas.common import Message
from app.schemas.equipment import (
    EquipmentAssignmentCreate,
    EquipmentAssignmentRead,
    EquipmentCategoryCreate,
    EquipmentCategoryRead,
    EquipmentCategoryUpdate,
    EquipmentCreate,
    EquipmentRead,
    EquipmentUpdate,
)
from app.services.audit import log_action


router = APIRouter(tags=["Parc informatique"])
Writer = Depends(require_roles(Role.ADMIN, Role.MANAGER))
Reader = Depends(get_current_user)


@router.get("/equipment-categories", response_model=list[EquipmentCategoryRead])
def list_categories(db: Session = Depends(get_db), _: User = Reader):
    return db.scalars(select(EquipmentCategory).order_by(EquipmentCategory.name)).all()


@router.post("/equipment-categories", response_model=EquipmentCategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: EquipmentCategoryCreate, db: Session = Depends(get_db), current_user: User = Writer):
    if db.scalar(select(EquipmentCategory).where(EquipmentCategory.code == payload.code.upper())):
        raise HTTPException(status_code=409, detail="Ce code existe déjà")
    item = EquipmentCategory(code=payload.code.upper(), name=payload.name, description=payload.description)
    db.add(item)
    db.flush()
    log_action(db, actor_id=current_user.id, action="CREATE", entity_type="EquipmentCategory", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/equipment-categories/{category_id}", response_model=EquipmentCategoryRead)
def update_category(category_id: int, payload: EquipmentCategoryUpdate, db: Session = Depends(get_db), current_user: User = Writer):
    item = db.get(EquipmentCategory, category_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"]:
        data["code"] = data["code"].upper()
    for key, value in data.items():
        setattr(item, key, value)
    log_action(db, actor_id=current_user.id, action="UPDATE", entity_type="EquipmentCategory", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/equipments", response_model=list[EquipmentRead])
def list_equipments(
    q: str | None = None,
    equipment_status: EquipmentStatus | None = None,
    category_id: int | None = None,
    include_archived: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Reader,
):
    stmt = select(Equipment).order_by(Equipment.id.desc())
    if not include_archived:
        stmt = stmt.where(Equipment.archived.is_(False))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Equipment.code.ilike(like),
                Equipment.brand.ilike(like),
                Equipment.model.ilike(like),
                Equipment.serial_number.ilike(like),
            )
        )
    if equipment_status:
        stmt = stmt.where(Equipment.status == equipment_status.value)
    if category_id:
        stmt = stmt.where(Equipment.category_id == category_id)
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("/equipments", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
def create_equipment(payload: EquipmentCreate, db: Session = Depends(get_db), current_user: User = Writer):
    if db.scalar(select(Equipment).where(Equipment.code == payload.code.upper())):
        raise HTTPException(status_code=409, detail="Ce code équipement existe déjà")
    if db.get(EquipmentCategory, payload.category_id) is None:
        raise HTTPException(status_code=400, detail="Catégorie invalide")
    data = payload.model_dump()
    data["code"] = data["code"].upper()
    data["status"] = data["status"].value
    item = Equipment(**data)
    db.add(item)
    db.flush()
    log_action(db, actor_id=current_user.id, action="CREATE", entity_type="Equipment", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/equipments/{equipment_id}", response_model=EquipmentRead)
def get_equipment(equipment_id: int, db: Session = Depends(get_db), _: User = Reader):
    item = db.get(Equipment, equipment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Équipement introuvable")
    return item


@router.patch("/equipments/{equipment_id}", response_model=EquipmentRead)
def update_equipment(equipment_id: int, payload: EquipmentUpdate, db: Session = Depends(get_db), current_user: User = Writer):
    item = db.get(Equipment, equipment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Équipement introuvable")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        data["status"] = data["status"].value
    for key, value in data.items():
        setattr(item, key, value)
    log_action(db, actor_id=current_user.id, action="UPDATE", entity_type="Equipment", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.post("/equipments/{equipment_id}/archive", response_model=Message)
def archive_equipment(equipment_id: int, db: Session = Depends(get_db), current_user: User = Writer):
    item = db.get(Equipment, equipment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Équipement introuvable")
    item.archived = True
    item.status = EquipmentStatus.ARCHIVED.value
    log_action(db, actor_id=current_user.id, action="ARCHIVE", entity_type="Equipment", entity_id=item.id)
    db.commit()
    return Message(message="Équipement archivé")


@router.post("/equipments/{equipment_id}/assignments", response_model=EquipmentAssignmentRead, status_code=status.HTTP_201_CREATED)
def assign_equipment(equipment_id: int, payload: EquipmentAssignmentCreate, db: Session = Depends(get_db), current_user: User = Writer):
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Équipement introuvable")
    if equipment.status in {EquipmentStatus.REFORMED.value, EquipmentStatus.ARCHIVED.value}:
        raise HTTPException(status_code=400, detail="Un équipement réformé ou archivé ne peut pas être affecté")
    active = db.scalars(
        select(EquipmentAssignment).where(
            EquipmentAssignment.equipment_id == equipment_id,
            EquipmentAssignment.is_active.is_(True),
        )
    ).all()
    now = datetime.now(timezone.utc)
    for old in active:
        old.is_active = False
        old.returned_at = now
    assignment = EquipmentAssignment(equipment_id=equipment_id, **payload.model_dump())
    db.add(assignment)
    db.flush()
    log_action(db, actor_id=current_user.id, action="ASSIGN", entity_type="Equipment", entity_id=equipment_id)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/equipments/{equipment_id}/assignments", response_model=list[EquipmentAssignmentRead])
def list_assignments(equipment_id: int, db: Session = Depends(get_db), _: User = Reader):
    return db.scalars(
        select(EquipmentAssignment)
        .where(EquipmentAssignment.equipment_id == equipment_id)
        .order_by(EquipmentAssignment.assigned_at.desc())
    ).all()


@router.get("/equipments/{equipment_id}/history")
def equipment_history(equipment_id: int, db: Session = Depends(get_db), _: User = Reader):
    if db.get(Equipment, equipment_id) is None:
        raise HTTPException(status_code=404, detail="Équipement introuvable")
    requests = db.scalars(
        select(MaintenanceRequest).where(MaintenanceRequest.equipment_id == equipment_id).order_by(MaintenanceRequest.created_at.desc())
    ).all()
    interventions = db.scalars(
        select(Intervention).where(Intervention.equipment_id == equipment_id).order_by(Intervention.created_at.desc())
    ).all()
    assignments = db.scalars(
        select(EquipmentAssignment).where(EquipmentAssignment.equipment_id == equipment_id).order_by(EquipmentAssignment.assigned_at.desc())
    ).all()
    return {
        "equipment_id": equipment_id,
        "requests": [{"id": x.id, "reference": x.reference, "status": x.status, "created_at": x.created_at} for x in requests],
        "interventions": [{"id": x.id, "reference": x.reference, "status": x.status, "diagnosis": x.diagnosis, "solution": x.solution, "created_at": x.created_at} for x in interventions],
        "assignments": [{"id": x.id, "user_id": x.user_id, "service_id": x.service_id, "assigned_at": x.assigned_at, "returned_at": x.returned_at} for x in assignments],
    }
