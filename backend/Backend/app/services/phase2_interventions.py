from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    EquipmentStatus,
    InterventionStatus,
    RequestStatus,
    Role,
    StockMovementType,
)
from app.models.equipment import Equipment
from app.models.maintenance import (
    Intervention,
    InterventionAction,
    InterventionStatusHistory,
    MaintenanceRequest,
)
from app.models.stock import InterventionPart, SparePart, StockMovement
from app.models.user import User
from app.schemas.phase2_interventions import (
    StockAlertItem,
    StockAlertsResponse,
    StockSummaryResponse,
)
from app.services.audit import create_notification, log_action


TERMINAL_INTERVENTION_STATUSES = {
    InterventionStatus.COMPLETED.value,
    InterventionStatus.CANCELLED.value,
}


def ensure_intervention_access(
    intervention: Intervention,
    current_user: User,
    *,
    allow_stock_manager: bool = False,
) -> None:
    allowed_roles = {
        Role.ADMIN.value,
        Role.MANAGER.value,
        Role.TECHNICIAN.value,
    }
    if allow_stock_manager:
        allowed_roles.add(Role.STOCK_MANAGER.value)

    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    if (
        current_user.role == Role.TECHNICIAN.value
        and intervention.technician_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Cette intervention ne vous est pas affectee",
        )


def ensure_intervention_editable(intervention: Intervention) -> None:
    if intervention.status in TERMINAL_INTERVENTION_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=(
                "Une intervention terminee ou annulee "
                "ne peut plus etre modifiee"
            ),
        )


def get_locked_intervention(
    db: Session,
    intervention_id: int,
) -> Intervention:
    intervention = db.scalar(
        select(Intervention)
        .where(Intervention.id == intervention_id)
        .with_for_update()
    )
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervention introuvable")
    return intervention


def get_action(
    db: Session,
    intervention_id: int,
    action_id: int,
) -> InterventionAction:
    action = db.scalar(
        select(InterventionAction).where(
            InterventionAction.id == action_id,
            InterventionAction.intervention_id == intervention_id,
        )
    )
    if action is None:
        raise HTTPException(status_code=404, detail="Action introuvable")
    return action


def get_locked_intervention_part(
    db: Session,
    intervention_id: int,
    link_id: int,
) -> InterventionPart:
    link = db.scalar(
        select(InterventionPart)
        .where(
            InterventionPart.id == link_id,
            InterventionPart.intervention_id == intervention_id,
        )
        .with_for_update()
    )
    if link is None:
        raise HTTPException(
            status_code=404,
            detail="Piece d'intervention introuvable",
        )
    return link


def get_locked_spare_part(db: Session, part_id: int) -> SparePart:
    part = db.scalar(
        select(SparePart)
        .where(SparePart.id == part_id)
        .with_for_update()
    )
    if part is None:
        raise HTTPException(status_code=404, detail="Piece introuvable")
    return part


def add_stock_movement(
    db: Session,
    *,
    part: SparePart,
    movement_type: str,
    quantity: int,
    unit_cost: Decimal,
    intervention_id: int,
    current_user: User,
    reason: str,
) -> None:
    db.add(
        StockMovement(
            part_id=part.id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            intervention_id=intervention_id,
            performed_by_id=current_user.id,
            reason=reason,
        )
    )


def adjust_intervention_cost(
    intervention: Intervention,
    amount: Decimal,
) -> None:
    current = Decimal(intervention.actual_cost or 0)
    intervention.actual_cost = max(Decimal("0"), current + amount)


def update_part_quantity(
    db: Session,
    *,
    intervention: Intervention,
    link: InterventionPart,
    new_quantity: int,
    current_user: User,
) -> InterventionPart:
    old_quantity = int(link.quantity)
    delta = new_quantity - old_quantity

    if delta == 0:
        return link

    part = get_locked_spare_part(db, link.part_id)
    unit_price = Decimal(link.unit_price or 0)

    if delta > 0:
        if not part.active:
            raise HTTPException(status_code=409, detail="La piece est inactive")
        if part.quantity < delta:
            raise HTTPException(status_code=409, detail="Stock insuffisant")

        part.quantity -= delta
        add_stock_movement(
            db,
            part=part,
            movement_type=StockMovementType.OUT.value,
            quantity=delta,
            unit_cost=unit_price,
            intervention_id=intervention.id,
            current_user=current_user,
            reason="Augmentation de la quantite utilisee",
        )
    else:
        returned_quantity = abs(delta)
        part.quantity += returned_quantity
        add_stock_movement(
            db,
            part=part,
            movement_type=StockMovementType.RETURN.value,
            quantity=returned_quantity,
            unit_cost=unit_price,
            intervention_id=intervention.id,
            current_user=current_user,
            reason="Restitution apres reduction de la quantite",
        )

    link.quantity = new_quantity
    adjust_intervention_cost(
        intervention,
        Decimal(delta) * unit_price,
    )
    log_action(
        db,
        actor_id=current_user.id,
        action="UPDATE_PART_QUANTITY",
        entity_type="Intervention",
        entity_id=intervention.id,
        details={
            "part_id": part.id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "delta": delta,
        },
    )
    return link


def remove_intervention_part(
    db: Session,
    *,
    intervention: Intervention,
    link: InterventionPart,
    current_user: User,
) -> None:
    part = get_locked_spare_part(db, link.part_id)
    quantity = int(link.quantity)
    unit_price = Decimal(link.unit_price or 0)

    part.quantity += quantity
    add_stock_movement(
        db,
        part=part,
        movement_type=StockMovementType.RETURN.value,
        quantity=quantity,
        unit_cost=unit_price,
        intervention_id=intervention.id,
        current_user=current_user,
        reason="Restitution apres retrait d'une piece",
    )
    adjust_intervention_cost(
        intervention,
        -(Decimal(quantity) * unit_price),
    )
    log_action(
        db,
        actor_id=current_user.id,
        action="REMOVE_PART",
        entity_type="Intervention",
        entity_id=intervention.id,
        details={"part_id": part.id, "quantity": quantity},
    )
    db.delete(link)


def close_intervention(
    db: Session,
    *,
    intervention: Intervention,
    diagnosis: str,
    solution: str,
    test_result: str,
    comment: str | None,
    current_user: User,
) -> Intervention:
    ensure_intervention_editable(intervention)

    if intervention.started_at is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "L'intervention doit etre demarree avant sa cloture. "
                "Passez d'abord au statut DIAGNOSING ou REPAIRING."
            ),
        )

    now = datetime.now(timezone.utc)
    old_status = intervention.status

    intervention.diagnosis = diagnosis.strip()
    intervention.solution = solution.strip()
    intervention.test_result = test_result.strip()
    intervention.status = InterventionStatus.COMPLETED.value
    intervention.ended_at = now
    intervention.closed_by_id = current_user.id

    equipment = db.get(Equipment, intervention.equipment_id)
    if equipment is not None:
        equipment.status = EquipmentStatus.IN_SERVICE.value

    request = None
    if intervention.request_id is not None:
        request = db.get(MaintenanceRequest, intervention.request_id)

    if request is not None:
        terminal_request_statuses = {
            RequestStatus.CLOSED.value,
            RequestStatus.CANCELLED.value,
            RequestStatus.REJECTED.value,
        }
        if request.status not in terminal_request_statuses:
            request.status = RequestStatus.RESOLVED.value
            request.closed_at = now

        create_notification(
            db,
            user_id=request.requester_id,
            title="Intervention terminee",
            message=(
                f"L'intervention {intervention.reference} est terminee. "
                f"La demande {request.reference} est resolue."
            ),
        )

    db.add(
        InterventionStatusHistory(
            intervention_id=intervention.id,
            old_status=old_status,
            new_status=InterventionStatus.COMPLETED.value,
            changed_by_id=current_user.id,
            comment=comment,
        )
    )
    log_action(
        db,
        actor_id=current_user.id,
        action="CLOSE",
        entity_type="Intervention",
        entity_id=intervention.id,
        details={
            "old_status": old_status,
            "new_status": InterventionStatus.COMPLETED.value,
            "request_id": intervention.request_id,
        },
    )
    return intervention


def cancel_intervention(
    db: Session,
    *,
    intervention: Intervention,
    reason: str,
    current_user: User,
) -> Intervention:
    ensure_intervention_editable(intervention)

    now = datetime.now(timezone.utc)
    old_status = intervention.status
    links = db.scalars(
        select(InterventionPart)
        .where(InterventionPart.intervention_id == intervention.id)
        .with_for_update()
    ).all()

    returned_value = Decimal("0")
    returned_parts: list[dict[str, int]] = []

    for link in links:
        part = get_locked_spare_part(db, link.part_id)
        quantity = int(link.quantity)
        unit_price = Decimal(link.unit_price or 0)

        part.quantity += quantity
        returned_value += Decimal(quantity) * unit_price
        returned_parts.append({"part_id": part.id, "quantity": quantity})
        add_stock_movement(
            db,
            part=part,
            movement_type=StockMovementType.RETURN.value,
            quantity=quantity,
            unit_cost=unit_price,
            intervention_id=intervention.id,
            current_user=current_user,
            reason="Restitution automatique apres annulation",
        )
        db.delete(link)

    adjust_intervention_cost(intervention, -returned_value)
    intervention.status = InterventionStatus.CANCELLED.value
    intervention.ended_at = now
    intervention.closed_by_id = current_user.id

    equipment = db.get(Equipment, intervention.equipment_id)
    if equipment is not None:
        equipment.status = EquipmentStatus.IN_SERVICE.value

    request = None
    if intervention.request_id is not None:
        request = db.get(MaintenanceRequest, intervention.request_id)

    if request is not None:
        request.status = (
            RequestStatus.ASSIGNED.value
            if request.assigned_technician_id is not None
            else RequestStatus.VALIDATED.value
        )
        request.closed_at = None
        create_notification(
            db,
            user_id=request.requester_id,
            title="Intervention annulee",
            message=(
                f"L'intervention {intervention.reference} a ete annulee. "
                f"La demande {request.reference} reste ouverte."
            ),
        )

    db.add(
        InterventionStatusHistory(
            intervention_id=intervention.id,
            old_status=old_status,
            new_status=InterventionStatus.CANCELLED.value,
            changed_by_id=current_user.id,
            comment=reason.strip(),
        )
    )
    log_action(
        db,
        actor_id=current_user.id,
        action="CANCEL",
        entity_type="Intervention",
        entity_id=intervention.id,
        details={
            "old_status": old_status,
            "reason": reason.strip(),
            "returned_parts": returned_parts,
            "returned_value": str(returned_value),
        },
    )
    return intervention


def stock_summary(db: Session) -> StockSummaryResponse:
    total_parts = int(
        db.scalar(select(func.count()).select_from(SparePart)) or 0
    )
    active_parts = int(
        db.scalar(
            select(func.count())
            .select_from(SparePart)
            .where(SparePart.active.is_(True))
        )
        or 0
    )
    total_quantity = int(
        db.scalar(
            select(func.coalesce(func.sum(SparePart.quantity), 0))
            .where(SparePart.active.is_(True))
        )
        or 0
    )
    low_stock_parts = int(
        db.scalar(
            select(func.count())
            .select_from(SparePart)
            .where(
                SparePart.active.is_(True),
                SparePart.quantity <= SparePart.minimum_threshold,
            )
        )
        or 0
    )
    out_of_stock_parts = int(
        db.scalar(
            select(func.count())
            .select_from(SparePart)
            .where(
                SparePart.active.is_(True),
                SparePart.quantity <= 0,
            )
        )
        or 0
    )
    inventory_value = Decimal(
        db.scalar(
            select(
                func.coalesce(
                    func.sum(SparePart.quantity * SparePart.unit_price),
                    0,
                )
            ).where(SparePart.active.is_(True))
        )
        or 0
    )

    return StockSummaryResponse(
        total_parts=total_parts,
        active_parts=active_parts,
        total_quantity=total_quantity,
        low_stock_parts=low_stock_parts,
        out_of_stock_parts=out_of_stock_parts,
        inventory_value=inventory_value,
    )


def stock_alerts(db: Session, *, limit: int) -> StockAlertsResponse:
    parts = db.scalars(
        select(SparePart)
        .where(
            SparePart.active.is_(True),
            SparePart.quantity <= SparePart.minimum_threshold,
        )
        .order_by(
            SparePart.quantity.asc(),
            SparePart.minimum_threshold.desc(),
            SparePart.name.asc(),
        )
        .limit(limit)
    ).all()

    items: list[StockAlertItem] = []
    for part in parts:
        threshold = int(part.minimum_threshold)
        quantity = int(part.quantity)
        shortage = max(0, threshold - quantity)
        suggested_order_quantity = max(0, threshold * 2 - quantity)

        if quantity <= 0:
            risk = "CRITICAL"
        elif threshold > 0 and quantity <= threshold / 2:
            risk = "HIGH"
        else:
            risk = "MEDIUM"

        items.append(
            StockAlertItem(
                part_id=part.id,
                code=part.code,
                name=part.name,
                quantity=quantity,
                minimum_threshold=threshold,
                shortage=shortage,
                suggested_order_quantity=suggested_order_quantity,
                risk=risk,
            )
        )

    return StockAlertsResponse(total=len(items), items=items)
