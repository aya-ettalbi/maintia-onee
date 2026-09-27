from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import Role
from app.db.session import get_db
from app.models.organization import Location, Service
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationRead, OrganizationUpdate
from app.services.audit import log_action


router = APIRouter(tags=["Organisation"])
Writer = Depends(require_roles(Role.ADMIN, Role.MANAGER))
Reader = Depends(get_current_user)


def _list(model, db, skip, limit):
    return db.scalars(select(model).order_by(model.name).offset(skip).limit(limit)).all()


def _create(model, payload, db, current_user):
    if db.scalar(select(model).where(model.code == payload.code.upper())):
        raise HTTPException(status_code=409, detail="Ce code existe déjà")
    item = model(code=payload.code.upper(), name=payload.name, description=payload.description)
    db.add(item)
    db.flush()
    log_action(db, actor_id=current_user.id, action="CREATE", entity_type=model.__name__, entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


def _update(model, item_id, payload, db, current_user):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Élément introuvable")
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"]:
        data["code"] = data["code"].upper()
    for key, value in data.items():
        setattr(item, key, value)
    log_action(db, actor_id=current_user.id, action="UPDATE", entity_type=model.__name__, entity_id=item.id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/services", response_model=list[OrganizationRead])
def list_services(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db), _: User = Reader):
    return _list(Service, db, skip, limit)


@router.post("/services", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_service(payload: OrganizationCreate, db: Session = Depends(get_db), current_user: User = Writer):
    return _create(Service, payload, db, current_user)


@router.patch("/services/{item_id}", response_model=OrganizationRead)
def update_service(item_id: int, payload: OrganizationUpdate, db: Session = Depends(get_db), current_user: User = Writer):
    return _update(Service, item_id, payload, db, current_user)


@router.get("/locations", response_model=list[OrganizationRead])
def list_locations(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db), _: User = Reader):
    return _list(Location, db, skip, limit)


@router.post("/locations", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_location(payload: OrganizationCreate, db: Session = Depends(get_db), current_user: User = Writer):
    return _create(Location, payload, db, current_user)


@router.patch("/locations/{item_id}", response_model=OrganizationRead)
def update_location(item_id: int, payload: OrganizationUpdate, db: Session = Depends(get_db), current_user: User = Writer):
    return _update(Location, item_id, payload, db, current_user)
