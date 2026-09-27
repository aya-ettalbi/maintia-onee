from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterator, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_core import EquipmentHistoricalLink
from app.models.equipment import Equipment
from app.models.historical import HistoricalRequest, HistoricalTask
from app.rag.onee_indexer import RagDocument, make_point_id
from app.rag.privacy import anonymize_text
from app.rag.query_understanding import infer_classification_group


EXACT_LINK_METHODS = {
    "CODE_ET_SERIE_EXACTS",
    "CODE_EQUIPEMENT_EXACT",
    "NUMERO_SERIE_EXACT",
}


@dataclass(frozen=True)
class LinkedEquipment:
    equipment: Equipment
    link_method: str
    link_confidence: float
    link_trust: str


def load_tasks_by_request(
    db: Session,
) -> dict[str, list[HistoricalTask]]:
    grouped: dict[str, list[HistoricalTask]] = defaultdict(list)

    tasks = db.scalars(
        select(HistoricalTask).order_by(
            HistoricalTask.numero_demande,
            HistoricalTask.date_creation_tache,
            HistoricalTask.id,
        )
    ).all()

    for task in tasks:
        if task.numero_demande:
            grouped[task.numero_demande].append(task)

    return grouped


def load_linked_equipment(
    db: Session,
) -> dict[int, LinkedEquipment]:
    rows = db.execute(
        select(
            EquipmentHistoricalLink,
            Equipment,
        )
        .join(
            Equipment,
            Equipment.id == EquipmentHistoricalLink.equipment_id,
        )
        .where(
            EquipmentHistoricalLink.validation_status.in_(
                ["AUTO", "VALIDE"]
            )
        )
        .order_by(
            EquipmentHistoricalLink.historical_request_id,
            EquipmentHistoricalLink.confidence_score.desc(),
        )
    ).all()

    result: dict[int, LinkedEquipment] = {}

    for link, equipment in rows:
        if link.historical_request_id in result:
            continue

        if link.validation_status == "VALIDE":
            trust = "HIGH"
        elif link.link_method in EXACT_LINK_METHODS:
            trust = "HIGH"
        elif link.confidence_score >= 0.85:
            trust = "MEDIUM"
        else:
            trust = "LOW"

        result[link.historical_request_id] = LinkedEquipment(
            equipment=equipment,
            link_method=link.link_method,
            link_confidence=float(link.confidence_score),
            link_trust=trust,
        )

    return result


def build_tasks_text(
    tasks: Sequence[HistoricalTask],
) -> str:
    lines: list[str] = []

    for index, task in enumerate(tasks[:15], start=1):
        description = anonymize_text(task.description_tache)
        classification = anonymize_text(
            task.classification_tache
        )
        rejection = anonymize_text(task.motif_rejet)

        details = " | ".join(
            value
            for value in (
                description,
                classification,
                rejection,
            )
            if value
        )

        if details:
            lines.append(f"Tâche {index}: {details}")

    if len(tasks) > 15:
        lines.append(
            f"{len(tasks) - 15} tâche(s) supplémentaire(s)."
        )

    return "\n".join(lines)


def build_secure_request_document(
    request: HistoricalRequest,
    tasks: Sequence[HistoricalTask],
    linked: LinkedEquipment | None,
) -> RagDocument:
    description = anonymize_text(
        request.description_demande
    )
    symptom = anonymize_text(request.symptome)
    cause = anonymize_text(request.cause)
    solution = anonymize_text(request.solution)
    classification = anonymize_text(
        request.classification
    )
    detail_classification = anonymize_text(
        request.detail_classification
    )
    nature = anonymize_text(request.nature_demande)
    status = anonymize_text(request.statut)

    classification_source = " ".join(
        value
        for value in (
            classification,
            detail_classification,
            description,
            symptom,
        )
        if value
    )
    classification_group = (
        infer_classification_group(
            classification_source.lower()
        )
        or "AUTRE"
    )

    lines = [
        "Type de source: demande historique de maintenance",
        f"Référence demande: {request.numero_demande}",
    ]

    if request.date_creation_demande:
        lines.append(
            "Date de création: "
            f"{request.date_creation_demande.date().isoformat()}"
        )

    for label, value in (
        ("Nature", nature),
        ("Classification", classification),
        ("Détail classification", detail_classification),
        ("Description", description),
        ("Symptôme", symptom),
        ("Cause", cause),
        ("Solution", solution),
        ("Statut", status),
    ):
        if value:
            lines.append(f"{label}: {value}")

    equipment = linked.equipment if linked else None

    if equipment is not None:
        lines.extend(
            [
                f"Équipement code: {equipment.code}",
                f"Équipement marque: {equipment.brand or ''}",
                f"Équipement modèle: {equipment.model or ''}",
                f"Fiabilité du lien équipement: {linked.link_trust}",
            ]
        )

    tasks_text = build_tasks_text(tasks)
    if tasks_text:
        lines.append("Actions et tâches historiques:")
        lines.append(tasks_text)

    content = "\n".join(
        line
        for line in lines
        if line.strip()
    )

    payload = {
        "source_type": "historical_request",
        "source_id": str(request.id),
        "reference": request.numero_demande,
        "numero_demande": request.numero_demande,
        "classification": classification or None,
        "classification_group": classification_group,
        "detail_classification": detail_classification or None,
        "nature_demande": nature or None,
        "statut": status or None,
        "cause": cause or None,
        "solution": solution or None,
        "symptome": symptom or None,
        "created_at": (
            request.date_creation_demande.isoformat()
            if request.date_creation_demande
            else None
        ),
        "equipment_id": equipment.id if equipment else None,
        "equipment_code": equipment.code if equipment else None,
        "equipment_brand": equipment.brand if equipment else None,
        "equipment_model": equipment.model if equipment else None,
        "link_method": linked.link_method if linked else None,
        "link_confidence": (
            linked.link_confidence if linked else None
        ),
        "link_trust": linked.link_trust if linked else None,
        "task_count": len(tasks),
        "content": content,
        "privacy_version": "v2",
    }

    return RagDocument(
        point_id=make_point_id(
            "historical_request",
            str(request.id),
        ),
        text=content,
        payload=payload,
    )


def iter_secure_request_documents(
    db: Session,
) -> Iterator[RagDocument]:
    tasks_by_request = load_tasks_by_request(db)
    linked_by_request = load_linked_equipment(db)

    requests = db.scalars(
        select(HistoricalRequest).order_by(
            HistoricalRequest.id
        )
    ).all()

    for request in requests:
        yield build_secure_request_document(
            request=request,
            tasks=tasks_by_request.get(
                request.numero_demande,
                [],
            ),
            linked=linked_by_request.get(request.id),
        )
