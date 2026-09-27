from __future__ import annotations

import argparse
import time

from qdrant_client import models

from app.db.session import SessionLocal
from app.rag.onee_indexer import OneeRagIndexer
from app.rag.secure_documents import (
    iter_secure_request_documents,
)


def create_extra_payload_indexes(
    indexer: OneeRagIndexer,
) -> None:
    fields = (
        ("classification_group", models.PayloadSchemaType.KEYWORD),
        ("equipment_brand", models.PayloadSchemaType.KEYWORD),
        ("equipment_model", models.PayloadSchemaType.KEYWORD),
        ("link_trust", models.PayloadSchemaType.KEYWORD),
        ("privacy_version", models.PayloadSchemaType.KEYWORD),
    )

    for field_name, schema in fields:
        try:
            indexer.client.create_payload_index(
                collection_name=indexer.collection_name,
                field_name=field_name,
                field_schema=schema,
            )
        except Exception as error:
            print(f"[INDEX PAYLOAD] {field_name}: {error}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruit la collection RAG avec "
            "anonymisation et métadonnées enrichies."
        )
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recrée entièrement la collection.",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    indexer = OneeRagIndexer()

    print("Collection :", indexer.collection_name)
    print("Modèle embedding :", indexer.embedding_model_name)
    print("Dimension :", indexer.vector_size)
    print("Mode privé : anonymisation v2")

    indexer.ensure_collection(
        recreate=args.recreate
    )
    create_extra_payload_indexes(indexer)

    with SessionLocal() as db:
        total = indexer.index_documents(
            iter_secure_request_documents(db),
            encode_batch_size=64,
            upsert_batch_size=128,
        )

    duration = time.perf_counter() - started

    print()
    print("RECONSTRUCTION SÉCURISÉE TERMINÉE")
    print("=================================")
    print("Documents :", total)
    print("Points Qdrant :", indexer.count_points())
    print(f"Durée : {duration:.1f} seconde(s)")


if __name__ == "__main__":
    main()
