from __future__ import annotations

import json
import logging
import math
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    EquipmentStatus,
    InterventionStatus,
    MaintenanceType,
    Priority,
    RecommendationStatus,
    RecommendationType,
    Role,
    UserStatus,
)
from app.models.ai_core import EquipmentHistoricalLink
from app.models.audit import Notification
from app.models.equipment import Equipment
from app.models.historical import HistoricalRequest
from app.models.intelligence import Recommendation
from app.models.maintenance import Intervention
from app.models.phase3_preventive import PreventiveMaintenancePlan
from app.models.phase4_failure_forecast import (
    FailureForecast,
    FailureForecastRun,
)
from app.models.user import User
from app.schemas.phase4_failure_forecast import (
    FailureForecastBatchRequest,
    FailureForecastBatchResponse,
    FailureForecastNarrative,
    FailureForecastSummary,
)
from app.services.audit import create_notification, log_action
from app.services.openrouter import OpenRouterClient, OpenRouterError


logger = logging.getLogger(__name__)

METHODOLOGY_VERSION = "HEURISTIC_HISTORY_V1"
EXACT_LINK_METHODS = {
    "CODE_ET_SERIE_EXACTS",
    "CODE_EQUIPEMENT_EXACT",
    "NUMERO_SERIE_EXACT",
}

FAMILY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "POWER": (
        "alimentation",
        "ne s allume",
        "demarrage",
        "demarrer",
        "power",
        "bip",
        "onduleur",
        "electrique",
    ),
    "STORAGE": (
        "disque",
        "hdd",
        "ssd",
        "boot",
        "secteur defectueux",
        "stockage",
    ),
    "MEMORY": (
        "ram",
        "memoire",
        "barrette",
    ),
    "DISPLAY": (
        "ecran",
        "affichage",
        "moniteur",
        "image noire",
        "ecran noir",
        "video",
    ),
    "PRINTER": (
        "imprimante",
        "impression",
        "bourrage",
        "papier",
        "toner",
        "cartouche",
    ),
    "COOLING": (
        "chauffe",
        "surchauffe",
        "ventilateur",
        "temperature",
        "refroidissement",
    ),
    "MOTHERBOARD": (
        "carte mere",
        "bios",
        "motherboard",
    ),
    "NETWORK": (
        "reseau",
        "connexion",
        "ethernet",
        "wifi",
        "prise",
    ),
    "PERIPHERAL": (
        "clavier",
        "souris",
        "scanner",
        "usb",
        "peripherique",
    ),
    "OPERATING_SYSTEM": (
        "windows",
        "systeme",
        "ecran bleu",
        "logiciel",
    ),
}

FAMILY_ACTIONS: dict[str, list[str]] = {
    "POWER": [
        "Controler l'alimentation, le cable secteur et l'onduleur.",
        "Tester le bloc d'alimentation avec un equipement de diagnostic adapte.",
    ],
    "STORAGE": [
        "Verifier l'etat SMART du disque et sauvegarder les donnees critiques.",
        "Preparer un support de remplacement compatible si les indicateurs se degradent.",
    ],
    "MEMORY": [
        "Executer un test memoire et controler les barrettes RAM.",
        "Nettoyer et reinstaller les barrettes avant tout remplacement.",
    ],
    "DISPLAY": [
        "Tester l'ecran, le cable video et la sortie graphique.",
        "Comparer avec un ecran de reference avant de remplacer une piece.",
    ],
    "PRINTER": [
        "Nettoyer le chemin papier et controler les consommables.",
        "Verifier les rouleaux, le four et les erreurs recurrentes du journal.",
    ],
    "COOLING": [
        "Nettoyer les ventilateurs et les circuits d'aeration.",
        "Controler les temperatures et remplacer la pate thermique si necessaire.",
    ],
    "MOTHERBOARD": [
        "Executer un diagnostic BIOS et controler les composants de la carte mere.",
        "Prevoir une expertise materielle avant toute decision de remplacement.",
    ],
    "NETWORK": [
        "Tester le cable, la prise, le port reseau et la configuration IP.",
        "Comparer le resultat avec un poste de reference.",
    ],
    "PERIPHERAL": [
        "Tester le peripherique et le port sur un equipement de reference.",
        "Verifier les pilotes et l'etat physique des connecteurs.",
    ],
    "OPERATING_SYSTEM": [
        "Verifier les journaux Windows, les mises a jour et l'integrite systeme.",
        "Sauvegarder les donnees avant toute reinstallation.",
    ],
    "OTHER": [
        "Realiser un diagnostic materiel complet avant toute intervention.",
        "Consigner les symptomes, les tests et les resultats obtenus.",
    ],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize(value: object) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _classify_family(*values: object) -> str:
    text = _normalize(" ".join(str(value or "") for value in values))
    if not text:
        return "OTHER"

    scores: dict[str, int] = {}
    for family, keywords in FAMILY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score:
            scores[family] = score

    if not scores:
        return "OTHER"
    return max(scores, key=lambda item: (scores[item], item))


def _link_weight(link: EquipmentHistoricalLink) -> float:
    if link.validation_status == "VALIDE":
        return 1.0
    if link.link_method in EXACT_LINK_METHODS:
        return 1.0
    if float(link.confidence_score or 0) >= 0.85:
        return 0.75
    return 0.40


def _equipment_age_years(equipment: Equipment) -> float | None:
    reference = equipment.commissioning_date or equipment.acquisition_date
    if reference is None:
        return None
    return max((date.today() - reference).days / 365.25, 0.0)


def _historical_evidence(
    db: Session,
    equipment_id: int,
) -> dict[str, Any]:
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
            EquipmentHistoricalLink.equipment_id == equipment_id,
            EquipmentHistoricalLink.validation_status.in_(["AUTO", "VALIDE"]),
        )
        .order_by(
            HistoricalRequest.date_creation_demande.desc(),
            HistoricalRequest.id.desc(),
        )
    ).all()

    unique: dict[int, tuple[EquipmentHistoricalLink, HistoricalRequest]] = {}
    for link, request in rows:
        current = unique.get(request.id)
        if current is None or _link_weight(link) > _link_weight(current[0]):
            unique[request.id] = (link, request)

    today = date.today()
    one_year_ago = today - timedelta(days=365)
    two_years_ago = today - timedelta(days=730)

    family_weights: dict[str, float] = defaultdict(float)
    exact_links = 0
    recent_365 = 0
    recent_730 = 0
    latest_date: date | None = None
    weighted_count = 0.0
    references: list[str] = []

    for link, request in unique.values():
        weight = _link_weight(link)
        weighted_count += weight

        if weight >= 1.0:
            exact_links += 1

        request_date = (
            request.date_creation_demande.date()
            if request.date_creation_demande
            else None
        )
        if request_date is not None:
            latest_date = max(latest_date, request_date) if latest_date else request_date
            if request_date >= one_year_ago:
                recent_365 += 1
            if request_date >= two_years_ago:
                recent_730 += 1

        family = _classify_family(
            request.classification,
            request.detail_classification,
            request.nature_demande,
            request.symptome,
            request.description_demande,
            request.cause,
        )
        family_weights[family] += weight

        if request.numero_demande and len(references) < 10:
            references.append(str(request.numero_demande))

    predicted_family = None
    top_family_weight = 0.0
    if family_weights:
        predicted_family = max(
            family_weights,
            key=lambda item: (family_weights[item], item),
        )
        top_family_weight = float(family_weights[predicted_family])
        if predicted_family == "OTHER" and len(family_weights) > 1:
            non_other = {
                key: value
                for key, value in family_weights.items()
                if key != "OTHER"
            }
            if non_other:
                predicted_family = max(
                    non_other,
                    key=lambda item: (non_other[item], item),
                )
                top_family_weight = float(non_other[predicted_family])

    return {
        "linked_requests": len(unique),
        "weighted_linked_requests": round(weighted_count, 2),
        "exact_or_validated_links": exact_links,
        "recent_365_days": recent_365,
        "recent_730_days": recent_730,
        "latest_historical_request_date": (
            latest_date.isoformat()
            if latest_date
            else None
        ),
        "family_weights": {
            key: round(value, 2)
            for key, value in sorted(
                family_weights.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        },
        "predicted_family": predicted_family,
        "top_family_weight": round(top_family_weight, 2),
        "references": references[:5],
    }


def _live_evidence(
    db: Session,
    equipment_id: int,
) -> dict[str, Any]:
    now = utc_now()
    corrective = db.scalars(
        select(Intervention)
        .where(
            Intervention.equipment_id == equipment_id,
            Intervention.maintenance_type == MaintenanceType.CORRECTIVE.value,
        )
        .order_by(Intervention.created_at.desc())
    ).all()

    last_180 = [
        item
        for item in corrective
        if item.created_at >= now - timedelta(days=180)
    ]
    last_365 = [
        item
        for item in corrective
        if item.created_at >= now - timedelta(days=365)
    ]
    completed = [
        item
        for item in corrective
        if item.status == InterventionStatus.COMPLETED.value
    ]

    total_cost = sum(
        (Decimal(item.actual_cost or 0) for item in completed),
        Decimal("0"),
    )

    diagnosis_families: dict[str, int] = defaultdict(int)
    for item in corrective:
        family = _classify_family(item.diagnosis, item.solution)
        diagnosis_families[family] += 1

    return {
        "corrective_total": len(corrective),
        "corrective_180_days": len(last_180),
        "corrective_365_days": len(last_365),
        "corrective_completed": len(completed),
        "completed_actual_cost": float(total_cost),
        "diagnosis_families": dict(diagnosis_families),
    }


def _overdue_preventive_count(
    db: Session,
    equipment_id: int,
) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(PreventiveMaintenancePlan)
            .where(
                PreventiveMaintenancePlan.equipment_id == equipment_id,
                PreventiveMaintenancePlan.active.is_(True),
                PreventiveMaintenancePlan.next_due_date < date.today(),
            )
        )
        or 0
    )


def _probability_from_score(
    score: float,
    horizon_days: int,
) -> float:
    base = min(max(score / 100.0, 0.0), 0.98)
    horizon_factor = min(max(horizon_days / 90.0, 0.25), 2.0)
    probability = 1.0 - math.pow(1.0 - base, horizon_factor)
    return round(min(max(probability, 0.0), 0.95), 4)


def _risk_level(
    probability: float,
    equipment_status: str,
) -> str:
    if equipment_status in {
        EquipmentStatus.IN_FAILURE.value,
        EquipmentStatus.OUT_OF_SERVICE.value,
    }:
        return "HIGH"
    if probability >= 0.65:
        return "HIGH"
    if probability >= 0.30:
        return "MEDIUM"
    return "LOW"


def _evidence_confidence(
    historical: dict[str, Any],
    live: dict[str, Any],
    age_years: float | None,
) -> str:
    if (
        historical["exact_or_validated_links"] >= 3
        or live["corrective_total"] >= 2
    ):
        return "HIGH"
    if historical["linked_requests"] >= 1 or live["corrective_total"] >= 1:
        return "MEDIUM"
    if age_years is not None:
        return "MEDIUM"
    return "LOW"


def _estimated_window(
    risk_level: str,
    horizon_days: int,
) -> tuple[date | None, date | None]:
    today = date.today()
    if risk_level == "HIGH":
        start = today + timedelta(days=max(3, round(horizon_days * 0.15)))
        return start, today + timedelta(days=horizon_days)
    if risk_level == "MEDIUM":
        start = today + timedelta(days=max(7, round(horizon_days * 0.35)))
        return start, today + timedelta(days=horizon_days)
    return None, None


def _score_and_factors(
    equipment: Equipment,
    historical: dict[str, Any],
    live: dict[str, Any],
    overdue_preventive: int,
) -> tuple[float, list[str], float | None]:
    score = 0.0
    factors: list[str] = []
    age_years = _equipment_age_years(equipment)

    status_points = {
        EquipmentStatus.IN_FAILURE.value: 30,
        EquipmentStatus.OUT_OF_SERVICE.value: 35,
        EquipmentStatus.WAITING_PART.value: 20,
        EquipmentStatus.IN_MAINTENANCE.value: 10,
    }
    points = status_points.get(equipment.status, 0)
    if points:
        score += points
        factors.append(
            f"Statut actuel de l'equipement : {equipment.status} (+{points})"
        )

    if age_years is not None:
        if age_years >= 8:
            score += 25
            factors.append(f"Anciennete tres elevee : {age_years:.1f} ans (+25)")
        elif age_years >= 5:
            score += 18
            factors.append(f"Anciennete elevee : {age_years:.1f} ans (+18)")
        elif age_years >= 3:
            score += 8
            factors.append(f"Anciennete a surveiller : {age_years:.1f} ans (+8)")

    if (
        equipment.warranty_end_date is not None
        and equipment.warranty_end_date < date.today()
    ):
        score += 5
        factors.append("Garantie expiree (+5)")

    weighted_history = float(historical["weighted_linked_requests"])
    if weighted_history >= 10:
        score += 25
        factors.append(
            f"Historique lie important : {historical['linked_requests']} demandes (+25)"
        )
    elif weighted_history >= 6:
        score += 18
        factors.append(
            f"Historique lie recurrent : {historical['linked_requests']} demandes (+18)"
        )
    elif weighted_history >= 3:
        score += 12
        factors.append(
            f"Plusieurs demandes historiques liees : {historical['linked_requests']} (+12)"
        )
    elif weighted_history > 0:
        score += 5
        factors.append(
            f"Historique lie disponible : {historical['linked_requests']} demande(s) (+5)"
        )

    live_180 = int(live["corrective_180_days"])
    if live_180:
        live_points = min(live_180 * 10, 30)
        score += live_points
        factors.append(
            f"{live_180} intervention(s) corrective(s) sur 180 jours (+{live_points})"
        )

    top_family_weight = float(historical["top_family_weight"])
    predicted_family = historical["predicted_family"]
    if predicted_family and top_family_weight >= 3:
        score += 12
        factors.append(
            f"Famille de panne recurrente {predicted_family} (+12)"
        )
    elif predicted_family and top_family_weight >= 2:
        score += 7
        factors.append(
            f"Famille de panne repetee {predicted_family} (+7)"
        )

    if historical["recent_365_days"] > 0:
        score += 8
        factors.append(
            f"{historical['recent_365_days']} demande(s) historique(s) sur 365 jours (+8)"
        )
    elif historical["recent_730_days"] > 0:
        score += 4
        factors.append(
            f"{historical['recent_730_days']} demande(s) historique(s) sur 730 jours (+4)"
        )

    if overdue_preventive > 0:
        overdue_points = min(overdue_preventive * 12, 24)
        score += overdue_points
        factors.append(
            f"{overdue_preventive} plan(s) preventif(s) en retard (+{overdue_points})"
        )

    score = round(min(score, 100.0), 2)
    if not factors:
        factors.append(
            "Aucun facteur majeur detecte avec les donnees actuellement disponibles"
        )

    return score, factors, age_years


def _recommended_actions(
    *,
    risk_level: str,
    predicted_family: str | None,
    age_years: float | None,
    overdue_preventive: int,
) -> list[str]:
    actions: list[str] = []

    if risk_level == "HIGH":
        actions.append(
            "Programmer une inspection preventive prioritaire sous 15 jours."
        )
    elif risk_level == "MEDIUM":
        actions.append(
            "Programmer un controle preventif dans les 30 prochains jours."
        )
    else:
        actions.append(
            "Maintenir la surveillance normale et respecter le calendrier preventif."
        )

    actions.extend(FAMILY_ACTIONS.get(predicted_family or "OTHER", FAMILY_ACTIONS["OTHER"]))

    if overdue_preventive:
        actions.append(
            "Traiter les plans preventifs en retard avant une nouvelle echeance."
        )

    if age_years is not None and age_years >= 8:
        actions.append(
            "Comparer le cout de maintenance au cout de renouvellement de l'equipement."
        )

    unique: list[str] = []
    for action in actions:
        if action not in unique:
            unique.append(action)
    return unique[:6]


def _deterministic_explanation(
    *,
    equipment: Equipment,
    horizon_days: int,
    risk_score: float,
    failure_probability: float,
    risk_level: str,
    confidence: str,
    predicted_family: str | None,
    factors: list[str],
) -> str:
    family_text = predicted_family or "non determinee"
    return (
        f"Prevision pour l'equipement {equipment.code} sur {horizon_days} jours. "
        f"Le score de risque deterministe est de {risk_score:.2f}/100 et "
        f"l'estimation heuristique de panne est de "
        f"{failure_probability * 100:.1f} %. "
        f"Le niveau de risque est {risk_level}, avec une confiance des preuves "
        f"{confidence}. La famille de panne la plus probable est {family_text}. "
        f"Facteurs principaux : {'; '.join(factors[:5])}. "
        "Cette estimation n'est pas une probabilite statistique calibree et "
        "doit etre validee par un technicien."
    )


def build_forecast_snapshot(
    db: Session,
    *,
    equipment_id: int,
    horizon_days: int,
) -> dict[str, Any]:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None or equipment.archived:
        raise HTTPException(status_code=404, detail="Equipement introuvable")

    historical = _historical_evidence(db, equipment_id)
    live = _live_evidence(db, equipment_id)
    overdue = _overdue_preventive_count(db, equipment_id)

    risk_score, factors, age_years = _score_and_factors(
        equipment,
        historical,
        live,
        overdue,
    )
    probability = _probability_from_score(risk_score, horizon_days)
    risk_level = _risk_level(probability, equipment.status)
    confidence = _evidence_confidence(historical, live, age_years)
    predicted_family = historical["predicted_family"]
    start_date, end_date = _estimated_window(risk_level, horizon_days)
    actions = _recommended_actions(
        risk_level=risk_level,
        predicted_family=predicted_family,
        age_years=age_years,
        overdue_preventive=overdue,
    )

    evidence_summary = {
        "equipment": {
            "code": equipment.code,
            "brand": equipment.brand,
            "model": equipment.model,
            "status": equipment.status,
            "age_years": round(age_years, 2) if age_years is not None else None,
            "warranty_end_date": (
                equipment.warranty_end_date.isoformat()
                if equipment.warranty_end_date
                else None
            ),
        },
        "historical": historical,
        "live_interventions": live,
        "overdue_preventive_plans": overdue,
        "probability_note": (
            "Estimation heuristique non calibree. "
            "Ne pas presenter comme une certitude statistique."
        ),
    }

    explanation = _deterministic_explanation(
        equipment=equipment,
        horizon_days=horizon_days,
        risk_score=risk_score,
        failure_probability=probability,
        risk_level=risk_level,
        confidence=confidence,
        predicted_family=predicted_family,
        factors=factors,
    )

    return {
        "equipment": equipment,
        "horizon_days": horizon_days,
        "risk_score": risk_score,
        "failure_probability": probability,
        "probability_calibrated": False,
        "risk_level": risk_level,
        "evidence_confidence": confidence,
        "predicted_failure_family": predicted_family,
        "estimated_start_date": start_date,
        "estimated_end_date": end_date,
        "factors": factors,
        "recommended_actions": actions,
        "evidence_summary": evidence_summary,
        "similar_references": historical["references"],
        "explanation": explanation,
        "methodology_version": METHODOLOGY_VERSION,
        "llm_used": False,
        "model_name": "deterministic-forecast",
    }


async def enrich_snapshot_with_llm(
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    safe_payload = {
        "equipment": snapshot["evidence_summary"]["equipment"],
        "horizon_days": snapshot["horizon_days"],
        "risk_score": snapshot["risk_score"],
        "failure_probability": snapshot["failure_probability"],
        "probability_calibrated": False,
        "risk_level": snapshot["risk_level"],
        "evidence_confidence": snapshot["evidence_confidence"],
        "predicted_failure_family": snapshot["predicted_failure_family"],
        "factors": snapshot["factors"],
        "recommended_actions": snapshot["recommended_actions"],
        "aggregated_evidence": snapshot["evidence_summary"],
    }

    system_prompt = (
        "Tu es MaintIA, assistant de maintenance informatique ONEE. "
        "Explique une prevision de risque a partir des donnees exactes fournies. "
        "N'invente aucun chiffre, date, panne, piece ou probabilite. "
        "La probabilite fournie est heuristique et non calibree. "
        "Ne modifie pas les facteurs ni les actions calculees par le Backend. "
        "Indique qu'une validation humaine est obligatoire. "
        "Retourne uniquement le JSON demande."
    )

    try:
        client = OpenRouterClient()
        raw, model_name = await client.generate_structured(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": (
                        "Redige une synthese professionnelle et une explication "
                        "du risque sans ajouter de nouvelles donnees.\n\n"
                        + json.dumps(
                            safe_payload,
                            ensure_ascii=False,
                            indent=2,
                        )
                    ),
                },
            ],
            json_schema=FailureForecastNarrative.model_json_schema(),
            schema_name="failure_forecast_narrative",
        )
        narrative = FailureForecastNarrative.model_validate(raw)

        warning_text = " ".join(
            item.strip()
            for item in narrative.warnings
            if item and item.strip()
        )
        snapshot["explanation"] = (
            narrative.summary.strip()
            + "\n\n"
            + narrative.risk_explanation.strip()
            + (
                "\n\nAvertissements : " + warning_text
                if warning_text
                else ""
            )
        )
        snapshot["llm_used"] = True
        snapshot["model_name"] = model_name
    except (
        OpenRouterError,
        ValueError,
        TypeError,
    ) as error:
        logger.warning(
            "Echec OpenRouter pour la prevision, fallback conserve : %s",
            error,
        )

    return snapshot


def _existing_open_recommendation(
    db: Session,
    equipment_id: int,
) -> Recommendation | None:
    cutoff = utc_now() - timedelta(days=30)
    return db.scalar(
        select(Recommendation)
        .where(
            Recommendation.equipment_id == equipment_id,
            Recommendation.recommendation_type
            == RecommendationType.PREVENTIVE_MAINTENANCE.value,
            Recommendation.generated_at >= cutoff,
            Recommendation.status.not_in(
                [
                    RecommendationStatus.APPLIED.value,
                    RecommendationStatus.REJECTED.value,
                    RecommendationStatus.EXPIRED.value,
                ]
            ),
        )
        .order_by(Recommendation.id.desc())
    )


def _ensure_high_risk_recommendation(
    db: Session,
    *,
    snapshot: dict[str, Any],
) -> tuple[int | None, bool]:
    equipment: Equipment = snapshot["equipment"]
    existing = _existing_open_recommendation(db, equipment.id)
    if existing is not None:
        return existing.id, False

    recommendation = Recommendation(
        equipment_id=equipment.id,
        part_id=None,
        recommendation_type=RecommendationType.PREVENTIVE_MAINTENANCE.value,
        priority=Priority.CRITICAL.value,
        title=f"Risque de panne eleve - {equipment.code}",
        observation=(
            f"Prevision a {snapshot['horizon_days']} jours : "
            f"{snapshot['risk_score']:.2f}/100, "
            f"niveau {snapshot['risk_level']}."
        ),
        justification="; ".join(snapshot["factors"]),
        recommended_action=" ".join(snapshot["recommended_actions"]),
        risk_score=snapshot["risk_score"],
        risk_level=snapshot["risk_level"],
        status=RecommendationStatus.NEW.value,
        due_date=date.today() + timedelta(days=15),
    )
    db.add(recommendation)
    db.flush()
    return recommendation.id, True


def _notify_managers(
    db: Session,
    *,
    snapshot: dict[str, Any],
) -> int:
    equipment: Equipment = snapshot["equipment"]
    users = db.scalars(
        select(User).where(
            User.role.in_([Role.ADMIN.value, Role.MANAGER.value]),
            User.status == UserStatus.ACTIVE.value,
        )
    ).all()

    title = "Risque de panne eleve"
    message = (
        f"Equipement {equipment.code} : score "
        f"{snapshot['risk_score']:.2f}/100 sur "
        f"{snapshot['horizon_days']} jours. "
        "Une validation technique est requise."
    )
    day_start = datetime.combine(
        date.today(),
        time.min,
        tzinfo=timezone.utc,
    )

    created = 0
    for user in users:
        duplicate = db.scalar(
            select(Notification.id).where(
                Notification.user_id == user.id,
                Notification.title == title,
                Notification.message == message,
                Notification.created_at >= day_start,
            )
        )
        if duplicate is not None:
            continue

        create_notification(
            db,
            user_id=user.id,
            title=title,
            message=message,
        )
        created += 1

    return created


def persist_forecast(
    db: Session,
    *,
    snapshot: dict[str, Any],
    created_by_id: int | None,
    create_actions: bool,
) -> tuple[FailureForecast, bool, int]:
    recommendation_id = None
    recommendation_created = False
    notification_count = 0

    if create_actions and snapshot["risk_level"] == "HIGH":
        recommendation_id, recommendation_created = (
            _ensure_high_risk_recommendation(
                db,
                snapshot=snapshot,
            )
        )
        notification_count = _notify_managers(
            db,
            snapshot=snapshot,
        )

    forecast = FailureForecast(
        equipment_id=snapshot["equipment"].id,
        horizon_days=snapshot["horizon_days"],
        risk_score=snapshot["risk_score"],
        failure_probability=snapshot["failure_probability"],
        probability_calibrated=False,
        risk_level=snapshot["risk_level"],
        evidence_confidence=snapshot["evidence_confidence"],
        predicted_failure_family=snapshot["predicted_failure_family"],
        estimated_start_date=snapshot["estimated_start_date"],
        estimated_end_date=snapshot["estimated_end_date"],
        factors=snapshot["factors"],
        recommended_actions=snapshot["recommended_actions"],
        evidence_summary=snapshot["evidence_summary"],
        similar_references=snapshot["similar_references"],
        explanation=snapshot["explanation"],
        methodology_version=snapshot["methodology_version"],
        llm_used=snapshot["llm_used"],
        model_name=snapshot["model_name"],
        recommendation_id=recommendation_id,
        notification_created=notification_count > 0,
        validation_status="PENDING",
        created_by_id=created_by_id,
    )
    db.add(forecast)
    db.flush()

    log_action(
        db,
        actor_id=created_by_id,
        action="CREATE_FAILURE_FORECAST",
        entity_type="FailureForecast",
        entity_id=forecast.id,
        details={
            "equipment_id": forecast.equipment_id,
            "horizon_days": forecast.horizon_days,
            "risk_score": forecast.risk_score,
            "risk_level": forecast.risk_level,
            "llm_used": forecast.llm_used,
            "probability_calibrated": False,
        },
    )

    return forecast, recommendation_created, notification_count


def run_batch_forecasts(
    db: Session,
    *,
    payload: FailureForecastBatchRequest,
    actor: User | None,
) -> FailureForecastBatchResponse:
    actor_id = actor.id if actor is not None else None
    run = FailureForecastRun(
        horizon_days=payload.horizon_days,
        only_with_history=payload.only_with_history,
        requested_limit=payload.limit,
        triggered_by_id=actor_id,
        status="RUNNING",
    )
    db.add(run)
    db.flush()

    stmt = (
        select(Equipment)
        .where(
            Equipment.archived.is_(False),
            Equipment.status.not_in(
                [
                    EquipmentStatus.ARCHIVED.value,
                    EquipmentStatus.REFORMED.value,
                ]
            ),
        )
        .order_by(Equipment.id.asc())
        .offset(payload.offset)
        .limit(payload.limit)
    )

    if payload.only_with_history:
        stmt = stmt.where(
            exists(
                select(EquipmentHistoricalLink.id).where(
                    EquipmentHistoricalLink.equipment_id == Equipment.id
                )
            )
        )

    equipments = db.scalars(stmt).all()
    errors: list[dict[str, Any]] = []

    for equipment in equipments:
        try:
            with db.begin_nested():
                snapshot = build_forecast_snapshot(
                    db,
                    equipment_id=equipment.id,
                    horizon_days=payload.horizon_days,
                )
                _, recommendation_created, notification_count = persist_forecast(
                    db,
                    snapshot=snapshot,
                    created_by_id=actor_id,
                    create_actions=payload.create_actions,
                )

                run.processed_count += 1
                if snapshot["risk_level"] == "HIGH":
                    run.high_risk_count += 1
                elif snapshot["risk_level"] == "MEDIUM":
                    run.medium_risk_count += 1
                else:
                    run.low_risk_count += 1

                if recommendation_created:
                    run.recommendations_created += 1
                run.notifications_created += notification_count

        except Exception as error:
            logger.exception(
                "Echec prevision equipement %s : %s",
                equipment.id,
                error,
            )
            run.error_count += 1
            if len(errors) < 100:
                errors.append(
                    {
                        "equipment_id": equipment.id,
                        "error": str(error)[:500],
                    }
                )

    run.error_details = errors
    run.ended_at = utc_now()
    run.status = (
        "COMPLETED"
        if run.error_count == 0
        else "COMPLETED_WITH_ERRORS"
    )

    log_action(
        db,
        actor_id=actor_id,
        action="RUN_FAILURE_FORECAST_BATCH",
        entity_type="FailureForecastRun",
        entity_id=run.id,
        details={
            "processed_count": run.processed_count,
            "high_risk_count": run.high_risk_count,
            "error_count": run.error_count,
        },
    )
    db.commit()
    db.refresh(run)

    return FailureForecastBatchResponse(
        run_id=run.id,
        status=run.status,
        horizon_days=run.horizon_days,
        processed_count=run.processed_count,
        high_risk_count=run.high_risk_count,
        medium_risk_count=run.medium_risk_count,
        low_risk_count=run.low_risk_count,
        notifications_created=run.notifications_created,
        recommendations_created=run.recommendations_created,
        error_count=run.error_count,
    )


def latest_forecast_query(
    *,
    horizon_days: int | None = None,
):
    latest_ids = (
        select(func.max(FailureForecast.id).label("id"))
        .group_by(FailureForecast.equipment_id)
    )
    if horizon_days is not None:
        latest_ids = latest_ids.where(
            FailureForecast.horizon_days == horizon_days
        )
    return latest_ids


def build_forecast_summary(db: Session) -> FailureForecastSummary:
    total = int(
        db.scalar(
            select(func.count()).select_from(FailureForecast)
        )
        or 0
    )

    latest_ids = latest_forecast_query().subquery()
    latest_rows = db.scalars(
        select(FailureForecast).where(
            FailureForecast.id.in_(select(latest_ids.c.id))
        )
    ).all()

    status_counts = defaultdict(int)
    validation_counts = defaultdict(int)
    for item in latest_rows:
        status_counts[item.risk_level] += 1
        validation_counts[item.validation_status] += 1

    latest_run = db.scalar(
        select(FailureForecastRun)
        .order_by(FailureForecastRun.id.desc())
        .limit(1)
    )

    return FailureForecastSummary(
        total_forecasts=total,
        latest_forecasts=len(latest_rows),
        high_risk=status_counts["HIGH"],
        medium_risk=status_counts["MEDIUM"],
        low_risk=status_counts["LOW"],
        pending_validation=validation_counts["PENDING"],
        confirmed=validation_counts["CONFIRMED"],
        partial=validation_counts["PARTIAL"],
        rejected=validation_counts["REJECTED"],
        latest_run=latest_run,
        warning=(
            "Les probabilites sont des estimations heuristiques non calibrees. "
            "Une validation humaine est obligatoire."
        ),
    )
