from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from app.rag.intelligent_retriever import (
    IntelligentRetriever,
)
from app.services.recommendation_evidence import (
    build_recommendation_evidence,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Teste la recherche intelligente "
            "avec reranking."
        )
    )
    parser.add_argument("question")
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--final-k",
        type=int,
        default=8,
    )
    args = parser.parse_args()

    retriever = IntelligentRetriever()

    print("Reranker :", retriever.reranker_model_name)
    print("Chargement terminé.")
    print()

    parsed, results = retriever.search(
        args.question,
        candidate_k=args.candidate_k,
        final_k=args.final_k,
    )

    print("COMPRÉHENSION DE LA QUESTION")
    print("============================")
    print(
        json.dumps(
            asdict(parsed),
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("RÉSULTATS RERANKÉS")
    print("==================")

    for index, result in enumerate(results, start=1):
        print()
        print("-" * 72)
        print(f"RÉSULTAT {index}")
        print("Référence :", result.reference)
        print("Score final :", result.final_score)
        print("Score reranker :", result.reranker_score)
        print("Score Qdrant :", result.dense_score)
        print("Score lexical :", result.lexical_score)
        print("Classification :", result.classification)
        print("Groupe :", result.classification_group)
        print("Équipement :", result.equipment_code)
        print("Marque :", result.equipment_brand)
        print("Modèle :", result.equipment_model)
        print("Fiabilité lien :", result.link_trust)
        print("Cause :", result.cause)
        print("Solution :", result.solution)

    evidence = build_recommendation_evidence(
        args.question,
        results,
    )

    print()
    print("PAQUET DE PREUVES POUR LE FUTUR LLM")
    print("===================================")
    print(
        json.dumps(
            evidence,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
