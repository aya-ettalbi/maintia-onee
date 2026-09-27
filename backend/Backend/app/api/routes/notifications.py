from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.audit import Notification
from app.models.user import User
from app.schemas.audit import NotificationRead
from app.schemas.common import Message


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.id.desc())
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.post("/{notification_id}/read", response_model=Message)
def mark_as_read(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.get(Notification, notification_id)
    if item is None or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    item.read_at = datetime.now(timezone.utc)
    db.commit()
    return Message(message="Notification marquée comme lue")
