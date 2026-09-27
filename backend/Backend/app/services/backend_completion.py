from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import StockMovementType
from app.models.equipment import Equipment
from app.models.historical import HistoricalRequest
from app.models.maintenance import Intervention, MaintenanceRequest
from app.models.stock import InterventionPart, SparePart, StockMovement
from app.schemas.backend_completion import (
    RecurrentFailureItem,
    RecurrentFailuresResponse,
    RiskAssessmentResponse,
    StockShortageRiskItem,
    StockShortageRisksResponse,
    TriageResponse,
)


def _normalize(value: str) -> str:
    value = value.lower().strip()
    value = (
        value.replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("â", "a")
        .replace("î", "i")
        .replace("ï", "i")
        .replace("ô", "o")
        .replace("ù", "u")
        .replace("û", "u")
        .replace("ç", "c")
    )
    return re.sub(r"\s+", " ", value)


TRIAGE_RULES: tuple[dict[str, Any], ...] = (
    {
        "incident_type": "ACCOUNT",
        "classification_group": "COMPTE",
        "keywords": (
            "mot de passe", "password", "compte bloque", "deblocage compte",
            "sap", "solman", "isu", "connexion compte",
        ),
    },
    {
        "incident_type": "NETWORK",
        "classification_group": "RESEAU",
        "keywords": (
            "reseau", "internet", "connexion", "wifi", "ethernet",
            "prise reseau", "adresse ip", "vpn",
        ),
    },
    {
        "incident_type": "PERIPHERAL",
        "classification_group": "IMPRIMANTE",
        "keywords": (
            "imprimante", "impression", "bourrage", "toner", "cartouche", "scanner",
        ),
    },
    {
        "incident_type": "PERIPHERAL",
        "classification_group": "PERIPHERIQUE",
        "keywords": (
            "souris", "clavier", "ecran", "moniteur", "usb", "peripherique",
        ),
    },
    {
        "incident_type": "SOFTWARE",
        "classification_group": "LOGICIEL",
        "keywords": (
            "windows", "office", "outlook", "messagerie", "application",
            "logiciel", "installation", "mise a jour",
        ),
    },
    {
        "incident_type": "HARDWARE_MAIN",
        "classification_group": "UC",
        "keywords": (
            "ordinateur", "pc", "unite centrale", "demarrage", "ecran noir",
            "bip", "ram", "disque dur", "carte mere", "alimentation",
        ),
    },
    {
        "incident_type": "SECURITY",
        "classification_group": "SECURITE",
        "keywords": (
            "virus", "malware", "phishing", "piratage", "incident securite", "ransomware",
        ),
    },
)

CRITICAL_KEYWORDS = (
    "incendie", "fumee", "odeur de brule", "court circuit", "ransomware",
    "serveur arrete", "service indisponible", "perte de donnees",
)

HIGH_KEYWORDS = (
    "ne demarre plus", "ecran noir", "plusieurs utilisateurs", "bloquant",
    "urgent", "critique", "bourrage recurrent", "bips", "bip",
)


def triage_request(
    db: Session,
    description: str,
    equipment_code: str | None = None,
) -> TriageResponse:
    normalized = _normalize(description)
    rule_scores: list[tuple[int, dict[str, Any], list[str]]] = []

    for rule in TRIAGE_RULES:
        matches = [keyword for keyword in rule["keywords"] if keyword in normalized]
        rule_scores.append((len(matches), rule, matches))

    rule_scores.sort(key=lambda item: item[0], reverse=True)
    best_score, best_rule, matches = rule_scores[0]

    if best_score == 0:
        incident_type = "OTHER"
        classification_group = "AUTRE"
        confidence_score = 35
        matched_rules: list[str] = []
    else:
        incident_type = str(best_rule["incident_type"])
        classification_group = str(best_rule["classification_group"])
        confidence_score = min(95, 45 + best_score * 15)
        matched_rules = matches

    equipment = None
    normalized_code = equipment_code.strip().upper() if equipment_code else None

    if normalized_code:
        equipment = db.scalar(select(Equipment).where(Equipment.code == normalized_code))
        if equipment is not None:
            confidence_score = min(98, confidence_score + 5)
            matched_rules.append("equipment_code_found")
        else:
            matched_rules.append("equipment_code_not_found")

    if any(keyword in normalized for keyword in CRITICAL_KEYWORDS):
        priority = "CRITICAL"
        matched_rules.append("critical_keyword")
    elif any(keyword in normalized for keyword in HIGH_KEYWORDS):
        priority = "HIGH"
        matched_rules.append("high_keyword")
    elif incident_type in {"HARDWARE_MAIN", "NETWORK", "SECURITY"}:
        priority = "HIGH"
    elif incident_type in {"PERIPHERAL", "SOFTWARE", "ACCOUNT"}:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    if confidence_score >= 80:
        confidence = "HIGH"
    elif confidence_score >= 50:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    suggested_team = (
        "SECURITY_TEAM" if incident_type == "SECURITY"
        else "NETWORK_TEAM" if incident_type == "NETWORK"
        else "TECHNICIAN"
    )

    return TriageResponse(
        incident_type=incident_type,
        classification_group=classification_group,
        suggested_priority=priority,
        suggested_team=suggested_team,
        confidence=confidence,
        confidence_score=confidence_score,
        matched_rules=matched_rules,
        equipment_code=equipment.code if equipment else normalized_code,
        human_validation_required=True,
    )


def _years_since(value: date | None) -> float | None:
    if value is None:
        return None
    days = (date.today() - value).days
    return round(max(days, 0) / 365.25, 2)


def _risk_level(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def _recommended_action(level: str) -> str:
    return {
        "CRITICAL": (
            "Planifier immédiatement un diagnostic approfondi et étudier "
            "le remplacement ou la réforme de l'équipement."
        ),
        "HIGH": (
            "Planifier une maintenance préventive prioritaire et contrôler "
            "les composants les plus fréquemment concernés."
        ),
        "MEDIUM": "Renforcer la surveillance et programmer un contrôle préventif.",
        "LOW": "Maintenir le suivi normal et poursuivre la maintenance planifiée.",
    }[level]


def equipment_risk_assessment(db: Session, equipment_id: int) -> RiskAssessmentResponse:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Équipement introuvable")

    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=365)

    request_count = int(
        db.scalar(
            select(func.count()).select_from(MaintenanceRequest).where(
                MaintenanceRequest.equipment_id == equipment_id
            )
        ) or 0
    )
    recent_request_count = int(
        db.scalar(
            select(func.count()).select_from(MaintenanceRequest).where(
                MaintenanceRequest.equipment_id == equipment_id,
                MaintenanceRequest.submitted_at >= recent_cutoff,
            )
        ) or 0
    )
    intervention_count = int(
        db.scalar(
            select(func.count()).select_from(Intervention).where(
                Intervention.equipment_id == equipment_id
            )
        ) or 0
    )

    interventions = db.scalars(
        select(Intervention).where(Intervention.equipment_id == equipment_id)
    ).all()

    repair_hours = [
        (item.ended_at - item.started_at).total_seconds() / 3600
        for item in interventions
        if item.started_at and item.ended_at
    ]
    average_repair_hours = round(sum(repair_hours) / len(repair_hours), 2) if repair_hours else 0.0
    total_cost = float(
        sum((Decimal(item.actual_cost or 0) for item in interventions), Decimal("0"))
    )
    parts_used = int(
        db.scalar(
            select(func.coalesce(func.sum(InterventionPart.quantity), 0))
            .select_from(InterventionPart)
            .join(Intervention, Intervention.id == InterventionPart.intervention_id)
            .where(Intervention.equipment_id == equipment_id)
        ) or 0
    )

    historical_link_count = 0
    try:
        from app.models.ai_core import EquipmentHistoricalLink

        historical_link_count = int(
            db.scalar(
                select(func.count()).select_from(EquipmentHistoricalLink).where(
                    EquipmentHistoricalLink.equipment_id == equipment_id
                )
            ) or 0
        )
    except (ImportError, AttributeError):
        historical_link_count = 0

    age_years = _years_since(equipment.commissioning_date or equipment.acquisition_date)

    score = 0
    factors: list[str] = []

    if age_years is not None:
        if age_years >= 7:
            score += 20
            factors.append(f"Équipement ancien : {age_years} ans")
        elif age_years >= 5:
            score += 12
            factors.append(f"Âge significatif : {age_years} ans")
        elif age_years >= 3:
            score += 6
            factors.append(f"Âge à surveiller : {age_years} ans")

    if recent_request_count >= 5:
        score += 25
        factors.append(f"{recent_request_count} demandes sur les 12 derniers mois")
    elif recent_request_count >= 3:
        score += 15
        factors.append(f"{recent_request_count} demandes récentes")
    elif recent_request_count >= 1:
        score += 5

    if intervention_count >= 10:
        score += 15
        factors.append(f"{intervention_count} interventions enregistrées")
    elif intervention_count >= 5:
        score += 10
        factors.append(f"{intervention_count} interventions enregistrées")
    elif intervention_count >= 2:
        score += 5

    if average_repair_hours >= 24:
        score += 15
        factors.append(f"MTTR équipement élevé : {average_repair_hours} h")
    elif average_repair_hours >= 8:
        score += 8
        factors.append(f"Temps moyen de réparation : {average_repair_hours} h")

    if total_cost >= 10000:
        score += 12
        factors.append("Coût cumulé de maintenance très élevé")
    elif total_cost >= 5000:
        score += 8
        factors.append("Coût cumulé de maintenance élevé")
    elif total_cost >= 1000:
        score += 4

    if parts_used >= 10:
        score += 8
        factors.append(f"{parts_used} pièces consommées")
    elif parts_used >= 4:
        score += 4

    if historical_link_count >= 10:
        score += 10
        factors.append(f"{historical_link_count} demandes historiques liées")
    elif historical_link_count >= 5:
        score += 6
        factors.append(f"{historical_link_count} demandes historiques liées")

    if equipment.archived or equipment.status in {"OUT_OF_SERVICE", "REFORMED", "IN_FAILURE"}:
        score += 15
        factors.append(f"État actuel défavorable : {equipment.status}")

    score = max(0, min(100, int(round(score))))
    level = _risk_level(score)

    if not factors:
        factors.append("Aucun facteur de risque important détecté dans les données disponibles")

    return RiskAssessmentResponse(
        equipment_id=equipment.id,
        equipment_code=equipment.code,
        score=score,
        level=level,
        factors=factors,
        recommended_action=_recommended_action(level),
        calculation_version="rules-v2",
        metrics={
            "age_years": age_years,
            "request_count": request_count,
            "recent_request_count": recent_request_count,
            "intervention_count": intervention_count,
            "average_repair_hours": average_repair_hours,
            "total_cost": round(total_cost, 2),
            "parts_used": parts_used,
            "historical_link_count": historical_link_count,
            "equipment_status": equipment.status,
            "archived": str(bool(equipment.archived)).lower(),
        },
        calculated_at=now,
    )


def recurrent_failures(
    db: Session,
    period_months: int = 24,
    minimum_occurrences: int = 3,
    limit: int = 50,
) -> RecurrentFailuresResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_months * 30)

    rows = db.execute(
        select(
            HistoricalRequest.classification,
            func.count(HistoricalRequest.id).label("occurrence_count"),
            func.max(HistoricalRequest.date_creation_demande).label("latest_date"),
        )
        .where(
            HistoricalRequest.classification.is_not(None),
            func.length(func.trim(HistoricalRequest.classification)) > 0,
            HistoricalRequest.date_creation_demande >= cutoff,
        )
        .group_by(HistoricalRequest.classification)
        .having(func.count(HistoricalRequest.id) >= minimum_occurrences)
        .order_by(func.count(HistoricalRequest.id).desc())
        .limit(limit)
    ).all()

    items = [
        RecurrentFailureItem(
            classification=str(row.classification),
            occurrence_count=int(row.occurrence_count),
            latest_date=row.latest_date,
        )
        for row in rows
    ]

    return RecurrentFailuresResponse(
        period_months=period_months,
        minimum_occurrences=minimum_occurrences,
        total_groups=len(items),
        items=items,
    )


def _movement_out_values() -> set[str]:
    values = {"OUT", "ADJUSTMENT_NEGATIVE"}
    for name in ("OUT", "ADJUSTMENT_NEGATIVE"):
        member = getattr(StockMovementType, name, None)
        if member is not None:
            values.add(str(member.value))
    return values


def stock_shortage_risks(
    db: Session,
    lookback_days: int = 90,
    limit: int = 100,
) -> StockShortageRisksResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    outgoing_values = _movement_out_values()

    parts = db.scalars(
        select(SparePart)
        .where(SparePart.active.is_(True))
        .order_by(SparePart.quantity.asc(), SparePart.name.asc())
    ).all()

    results: list[StockShortageRiskItem] = []

    for part in parts:
        outgoing_quantity = int(
            db.scalar(
                select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
                    StockMovement.part_id == part.id,
                    StockMovement.created_at >= cutoff,
                    StockMovement.movement_type.in_(outgoing_values),
                )
            ) or 0
        )

        months = max(lookback_days / 30, 1)
        average_monthly_usage = round(outgoing_quantity / months, 2)
        months_of_coverage = (
            round(part.quantity / average_monthly_usage, 2)
            if average_monthly_usage > 0 else None
        )

        below_threshold = part.quantity <= part.minimum_threshold
        low_coverage = months_of_coverage is not None and months_of_coverage <= 1.5

        if not below_threshold and not low_coverage:
            continue

        if part.quantity == 0 or (months_of_coverage is not None and months_of_coverage <= 0.5):
            risk = "CRITICAL"
        elif below_threshold or (months_of_coverage is not None and months_of_coverage <= 1):
            risk = "HIGH"
        else:
            risk = "MEDIUM"

        target_stock = max(
            part.minimum_threshold * 2,
            ceil(average_monthly_usage * 2 + part.minimum_threshold),
        )
        suggested_order_quantity = max(0, int(target_stock - part.quantity))

        results.append(
            StockShortageRiskItem(
                part_id=part.id,
                part_code=part.code,
                part_name=part.name,
                current_quantity=part.quantity,
                minimum_threshold=part.minimum_threshold,
                outgoing_quantity=outgoing_quantity,
                average_monthly_usage=average_monthly_usage,
                months_of_coverage=months_of_coverage,
                suggested_order_quantity=suggested_order_quantity,
                risk=risk,
            )
        )

    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    results.sort(
        key=lambda item: (
            risk_order.get(item.risk, 9),
            item.months_of_coverage if item.months_of_coverage is not None else 999,
            item.current_quantity,
        )
    )
    results = results[:limit]

    return StockShortageRisksResponse(
        lookback_days=lookback_days,
        total_at_risk=len(results),
        items=results,
    )
