from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.enums import Role
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead


router = APIRouter(prefix="/audit-logs", tags=["Audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    entity_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    return db.scalars(stmt.offset(skip).limit(limit)).all()
