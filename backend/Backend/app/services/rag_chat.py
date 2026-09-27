from __future__ import annotations

import json
import logging
import re
from functools import lru_cache

from fastapi.concurrency import run_in_threadpool
from typing import Any

from app.rag.intelligent_retriever import (
    IntelligentResult,
    IntelligentRetriever,
)
from app.rag.privacy import anonymize_text
from app.schemas.chat import (
    ChatResponse,
    ChatSource,
    LLMRecommendation,
)
from app.services.equipment_history_service import (
    get_equipment_history_stats,
)
from app.services.openrouter import (
    OpenRouterClient,
    OpenRouterError,
)
from app.services.recommendation_evidence import (
    build_recommendation_evidence,
)


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Tu es MaintIA, un copilote de maintenance informatique pour l'ONEE.

Règles obligatoires :
1. Utilise uniquement les preuves historiques fournies.
2. N'invente jamais une panne, une pièce, un chiffre ou une intervention.
3. Distingue clairement les causes historiques des vérifications proposées.
4. Ne révèle jamais de mot de passe, compte interne, email, matricule,
   adresse MAC, numéro de série ou donnée personnelle.
5. Pour une opération matérielle, indique qu'un technicien habilité
   doit valider l'action.
6. Lorsque les preuves sont faibles ou contradictoires, dis-le clairement.
7. Ne présente pas une similarité comme une certitude scientifique.
8. Réponds en français, de façon professionnelle et compréhensible.
9. Ne cite que les références réellement présentes dans le contexte.
10. Pour une demande de mot de passe, recommande uniquement la procédure
    officielle de réinitialisation. Ne fournis jamais un mot de passe.
11. Retourne uniquement un objet JSON avec les champs à la racine :
    summary, probable_causes, recommended_checks, historical_solutions,
    warnings. N'ajoute pas de clé englobante comme recommendation.
12. Pour EQUIPMENT_HISTORY, utilise exclusivement
    exact_equipment_history_stats pour annoncer les nombres.
    Ne calcule jamais le nombre de demandes à partir des causes,
    solutions ou documents affichés.
""".strip()


@lru_cache(maxsize=1)
def get_retriever() -> IntelligentRetriever:
    """
    Charge les deux modèles une seule fois par processus FastAPI :
    - modèle d'embedding ;
    - Cross-Encoder de reranking.
    """
    return IntelligentRetriever()


@lru_cache(maxsize=1)
def get_openrouter_client() -> OpenRouterClient:
    return OpenRouterClient()


def _safe(value: object, max_length: int = 1200) -> str:
    return anonymize_text(value)[:max_length]


def _build_context(
    question: str,
    parsed: Any,
    results: list[IntelligentResult],
    evidence: dict[str, Any],
    equipment_history_stats: dict[str, Any] | None = None,
) -> str:
    cases: list[dict[str, Any]] = []

    for result in results:
        cases.append(
            {
                "reference": result.reference,
                "score_final": result.final_score,
                "classification": _safe(
                    result.classification,
                    200,
                ),
                "groupe": result.classification_group,
                "equipement_code": result.equipment_code,
                "marque": (
                    _safe(
                        result.equipment_brand,
                        120,
                    )
                    if result.link_trust == "HIGH"
                    else None
                ),
                "modele": (
                    _safe(
                        result.equipment_model,
                        120,
                    )
                    if result.link_trust == "HIGH"
                    else None
                ),
                "fiabilite_lien": result.link_trust,
                "note_lien_equipement": (
                    None
                    if result.link_trust == "HIGH"
                    else (
                        "Lien automatique à vérifier. "
                        "La marque et le modèle ne doivent pas "
                        "être considérés comme des preuves."
                    )
                ),
                "symptome": _safe(
                    result.symptom,
                    500,
                ),
                "cause": _safe(
                    result.cause,
                    500,
                ),
                "solution_historique": _safe(
                    result.solution,
                    700,
                ),
                "contenu": _safe(
                    result.content,
                    1200,
                ),
            }
        )

    safe_evidence = {
        "confidence": evidence.get("confidence"),
        "confidence_score": evidence.get(
            "confidence_score"
        ),
        "probable_causes": [
            {
                "label": _safe(item.get("label"), 500),
                "evidence_count": item.get(
                    "evidence_count"
                ),
                "references": item.get("references", []),
            }
            for item in evidence.get(
                "probable_causes",
                [],
            )
        ],
        "historical_solutions": [
            {
                "label": _safe(item.get("label"), 700),
                "evidence_count": item.get(
                    "evidence_count"
                ),
                "references": item.get("references", []),
            }
            for item in evidence.get(
                "historical_solutions",
                [],
            )
        ],
    }

    context = {
        "question": _safe(question, 2000),
        "intent": parsed.intent,
        "classification_group": (
            parsed.classification_group
        ),
        "equipment_code": parsed.equipment_code,
        "evidence_summary": safe_evidence,
        "exact_equipment_history_stats": (
            equipment_history_stats
        ),
        "historical_cases": cases,
    }

    return json.dumps(
        context,
        ensure_ascii=False,
        indent=2,
    )


def _strip_leading_number(value: str) -> str:
    return re.sub(
        r"^\s*\d+\s*[.)-]\s*",
        "",
        value,
    ).strip()


def _normalize_llm_payload(raw: object) -> dict[str, Any]:
    """
    Accepte les deux formats parfois renvoyés par OpenRouter :

    1. Format attendu :
       {"summary": "...", "probable_causes": [...], ...}

    2. Format enveloppé :
       {"recommendation": {"summary": "...", ...}}

    Les champs de confiance ajoutés par le LLM sont ignorés, car la
    confiance est calculée par le Backend à partir des preuves RAG.
    """
    if not isinstance(raw, dict):
        raise TypeError(
            "La réponse OpenRouter doit être un objet JSON."
        )

    payload: dict[str, Any] = raw

    wrapped = payload.get("recommendation")
    if isinstance(wrapped, dict):
        payload = wrapped

    allowed_fields = {
        "summary",
        "probable_causes",
        "recommended_checks",
        "historical_solutions",
        "warnings",
    }

    normalized = {
        key: value
        for key, value in payload.items()
        if key in allowed_fields
    }

    if not normalized:
        raise ValueError(
            "La réponse OpenRouter ne contient aucun champ attendu."
        )

    return normalized


def _enrich_generated_from_evidence(
    generated: LLMRecommendation,
    evidence: dict[str, Any],
) -> LLMRecommendation:
    """
    Complète la réponse OpenRouter avec les preuves RAG lorsque
    le modèle retourne des listes vides.
    """
    fallback = _deterministic_fallback(evidence)

    probable_causes = [
        item.strip()
        for item in generated.probable_causes
        if item and item.strip()
    ]

    recommended_checks = [
        _strip_leading_number(item)
        for item in generated.recommended_checks
        if item and item.strip()
    ]

    historical_solutions = [
        item.strip()
        for item in generated.historical_solutions
        if item and item.strip()
    ]

    warnings = [
        item.strip()
        for item in generated.warnings
        if item and item.strip()
    ]

    return LLMRecommendation(
        summary=generated.summary.strip(),
        probable_causes=(
            probable_causes
            or fallback.probable_causes
        ),
        recommended_checks=(
            recommended_checks
            or fallback.recommended_checks
        ),
        historical_solutions=(
            historical_solutions
            or fallback.historical_solutions
        ),
        warnings=(
            warnings
            or fallback.warnings
        ),
    )


def _apply_equipment_history_summary(
    generated: LLMRecommendation,
    stats: dict[str, Any] | None,
) -> LLMRecommendation:
    """Construit un résumé exact à partir des données PostgreSQL."""
    if not stats:
        return generated

    equipment_code = str(
        stats.get("equipment_code") or "inconnu"
    )

    if not stats.get("equipment_exists"):
        summary = (
            "Aucun historique fiable n'a été trouvé "
            "pour l'équipement "
            f"{equipment_code}."
        )
    else:
        brand = stats.get("equipment_brand")
        model = stats.get("equipment_model")

        identity_values = [
            str(value).strip()
            for value in (brand, model)
            if value
        ]

        identity = (
            f" ({' '.join(identity_values)})"
            if identity_values
            else ""
        )

        linked_count = int(
            stats.get("linked_requests_count") or 0
        )
        high_count = int(
            stats.get("high_confidence_links") or 0
        )
        medium_count = int(
            stats.get("medium_confidence_links") or 0
        )
        low_count = int(
            stats.get("low_confidence_links") or 0
        )
        causes_count = int(
            stats.get("documented_causes_count") or 0
        )
        solutions_count = int(
            stats.get("documented_solutions_count") or 0
        )

        requests_label = (
            "demande historique"
            if linked_count == 1
            else "demandes historiques"
        )
        high_links_label = (
            "lien" if high_count == 1 else "liens"
        )
        medium_links_label = (
            "lien" if medium_count == 1 else "liens"
        )
        low_links_label = (
            "lien" if low_count == 1 else "liens"
        )
        causes_label = (
            "cause documentée"
            if causes_count == 1
            else "causes documentées"
        )
        solutions_label = (
            "solution documentée"
            if solutions_count == 1
            else "solutions documentées"
        )

        summary = (
            "L'équipement "
            f"{equipment_code}{identity} est associé "
            f"à {linked_count} {requests_label} : "
            f"{high_count} {high_links_label} "
            "à haute fiabilité, "
            f"{medium_count} {medium_links_label} "
            "à moyenne fiabilité et "
            f"{low_count} {low_links_label} "
            "à faible fiabilité. "
            f"L'historique contient {causes_count} "
            f"{causes_label} et {solutions_count} "
            f"{solutions_label}."
        )

    return LLMRecommendation(
        summary=summary,
        probable_causes=generated.probable_causes,
        recommended_checks=generated.recommended_checks,
        historical_solutions=generated.historical_solutions,
        warnings=generated.warnings,
    )


def _compose_answer(
    generated: LLMRecommendation,
) -> str:
    sections = [generated.summary.strip()]

    if generated.probable_causes:
        sections.append(
            "Causes possibles :\n"
            + "\n".join(
                f"- {item}"
                for item in generated.probable_causes
            )
        )

    if generated.recommended_checks:
        sections.append(
            "Vérifications recommandées :\n"
            + "\n".join(
                f"{index}. {_strip_leading_number(item)}"
                for index, item in enumerate(
                    generated.recommended_checks,
                    start=1,
                )
            )
        )

    if generated.historical_solutions:
        sections.append(
            "Solutions observées dans l'historique :\n"
            + "\n".join(
                f"- {item}"
                for item in generated.historical_solutions
            )
        )

    if generated.warnings:
        sections.append(
            "Avertissements :\n"
            + "\n".join(
                f"- {item}"
                for item in generated.warnings
            )
        )

    return "\n\n".join(sections)


def _deterministic_fallback(
    evidence: dict[str, Any],
) -> LLMRecommendation:
    causes = [
        _safe(item.get("label"), 500)
        for item in evidence.get("probable_causes", [])
        if item.get("label")
    ][:5]

    solutions = [
        _safe(item.get("label"), 700)
        for item in evidence.get(
            "historical_solutions",
            [],
        )
        if item.get("label")
    ][:5]

    confidence = evidence.get("confidence", "LOW")

    if confidence == "LOW":
        summary = (
            "Les données historiques disponibles ne permettent pas "
            "d'établir une recommandation suffisamment fiable. "
            "Les éléments ci-dessous doivent être vérifiés manuellement."
        )
    else:
        summary = (
            "Les incidents historiques similaires fournissent "
            "plusieurs pistes de diagnostic à confirmer."
        )

    checks = [
        "Vérifier les symptômes exacts et leur reproductibilité.",
        "Contrôler les branchements, l'alimentation et l'état apparent.",
        "Comparer avec les causes historiques les plus fréquentes.",
        "Consigner les tests réalisés avant tout remplacement de pièce.",
    ]

    return LLMRecommendation(
        summary=summary,
        probable_causes=causes,
        recommended_checks=checks,
        historical_solutions=solutions,
        warnings=[
            "Toute action matérielle doit être validée "
            "par un technicien habilité."
        ],
    )


async def answer_with_rag(
    *,
    message: str,
    candidate_k: int,
    top_k: int,
) -> ChatResponse:
    normalized_message = re.sub(
        r"[^a-z0-9]+",
        " ",
        message.lower().strip(),
    ).strip()

    quick_greetings = {
        "bonjour",
        "bonsoir",
        "salut",
        "hello",
        "hi",
        "salam",
        "salam alaykom",
        "assalam alaykom",
        "merci",
    }

    if normalized_message in quick_greetings:
        summary = (
            "Bonjour, je suis MaintIA. Décrivez un symptôme, "
            "indiquez le code d'un équipement ou demandez son historique."
        )
        return ChatResponse(
            answer=summary,
            summary=summary,
            probable_causes=[],
            recommended_checks=[
                "Exemple : écran noir avec trois bips au démarrage.",
                "Exemple : historique de l'équipement UC110570.",
            ],
            historical_solutions=[],
            warnings=[],
            confidence="HIGH",
            confidence_score=100,
            human_validation_required=False,
            intent="GREETING",
            classification_group=None,
            equipment_code=None,
            model="deterministic-greeting",
            llm_used=False,
            sources=[],
        )

    # Les modèles et le reranking utilisent le CPU. Ils sont exécutés
    # dans un thread pour ne pas bloquer /health ni le reste du Backend.
    retriever = await run_in_threadpool(get_retriever)
    parsed, results = await run_in_threadpool(
        retriever.search,
        message,
        candidate_k=candidate_k,
        final_k=top_k,
    )

    evidence = build_recommendation_evidence(
        message,
        results,
    )

    equipment_history_stats = None

    if (
        parsed.intent == "EQUIPMENT_HISTORY"
        and parsed.equipment_code
    ):
        equipment_history_stats = (
            get_equipment_history_stats(
                parsed.equipment_code
            )
        )

    context = _build_context(
        message,
        parsed,
        results,
        evidence,
        equipment_history_stats,
    )

    llm_used = False
    model_name = "deterministic-fallback"

    if parsed.intent == "EQUIPMENT_HISTORY":
        generated = _deterministic_fallback(
            evidence
        )
        model_name = "deterministic-history"
    else:
        try:
            client = get_openrouter_client()
            raw, model_name = await client.generate_structured(
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": (
                            "Analyse le contexte RAG suivant et produis "
                            "une recommandation structurée.\n\n"
                            f"{context}"
                        ),
                    },
                ],
                json_schema=(
                    LLMRecommendation.model_json_schema()
                ),
                schema_name="maintenance_recommendation",
            )

            normalized_raw = _normalize_llm_payload(raw)
            generated = LLMRecommendation.model_validate(
                normalized_raw
            )
            llm_used = True

        except (
            OpenRouterError,
            ValueError,
            TypeError,
        ) as error:
            logger.warning(
                "Échec OpenRouter, utilisation du fallback : %s",
                error,
            )
            generated = _deterministic_fallback(evidence)
            model_name = "deterministic-fallback"
            llm_used = False

    generated = _enrich_generated_from_evidence(
        generated,
        evidence,
    )

    if parsed.intent == "EQUIPMENT_HISTORY":
        generated = _apply_equipment_history_summary(
            generated,
            equipment_history_stats,
        )

    sources = [
        ChatSource(
            reference=result.reference,
            final_score=result.final_score,
            reranker_score=result.reranker_score,
            dense_score=result.dense_score,
            classification=result.classification,
            equipment_code=result.equipment_code,
            equipment_brand=result.equipment_brand,
            equipment_model=result.equipment_model,
            link_trust=result.link_trust,
        )
        for result in results
    ]

    return ChatResponse(
        answer=_compose_answer(generated),
        summary=generated.summary,
        probable_causes=generated.probable_causes,
        recommended_checks=generated.recommended_checks,
        historical_solutions=(
            generated.historical_solutions
        ),
        warnings=generated.warnings,
        confidence=evidence.get(
            "confidence",
            "LOW",
        ),
        confidence_score=int(
            evidence.get(
                "confidence_score",
                0,
            )
        ),
        human_validation_required=True,
        intent=parsed.intent,
        classification_group=(
            parsed.classification_group
        ),
        equipment_code=parsed.equipment_code,
        model=model_name,
        llm_used=llm_used,
        sources=sources,
    )