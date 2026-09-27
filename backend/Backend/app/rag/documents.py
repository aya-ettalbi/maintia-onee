from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    text = str(value).strip()
    return "" if text.lower() in {"none", "nan", "null"} else text


def add_line(lines: list[str], label: str, value: Any) -> None:
    text = clean(value)
    if text:
        lines.append(f"{label} : {text}")


def make_document(*, source_type: str, source_id: int | str, reference: str, title: str,
                  lines: list[str], status: Any = None, category: Any = None,
                  created_at: Any = None) -> dict:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "reference": clean(reference),
        "title": clean(title),
        "content": "\n".join(line for line in lines if line.strip()),
        "status": clean(status),
        "category": clean(category),
        "created_at": clean(created_at),
        "visibility": "technical",
    }


def historical_request_document(request, tasks: list) -> dict:
    lines = ["Type : demande historique de maintenance ONEE"]
    add_line(lines, "Numéro de demande", request.numero_demande)
    add_line(lines, "Date de création", request.date_creation_demande)
    add_line(lines, "Date de résolution", request.date_resolution_demande)
    add_line(lines, "Nature", request.nature_demande)
    add_line(lines, "Classification", request.classification)
    add_line(lines, "Détail de classification", request.detail_classification)
    add_line(lines, "Description", request.description_demande)
    add_line(lines, "Symptôme", request.symptome)
    add_line(lines, "Cause", request.cause)
    add_line(lines, "Solution", request.solution)
    add_line(lines, "Statut", request.statut)
    add_line(lines, "Groupe d'intervenants", request.groupe_intervenants)

    if tasks:
        lines.append("Tâches techniques associées :")
        for task in tasks:
            parts = []
            if clean(task.numero_tache):
                parts.append(f"Tâche {clean(task.numero_tache)}")
            if clean(task.description_tache):
                parts.append(clean(task.description_tache))
            if clean(task.classification_tache):
                parts.append(f"classification {clean(task.classification_tache)}")
            if clean(task.statut_tache):
                parts.append(f"statut {clean(task.statut_tache)}")
            if clean(task.groupe_intervenant):
                parts.append(f"groupe {clean(task.groupe_intervenant)}")
            if parts:
                lines.append("- " + " | ".join(parts))

    return make_document(
        source_type="historical_request",
        source_id=request.id,
        reference=request.numero_demande,
        title=f"Demande historique {request.numero_demande}",
        lines=lines,
        status=request.statut,
        category=request.classification,
        created_at=request.date_creation_demande,
    )


def historical_task_document(task) -> dict:
    lines = ["Type : tâche historique ONEE sans demande associée"]
    add_line(lines, "Numéro de tâche", task.numero_tache)
    add_line(lines, "Numéro de demande", task.numero_demande)
    add_line(lines, "Date de création", task.date_creation_tache)
    add_line(lines, "Date de fin", task.date_fin_tache)
    add_line(lines, "Description", task.description_tache)
    add_line(lines, "Classification", task.classification_tache)
    add_line(lines, "Détail de la demande", task.detail_demande)
    add_line(lines, "Statut", task.statut_tache)
    add_line(lines, "Groupe intervenant", task.groupe_intervenant)
    add_line(lines, "Motif de rejet", task.motif_rejet)
    return make_document(
        source_type="historical_task",
        source_id=task.id,
        reference=task.numero_tache,
        title=f"Tâche historique {task.numero_tache}",
        lines=lines,
        status=task.statut_tache,
        category=task.classification_tache,
        created_at=task.date_creation_tache,
    )


def historical_it_supply_document(item) -> dict:
    reference = item.numero_demande or f"IT-{item.id}"
    lines = ["Type : demande historique de fourniture informatique"]
    add_line(lines, "Numéro de demande", item.numero_demande)
    add_line(lines, "Date d'initiation", item.date_initiation)
    add_line(lines, "Date de traitement", item.date_traitement)
    add_line(lines, "Étape en cours", item.etape_en_cours)
    add_line(lines, "Direction", item.direction)
    add_line(lines, "Motif", item.motif_demande)
    add_line(lines, "Articles demandés", item.articles)
    return make_document(
        source_type="historical_it_supply",
        source_id=item.id,
        reference=reference,
        title=f"Fourniture informatique {reference}",
        lines=lines,
        status=item.etape_en_cours,
        category="fourniture informatique",
        created_at=item.date_initiation,
    )


def historical_office_supply_document(item) -> dict:
    reference = item.reference or item.reference_consolidee or f"BUREAU-{item.id}"
    lines = ["Type : demande historique de fourniture de bureau"]
    add_line(lines, "Référence", item.reference)
    add_line(lines, "Référence consolidée", item.reference_consolidee)
    add_line(lines, "Date d'initiation", item.date_initiation)
    add_line(lines, "Date de traitement", item.date_traitement)
    add_line(lines, "Étape en cours", item.etape_en_cours)
    add_line(lines, "Direction", item.direction)
    add_line(lines, "Code source", item.code_source)
    return make_document(
        source_type="historical_office_supply",
        source_id=item.id,
        reference=reference,
        title=f"Fourniture de bureau {reference}",
        lines=lines,
        status=item.etape_en_cours,
        category="fourniture de bureau",
        created_at=item.date_initiation,
    )


def historical_security_document(item) -> dict:
    reference = item.numero_fiche or f"HIMAYA-{item.id}"
    lines = ["Type : incident historique de sécurité Himaya"]
    add_line(lines, "Numéro de fiche", item.numero_fiche)
    add_line(lines, "Date d'initiation", item.date_initiation)
    add_line(lines, "Date de traitement", item.date_traitement)
    add_line(lines, "Date de clôture", item.date_cloture)
    add_line(lines, "Statut", item.statut)
    add_line(lines, "Étape en cours", item.etape_en_cours)
    add_line(lines, "Criticité", item.criticite)
    add_line(lines, "Description", item.description_incident)
    add_line(lines, "Cause", item.cause_incident)
    add_line(lines, "Impact", item.impact_incident)
    add_line(lines, "Action curative", item.action_curative)
    add_line(lines, "Action corrective", item.action_corrective)
    add_line(lines, "Groupe de traitement", item.groupe_traitement)
    return make_document(
        source_type="historical_security_incident",
        source_id=item.id,
        reference=reference,
        title=f"Incident Himaya {reference}",
        lines=lines,
        status=item.statut,
        category=item.criticite or "sécurité",
        created_at=item.date_initiation,
    )
