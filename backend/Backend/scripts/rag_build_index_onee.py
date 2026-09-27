from __future__ import annotations

import argparse
import time

from app.db.session import SessionLocal
from app.rag.onee_indexer import (
    OneeRagIndexer,
    iter_request_documents,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Construit l'index RAG ONEE dans Qdrant."
        )
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Supprime et recrée la collection.",
    )
    parser.add_argument(
        "--encode-batch-size",
        type=int,
        default=64,
    )
    parser.add_argument(
        "--upsert-batch-size",
        type=int,
        default=128,
    )
    args = parser.parse_args()

    started = time.perf_counter()
    indexer = OneeRagIndexer()

    print("Qdrant :", indexer.qdrant_url)
    print("Collection :", indexer.collection_name)
    print("Modèle :", indexer.embedding_model_name)
    print("Dimension :", indexer.vector_size)

    indexer.ensure_collection(
        recreate=args.recreate
    )

    with SessionLocal() as db:
        indexed = indexer.index_documents(
            iter_request_documents(db),
            encode_batch_size=args.encode_batch_size,
            upsert_batch_size=args.upsert_batch_size,
        )

    elapsed = time.perf_counter() - started

    print()
    print("INDEXATION TERMINÉE")
    print("===================")
    print("Documents indexés :", indexed)
    print("Points Qdrant :", indexer.count_points())
    print(f"Durée : {elapsed:.1f} seconde(s)")


if __name__ == "__main__":
    main()
