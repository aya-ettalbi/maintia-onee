from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable

from app.rag.intelligent_retriever import IntelligentResult
from app.rag.privacy import normalize_for_matching


VAGUE_VALUES = {
    "",
    "probleme",
    "probleme materiel",
    "probleme d impression",
    "prb il",
    "prb",
    "??",
    "resolu",
    "resolution",
    "aucune anomalie",
    "intervention",
    "maintenance",
}


@dataclass(frozen=True)
class EvidenceItem:
    label: str
    evidence_count: int
    references: tuple[str, ...]


def _group_values(
    results: Iterable[IntelligentResult],
    attribute: str,
    *,
    limit: int,
) -> list[EvidenceItem]:
    labels: dict[str, str] = {}
    references: dict[str, list[str]] = {}
    counts: Counter[str] = Counter()

    for result in results:
        raw_value = getattr(result, attribute)
        normalized = normalize_for_matching(raw_value)

        if not _is_meaningful_value(raw_value):
         continue

        labels.setdefault(
            normalized,
            str(raw_value).strip(),
        )
        counts[normalized] += 1

        if result.reference:
            references.setdefault(
                normalized,
                [],
            ).append(result.reference)

    items: list[EvidenceItem] = []

    for normalized, count in counts.most_common(limit):
        items.append(
            EvidenceItem(
                label=labels[normalized],
                evidence_count=count,
                references=tuple(
                    dict.fromkeys(
                        references.get(normalized, [])
                    )
                ),
            )
        )

    return items
EQUIPMENT_CODE_RE = re.compile(
    r"\b[A-Z]{2,5}[-_]?\d{3,}\b",
    re.IGNORECASE,
)


def _extract_requested_equipment_code(
    question: str,
) -> str | None:
    match = EQUIPMENT_CODE_RE.search(question)

    if not match:
        return None

    return match.group(0).upper().replace("_", "-")


def _is_meaningful_value(
    value: object,
) -> bool:
    normalized = normalize_for_matching(value)

    if not normalized:
        return False

    if normalized in VAGUE_VALUES:
        return False

    # Ignore les valeurs trop courtes comme "ok", "??", "prb".
    useful_characters = normalized.replace(" ", "")

    return len(useful_characters) >= 5

def calculate_confidence(
    question: str,
    results: list[IntelligentResult],
) -> tuple[str, int]:
    """
    Calcule la confiance à partir de critères contrôlés par le Backend.

    HIGH :
    - au moins trois sources solides ;
    - scores élevés ;
    - résultats cohérents ;
    - majorité de liens HIGH ou sources indépendantes d'un lien équipement.

    MEDIUM :
    - résultats pertinents ;
    - plusieurs liens MEDIUM ;
    - causes différentes ou preuves partielles.

    LOW :
    - aucun résultat ;
    - scores faibles ;
    - équipement exact introuvable ;
    - contradictions importantes.
    """
    if not results:
        return "LOW", 0

    requested_equipment_code = (
        _extract_requested_equipment_code(question)
    )

    # Lorsqu'un code précis est demandé, les résultats doivent
    # obligatoirement appartenir à cet équipement.
    if requested_equipment_code:
        exact_matches = [
            result
            for result in results
            if result.equipment_code
            == requested_equipment_code
        ]

        if not exact_matches:
            return "LOW", 0

        # Ne garder que les résultats de l'équipement demandé
        # pour calculer la confiance.
        evaluated_results = exact_matches[:5]
    else:
        evaluated_results = results[:5]

    if not evaluated_results:
        return "LOW", 0

    average_score = sum(
        result.final_score
        for result in evaluated_results
    ) / len(evaluated_results)

    # Source solide : score final au moins égal à 0,65.
    strong_count = sum(
        result.final_score >= 0.65
        for result in evaluated_results
    )

    high_or_independent_count = sum(
        result.link_trust in ("HIGH", None)
        for result in evaluated_results
    )

    medium_count = sum(
        result.link_trust == "MEDIUM"
        for result in evaluated_results
    )

    low_count = sum(
        result.link_trust == "LOW"
        for result in evaluated_results
    )

    meaningful_causes = {
        normalize_for_matching(result.cause)
        for result in evaluated_results
        if _is_meaningful_value(result.cause)
    }

    meaningful_solutions = {
        normalize_for_matching(result.solution)
        for result in evaluated_results
        if _is_meaningful_value(result.solution)
    }

    classification_groups = {
        result.classification_group
        for result in evaluated_results
        if result.classification_group
    }

    # Score de base, calculé uniquement par le Backend.
    score = round(
        65 * average_score
        + 5 * strong_count
        + 2 * high_or_independent_count
    )

    # Plusieurs liens automatiques MEDIUM :
    # la confiance ne doit pas rester HIGH.
    if medium_count > high_or_independent_count:
        score -= 15

    # Un lien LOW diminue fortement la confiance.
    if low_count > 0:
        score -= 10

    # Trop de causes différentes indique une incertitude.
    causes_are_divergent = len(meaningful_causes) >= 4

    if causes_are_divergent:
        score -= 10

    # Des catégories très différentes peuvent indiquer
    # des résultats partiellement incohérents.
    classifications_are_divergent = (
        len(classification_groups) >= 3
    )

    if classifications_are_divergent:
        score -= 10

    # Peu de preuves réellement documentées.
    if (
        not meaningful_causes
        and not meaningful_solutions
    ):
        score -= 15

    if strong_count < 2:
        score -= 8

    score = max(0, min(100, score))

    high_conditions = (
        score >= 72
        and strong_count >= 3
        and medium_count <= high_or_independent_count
        and low_count == 0
        and not causes_are_divergent
        and not classifications_are_divergent
    )

    if high_conditions:
        return "HIGH", score

    medium_conditions = (
        score >= 45
        and strong_count >= 1
    )

    if medium_conditions:
        return "MEDIUM", score

    return "LOW", score


def build_recommendation_evidence(
    question: str,
    results: list[IntelligentResult],
) -> dict:
    confidence, confidence_score = calculate_confidence(
    question,
    results,
)

    causes = _group_values(
        results[:8],
        "cause",
        limit=5,
    )
    solutions = _group_values(
        results[:8],
        "solution",
        limit=5,
    )

    return {
        "question": question,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "human_validation_required": True,
        "probable_causes": [
            asdict(item)
            for item in causes
        ],
        "historical_solutions": [
            asdict(item)
            for item in solutions
        ],
        "sources": [
            {
                "reference": result.reference,
                "final_score": result.final_score,
                "reranker_score": result.reranker_score,
                "dense_score": result.dense_score,
                "classification": result.classification,
                "equipment_code": result.equipment_code,
                "equipment_brand": result.equipment_brand,
                "equipment_model": result.equipment_model,
                "link_trust": result.link_trust,
            }
            for result in results
        ],
        "safety_rule": (
            "La recommandation est une aide au diagnostic. "
            "Toute action matérielle doit être validée "
            "par un technicien habilité."
        ),
    }
