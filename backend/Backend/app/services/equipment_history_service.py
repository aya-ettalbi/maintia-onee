from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.ai_core import EquipmentHistoricalLink
from app.models.equipment import Equipment
from app.models.historical import HistoricalRequest
from app.rag.privacy import normalize_for_matching


EXACT_LINK_METHODS = {
    "CODE_ET_SERIE_EXACTS",
    "CODE_EQUIPEMENT_EXACT",
    "NUMERO_SERIE_EXACT",
}

VAGUE_HISTORY_VALUES = {
    "",
    "probleme",
    "probleme materiel",
    "probleme d impression",
    "prb",
    "prb il",
    "resolu",
    "resolution",
    "maintenance",
    "intervention",
    "aucune anomalie",
}


def _is_documented(value: object) -> bool:
    normalized = normalize_for_matching(value)

    if not normalized:
        return False

    if normalized in VAGUE_HISTORY_VALUES:
        return False

    return len(normalized.replace(" ", "")) >= 5


def _link_trust(
    link: EquipmentHistoricalLink,
) -> str:
    if link.validation_status == "VALIDE":
        return "HIGH"

    if link.link_method in EXACT_LINK_METHODS:
        return "HIGH"

    if float(link.confidence_score or 0) >= 0.85:
        return "MEDIUM"

    return "LOW"


def get_equipment_history_stats(
    equipment_code: str,
) -> dict[str, Any]:
    normalized_code = equipment_code.strip().upper()

    with SessionLocal() as db:
        equipment = db.scalar(
            select(Equipment).where(
                func.upper(Equipment.code)
                == normalized_code
            )
        )

        if equipment is None:
            return {
                "equipment_exists": False,
                "equipment_code": normalized_code,
                "linked_requests_count": 0,
                "high_confidence_links": 0,
                "medium_confidence_links": 0,
                "low_confidence_links": 0,
                "documented_causes_count": 0,
                "documented_solutions_count": 0,
                "latest_request_date": None,
                "references": [],
            }

        rows = db.execute(
            select(
                EquipmentHistoricalLink,
                HistoricalRequest,
            )
            .join(
                HistoricalRequest,
                HistoricalRequest.id
                == EquipmentHistoricalLink.historical_request_id,
            )
            .where(
                EquipmentHistoricalLink.equipment_id
                == equipment.id,
                EquipmentHistoricalLink.validation_status.in_(
                    ["AUTO", "VALIDE"]
                ),
            )
            .order_by(
                HistoricalRequest.date_creation_demande.desc(),
                HistoricalRequest.id.desc(),
            )
        ).all()

        # Une demande ne doit être comptée qu'une fois.
        unique_rows: dict[
            int,
            tuple[
                EquipmentHistoricalLink,
                HistoricalRequest,
            ],
        ] = {}

        for link, request in rows:
            current = unique_rows.get(request.id)

            if current is None:
                unique_rows[request.id] = (
                    link,
                    request,
                )
                continue

            current_link = current[0]

            if float(
                link.confidence_score or 0
            ) > float(
                current_link.confidence_score or 0
            ):
                unique_rows[request.id] = (
                    link,
                    request,
                )

        selected_rows = list(unique_rows.values())

        high_count = 0
        medium_count = 0
        low_count = 0

        documented_causes = 0
        documented_solutions = 0
        references: list[str] = []
        dates = []

        for link, request in selected_rows:
            trust = _link_trust(link)

            if trust == "HIGH":
                high_count += 1
            elif trust == "MEDIUM":
                medium_count += 1
            else:
                low_count += 1

            if _is_documented(request.cause):
                documented_causes += 1

            if _is_documented(request.solution):
                documented_solutions += 1

            if request.numero_demande:
                references.append(
                    str(request.numero_demande)
                )

            if request.date_creation_demande:
                dates.append(
                    request.date_creation_demande
                )

        latest_date = (
            max(dates).isoformat()
            if dates
            else None
        )

        return {
            "equipment_exists": True,
            "equipment_code": equipment.code,
            "equipment_brand": equipment.brand,
            "equipment_model": equipment.model,
            "linked_requests_count": len(
                selected_rows
            ),
            "high_confidence_links": high_count,
            "medium_confidence_links": medium_count,
            "low_confidence_links": low_count,
            "documented_causes_count": (
                documented_causes
            ),
            "documented_solutions_count": (
                documented_solutions
            ),
            "latest_request_date": latest_date,
            "references": references,
        }
