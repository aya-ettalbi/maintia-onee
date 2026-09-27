from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import Role
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Message
from app.schemas.maintenance import (
    InterventionActionRead,
    InterventionPartRead,
    InterventionRead,
)
from app.schemas.phase2_interventions import (
    InterventionActionUpdate,
    InterventionCancelRequest,
    InterventionCloseRequest,
    InterventionPartUpdate,
    StockAlertsResponse,
    StockSummaryResponse,
)
from app.services.audit import log_action
from app.services.phase2_interventions import (
    cancel_intervention,
    close_intervention,
    ensure_intervention_access,
    ensure_intervention_editable,
    get_action,
    get_locked_intervention,
    get_locked_intervention_part,
    remove_intervention_part,
    stock_alerts,
    stock_summary,
    update_part_quantity,
)


router = APIRouter(tags=["Phase 2 - Interventions et Stock"])


@router.patch(
    "/interventions/{intervention_id}/actions/{action_id}",
    response_model=InterventionActionRead,
)
def update_intervention_action(
    intervention_id: int,
    action_id: int,
    payload: InterventionActionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)
    ),
):
    intervention = get_locked_intervention(db, intervention_id)
    ensure_intervention_access(intervention, current_user)
    ensure_intervention_editable(intervention)

    action = get_action(db, intervention_id, action_id)
    old_description = action.description
    action.description = payload.description.strip()

    log_action(
        db,
        actor_id=current_user.id,
        action="UPDATE_ACTION",
        entity_type="Intervention",
        entity_id=intervention.id,
        details={
            "action_id": action.id,
            "old_description": old_description,
            "new_description": action.description,
        },
    )
    db.commit()
    db.refresh(action)
    return action


@router.delete(
    "/interventions/{intervention_id}/actions/{action_id}",
    response_model=Message,
)
def delete_intervention_action(
    intervention_id: int,
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)
    ),
):
    intervention = get_locked_intervention(db, intervention_id)
    ensure_intervention_access(intervention, current_user)
    ensure_intervention_editable(intervention)

    action = get_action(db, intervention_id, action_id)
    details = {
        "action_id": action.id,
        "description": action.description,
    }
    db.delete(action)

    log_action(
        db,
        actor_id=current_user.id,
        action="DELETE_ACTION",
        entity_type="Intervention",
        entity_id=intervention.id,
        details=details,
    )
    db.commit()
    return Message(message="Action supprimee avec succes")


@router.patch(
    "/interventions/{intervention_id}/parts/{link_id}",
    response_model=InterventionPartRead,
)
def update_intervention_part(
    intervention_id: int,
    link_id: int,
    payload: InterventionPartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            Role.ADMIN,
            Role.MANAGER,
            Role.TECHNICIAN,
            Role.STOCK_MANAGER,
        )
    ),
):
    intervention = get_locked_intervention(db, intervention_id)
    ensure_intervention_access(
        intervention,
        current_user,
        allow_stock_manager=True,
    )
    ensure_intervention_editable(intervention)

    link = get_locked_intervention_part(
        db,
        intervention_id,
        link_id,
    )
    link = update_part_quantity(
        db,
        intervention=intervention,
        link=link,
        new_quantity=payload.quantity,
        current_user=current_user,
    )
    db.commit()
    db.refresh(link)
    return link


@router.delete(
    "/interventions/{intervention_id}/parts/{link_id}",
    response_model=Message,
)
def delete_intervention_part(
    intervention_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            Role.ADMIN,
            Role.MANAGER,
            Role.TECHNICIAN,
            Role.STOCK_MANAGER,
        )
    ),
):
    intervention = get_locked_intervention(db, intervention_id)
    ensure_intervention_access(
        intervention,
        current_user,
        allow_stock_manager=True,
    )
    ensure_intervention_editable(intervention)

    link = get_locked_intervention_part(
        db,
        intervention_id,
        link_id,
    )
    remove_intervention_part(
        db,
        intervention=intervention,
        link=link,
        current_user=current_user,
    )
    db.commit()
    return Message(
        message="Piece retiree et restituee au stock avec succes"
    )


@router.post(
    "/interventions/{intervention_id}/close",
    response_model=InterventionRead,
)
def close_intervention_endpoint(
    intervention_id: int,
    payload: InterventionCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)
    ),
):
    intervention = get_locked_intervention(db, intervention_id)
    ensure_intervention_access(intervention, current_user)

    intervention = close_intervention(
        db,
        intervention=intervention,
        diagnosis=payload.diagnosis,
        solution=payload.solution,
        test_result=payload.test_result,
        comment=payload.comment,
        current_user=current_user,
    )
    db.commit()
    db.refresh(intervention)
    return intervention


@router.post(
    "/interventions/{intervention_id}/cancel",
    response_model=InterventionRead,
)
def cancel_intervention_endpoint(
    intervention_id: int,
    payload: InterventionCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER, Role.TECHNICIAN)
    ),
):
    intervention = get_locked_intervention(db, intervention_id)
    ensure_intervention_access(intervention, current_user)

    intervention = cancel_intervention(
        db,
        intervention=intervention,
        reason=payload.reason,
        current_user=current_user,
    )
    db.commit()
    db.refresh(intervention)
    return intervention


@router.get(
    "/stock/summary",
    response_model=StockSummaryResponse,
)
def stock_summary_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return stock_summary(db)


@router.get(
    "/stock/alerts",
    response_model=StockAlertsResponse,
)
def stock_alerts_endpoint(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return stock_alerts(db, limit=limit)
