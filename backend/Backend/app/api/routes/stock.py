from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import Role, StockMovementType
from app.db.session import get_db
from app.models.stock import SparePart, StockMovement
from app.models.user import User
from app.schemas.stock import (
    SparePartCreate,
    SparePartRead,
    SparePartUpdate,
    StockMovementCreate,
    StockMovementRead,
)
from app.services.audit import log_action


router = APIRouter(tags=["Stock"])
Writer = Depends(require_roles(Role.ADMIN, Role.MANAGER, Role.STOCK_MANAGER))
Reader = Depends(get_current_user)


@router.get("/spare-parts", response_model=list[SparePartRead])
def list_parts(
    q: str | None = None,
    low_stock_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Reader,
):
    stmt = select(SparePart).order_by(SparePart.name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(SparePart.code.ilike(like), SparePart.name.ilike(like)))
    if low_stock_only:
        stmt = stmt.where(SparePart.quantity <= SparePart.minimum_threshold)
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("/spare-parts", response_model=SparePartRead, status_code=status.HTTP_201_CREATED)
def create_part(payload: SparePartCreate, db: Session = Depends(get_db), current_user: User = Writer):
    if db.scalar(select(SparePart).where(SparePart.code == payload.code.upper())):
        raise HTTPException(status_code=409, detail="Ce code pièce existe déjà")
    data = payload.model_dump()
    data["code"] = data["code"].upper()
    item = SparePart(**data)
    db.add(item)
    db.flush()
    log_action(db, actor_id=current_user.id, action="CREATE", entity_type="SparePart", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/spare-parts/{part_id}", response_model=SparePartRead)
def get_part(part_id: int, db: Session = Depends(get_db), _: User = Reader):
    item = db.get(SparePart, part_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    return item


@router.patch("/spare-parts/{part_id}", response_model=SparePartRead)
def update_part(part_id: int, payload: SparePartUpdate, db: Session = Depends(get_db), current_user: User = Writer):
    item = db.get(SparePart, part_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    log_action(db, actor_id=current_user.id, action="UPDATE", entity_type="SparePart", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/stock-movements", response_model=list[StockMovementRead])
def list_movements(
    part_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Reader,
):
    stmt = select(StockMovement).order_by(StockMovement.id.desc())
    if part_id:
        stmt = stmt.where(StockMovement.part_id == part_id)
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("/stock-movements", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def create_movement(payload: StockMovementCreate, db: Session = Depends(get_db), current_user: User = Writer):
    part = db.get(SparePart, payload.part_id)
    if part is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")

    movement_type = payload.movement_type
    if movement_type in {StockMovementType.OUT, StockMovementType.ADJUSTMENT_NEGATIVE}:
        if part.quantity < payload.quantity:
            raise HTTPException(status_code=400, detail="Stock insuffisant")
        part.quantity -= payload.quantity
    elif movement_type in {StockMovementType.IN, StockMovementType.RETURN, StockMovementType.ADJUSTMENT_POSITIVE}:
        part.quantity += payload.quantity
    elif movement_type == StockMovementType.INVENTORY:
        part.quantity = payload.quantity

    movement = StockMovement(
        part_id=payload.part_id,
        movement_type=movement_type.value,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        intervention_id=payload.intervention_id,
        performed_by_id=current_user.id,
        reason=payload.reason,
    )
    db.add(movement)
    db.flush()
    log_action(db, actor_id=current_user.id, action="STOCK_MOVEMENT", entity_type="SparePart", entity_id=part.id, details={"type": movement_type.value, "quantity": payload.quantity})
    db.commit()
    db.refresh(movement)
    return movement
