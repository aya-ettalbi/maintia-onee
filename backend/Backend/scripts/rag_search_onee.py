from __future__ import annotations

import argparse

from app.rag.onee_indexer import OneeRagIndexer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Teste la recherche RAG ONEE."
    )
    parser.add_argument(
        "question",
        help="Question technique à rechercher.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--equipment-id",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=None,
    )
    args = parser.parse_args()

    indexer = OneeRagIndexer()
    results = indexer.search(
        args.question,
        limit=args.limit,
        equipment_id=args.equipment_id,
        score_threshold=args.score_threshold,
    )

    print(f"Question : {args.question}")
    print(f"Résultats : {len(results)}")
    print()

    for position, point in enumerate(results, start=1):
        payload = point.payload or {}

        print("=" * 70)
        print(f"RÉSULTAT {position}")
        print("Score :", round(float(point.score), 4))
        print("Référence :", payload.get("reference"))
        print("Classification :", payload.get("classification"))
        print("Équipement :", payload.get("equipment_code"))
        print("Marque :", payload.get("equipment_brand"))
        print("Modèle :", payload.get("equipment_model"))
        print("Tâches :", payload.get("task_count"))
        print()
        print(payload.get("content", "")[:1800])
        print()


if __name__ == "__main__":
    main()
