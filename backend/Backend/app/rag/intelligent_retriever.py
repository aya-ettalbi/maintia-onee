from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Iterable

import numpy as np
from qdrant_client import models
from sentence_transformers import CrossEncoder

from app.rag.onee_indexer import OneeRagIndexer
from app.rag.privacy import normalize_for_matching
from app.rag.query_understanding import ParsedQuery, parse_query


DEFAULT_RERANKER_MODEL = (
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)


@dataclass(frozen=True)
class IntelligentResult:
    point_id: str
    reference: str | None
    final_score: float
    reranker_score: float
    reranker_raw: float
    dense_score: float
    lexical_score: float
    classification_group: str | None
    classification: str | None
    equipment_id: int | None
    equipment_code: str | None
    equipment_brand: str | None
    equipment_model: str | None
    link_trust: str | None
    cause: str | None
    solution: str | None
    symptom: str | None
    created_at: str | None
    content: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _minmax(values: Iterable[float]) -> list[float]:
    values_list = [float(value) for value in values]
    if not values_list:
        return []

    minimum = min(values_list)
    maximum = max(values_list)

    if math.isclose(minimum, maximum):
        return [1.0 for _ in values_list]

    return [
        (value - minimum) / (maximum - minimum)
        for value in values_list
    ]


def _lexical_overlap(
    query: ParsedQuery,
    content: str,
) -> float:
    query_terms = set(query.keywords)
    if not query_terms:
        return 0.0

    document_terms = set(
        normalize_for_matching(content).split()
    )
    overlap = query_terms & document_terms
    return len(overlap) / len(query_terms)


def _parse_date(value: object) -> datetime:
    if not value:
        return datetime.min

    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.min


class IntelligentRetriever:
    """
    Recherche en deux étapes :

    1. Bi-encoder + Qdrant pour récupérer rapidement des candidats.
    2. Cross-Encoder pour réordonner précisément les candidats.

    Les logits du Cross-Encoder sont normalisés relativement au lot courant.
    Cela évite de traiter un score brut faible comme une mauvaise réponse alors
    que le premier document reste nettement meilleur que les autres.
    """

    def __init__(
        self,
        *,
        reranker_model: str | None = None,
    ) -> None:
        self.indexer = OneeRagIndexer()
        self.reranker_model_name = (
            reranker_model
            or os.getenv(
                "RAG_RERANKER_MODEL",
                DEFAULT_RERANKER_MODEL,
            )
        )
        self.reranker = CrossEncoder(
            self.reranker_model_name
        )

    def _query_qdrant(
        self,
        query: str,
        *,
        limit: int,
        parsed: ParsedQuery,
        use_business_filter: bool,
    ) -> list:
        vector = self.indexer.model.encode(
            [query],
            normalize_embeddings=True,
        )[0].tolist()

        must_conditions = [
            models.FieldCondition(
                key="source_type",
                match=models.MatchValue(
                    value="historical_request"
                ),
            )
        ]

        if parsed.equipment_code:
            must_conditions.append(
                models.FieldCondition(
                    key="equipment_code",
                    match=models.MatchValue(
                        value=parsed.equipment_code,
                    ),
                )
            )
        elif (
            use_business_filter
            and parsed.classification_group
        ):
            must_conditions.append(
                models.FieldCondition(
                    key="classification_group",
                    match=models.MatchValue(
                        value=parsed.classification_group,
                    ),
                )
            )

        response = self.indexer.client.query_points(
            collection_name=self.indexer.collection_name,
            query=vector,
            query_filter=models.Filter(
                must=must_conditions
            ),
            limit=limit,
            with_payload=True,
        )
        return list(response.points)

    def _retrieve_candidates(
        self,
        query: str,
        parsed: ParsedQuery,
        candidate_k: int,
    ) -> list:
        merged: dict[str, Any] = {}

        for point in self._query_qdrant(
            query,
            limit=max(candidate_k, 20),
            parsed=parsed,
            use_business_filter=True,
        ):
            merged[str(point.id)] = point

        # Recherche générale de secours uniquement lorsqu'aucun code exact
        # n'est demandé. Pour un équipement exact, on ne mélange pas les autres.
        if not parsed.equipment_code:
            for point in self._query_qdrant(
                query,
                limit=max(10, candidate_k // 2),
                parsed=parsed,
                use_business_filter=False,
            ):
                key = str(point.id)
                current = merged.get(key)
                if (
                    current is None
                    or float(point.score) > float(current.score)
                ):
                    merged[key] = point

        return sorted(
            merged.values(),
            key=lambda point: float(point.score),
            reverse=True,
        )[:candidate_k]

    def _history_results(
        self,
        points: list,
        *,
        final_k: int,
    ) -> list[IntelligentResult]:
        points = sorted(
            points,
            key=lambda point: _parse_date(
                (point.payload or {}).get("created_at")
            ),
            reverse=True,
        )

        results: list[IntelligentResult] = []

        for point in points[:final_k]:
            payload = dict(point.payload or {})
            trust_score = {
                "HIGH": 1.0,
                "MEDIUM": 0.85,
                "LOW": 0.60,
                None: 0.75,
            }.get(payload.get("link_trust"), 0.75)

            results.append(
                IntelligentResult(
                    point_id=str(point.id),
                    reference=payload.get("reference"),
                    final_score=trust_score,
                    reranker_score=0.0,
                    reranker_raw=0.0,
                    dense_score=round(float(point.score), 4),
                    lexical_score=0.0,
                    classification_group=payload.get(
                        "classification_group"
                    ),
                    classification=payload.get(
                        "classification"
                    ),
                    equipment_id=payload.get("equipment_id"),
                    equipment_code=payload.get("equipment_code"),
                    equipment_brand=payload.get("equipment_brand"),
                    equipment_model=payload.get("equipment_model"),
                    link_trust=payload.get("link_trust"),
                    cause=payload.get("cause"),
                    solution=payload.get("solution"),
                    symptom=payload.get("symptome"),
                    created_at=payload.get("created_at"),
                    content=str(payload.get("content", "")),
                    payload=payload,
                )
            )

        return results

    def search(
        self,
        query: str,
        *,
        candidate_k: int = 30,
        final_k: int = 8,
    ) -> tuple[ParsedQuery, list[IntelligentResult]]:
        parsed = parse_query(query)
        candidates = self._retrieve_candidates(
            query,
            parsed,
            candidate_k,
        )

        if not candidates:
            return parsed, []

        if parsed.intent == "EQUIPMENT_HISTORY":
            return parsed, self._history_results(
                candidates,
                final_k=final_k,
            )

        pairs = [
            (
                query,
                str(
                    (point.payload or {}).get(
                        "content",
                        "",
                    )
                ),
            )
            for point in candidates
        ]

        raw_scores = np.asarray(
            self.reranker.predict(
                pairs,
                batch_size=16,
                show_progress_bar=False,
            ),
            dtype=float,
        ).reshape(-1)

        reranker_scores = _minmax(raw_scores)
        dense_normalized = _minmax(
            float(point.score)
            for point in candidates
        )

        ranked: list[IntelligentResult] = []

        for point, raw_score, reranker_score, dense_norm in zip(
            candidates,
            raw_scores,
            reranker_scores,
            dense_normalized,
            strict=True,
        ):
            payload = dict(point.payload or {})
            content = str(payload.get("content", ""))
            lexical_score = _lexical_overlap(
                parsed,
                content,
            )

            category_bonus = 0.0
            if (
                parsed.classification_group
                and payload.get("classification_group")
                == parsed.classification_group
            ):
                category_bonus = 0.05

            equipment_bonus = 0.0
            if (
                parsed.equipment_code
                and payload.get("equipment_code")
                == parsed.equipment_code
            ):
                equipment_bonus = 0.10

            trust_adjustment = {
                "HIGH": 0.03,
                "MEDIUM": 0.0,
                "LOW": -0.05,
                None: 0.0,
            }.get(payload.get("link_trust"), 0.0)

            final_score = (
                0.55 * float(reranker_score)
                + 0.25 * float(dense_norm)
                + 0.15 * float(lexical_score)
                + category_bonus
                + equipment_bonus
                + trust_adjustment
            )
            final_score = max(
                0.0,
                min(1.0, final_score),
            )

            ranked.append(
                IntelligentResult(
                    point_id=str(point.id),
                    reference=payload.get("reference"),
                    final_score=round(final_score, 4),
                    reranker_score=round(
                        float(reranker_score),
                        4,
                    ),
                    reranker_raw=round(
                        float(raw_score),
                        4,
                    ),
                    dense_score=round(
                        float(point.score),
                        4,
                    ),
                    lexical_score=round(
                        lexical_score,
                        4,
                    ),
                    classification_group=payload.get(
                        "classification_group"
                    ),
                    classification=payload.get(
                        "classification"
                    ),
                    equipment_id=payload.get("equipment_id"),
                    equipment_code=payload.get("equipment_code"),
                    equipment_brand=payload.get("equipment_brand"),
                    equipment_model=payload.get("equipment_model"),
                    link_trust=payload.get("link_trust"),
                    cause=payload.get("cause"),
                    solution=payload.get("solution"),
                    symptom=payload.get("symptome"),
                    created_at=payload.get("created_at"),
                    content=content,
                    payload=payload,
                )
            )

        ranked.sort(
            key=lambda result: result.final_score,
            reverse=True,
        )
        return parsed, ranked[:final_k]
