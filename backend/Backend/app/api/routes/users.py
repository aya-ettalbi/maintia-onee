from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.enums import Role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Message
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.audit import log_action


router = APIRouter(prefix="/users", tags=["Utilisateurs"])
Admin = Depends(require_roles(Role.ADMIN))
DirectoryReader = Depends(require_roles(Role.ADMIN, Role.MANAGER))


@router.get("", response_model=list[UserRead])
def list_users(
    q: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = DirectoryReader,
):
    stmt = select(User).order_by(User.id.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(User.first_name.ilike(like), User.last_name.ilike(like), User.email.ilike(like))
        )
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Admin,
):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="Cet email existe déjà")
    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=payload.role.value,
        service_id=payload.service_id,
    )
    db.add(user)
    db.flush()
    log_action(db, actor_id=current_user.id, action="CREATE", entity_type="User", entity_id=user.id)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = DirectoryReader):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Admin,
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    data = payload.model_dump(exclude_unset=True)
    if "role" in data:
        data["role"] = data["role"].value
    if "status" in data:
        data["status"] = data["status"].value
    password = data.pop("password", None)
    if password:
        user.hashed_password = hash_password(password)
    for key, value in data.items():
        setattr(user, key, value)
    log_action(db, actor_id=current_user.id, action="UPDATE", entity_type="User", entity_id=user.id)
    db.commit()
    db.refresh(user)
    return user
