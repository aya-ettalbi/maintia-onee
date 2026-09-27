from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Iterable

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.historical import (
    HistoricalITSupply,
    HistoricalOfficeSupply,
    HistoricalRequest,
    HistoricalSecurityIncident,
    HistoricalTask,
)
from app.rag.documents import (
    historical_it_supply_document,
    historical_office_supply_document,
    historical_request_document,
    historical_security_document,
    historical_task_document,
)
from app.rag.embeddings import embed_texts
from app.rag.vector_store import (
    collection_points_count,
    ensure_collection,
    reset_collection,
    upsert_documents,
)


def index_batches(documents: Iterable[dict], label: str) -> int:
    batch: list[dict] = []
    total = 0

    for document in documents:
        if not document.get("content", "").strip():
            continue
        batch.append(document)

        if len(batch) >= settings.RAG_BATCH_SIZE:
            vectors = embed_texts([item["content"] for item in batch])
            upsert_documents(batch, vectors)
            total += len(batch)
            print(f"[RAG] {label} : {total} document(s)")
            batch.clear()

    if batch:
        vectors = embed_texts([item["content"] for item in batch])
        upsert_documents(batch, vectors)
        total += len(batch)
        print(f"[RAG] {label} : {total} document(s)")

    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexation historique PostgreSQL vers Qdrant")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    reset_collection() if args.reset else ensure_collection()
    totals: dict[str, int] = {}

    with SessionLocal() as db:
        tasks = db.scalars(select(HistoricalTask).order_by(HistoricalTask.id)).all()
        tasks_by_request: dict[str, list[HistoricalTask]] = defaultdict(list)
        for task in tasks:
            key = (task.numero_demande or "").strip()
            if key:
                tasks_by_request[key].append(task)

        requests = db.scalars(select(HistoricalRequest).order_by(HistoricalRequest.id)).all()
        request_numbers = {(item.numero_demande or "").strip() for item in requests}

        totals["historical_requests"] = index_batches(
            (
                historical_request_document(
                    item,
                    tasks_by_request.get((item.numero_demande or "").strip(), []),
                )
                for item in requests
            ),
            "Demandes historiques",
        )

        orphan_tasks = [
            task for task in tasks
            if not (task.numero_demande or "").strip()
            or (task.numero_demande or "").strip() not in request_numbers
        ]
        totals["orphan_tasks"] = index_batches(
            (historical_task_document(item) for item in orphan_tasks),
            "Tâches historiques sans demande",
        )

        it_items = db.scalars(select(HistoricalITSupply).order_by(HistoricalITSupply.id)).all()
        totals["it_supplies"] = index_batches(
            (historical_it_supply_document(item) for item in it_items),
            "Fournitures informatiques",
        )

        office_items = db.scalars(select(HistoricalOfficeSupply).order_by(HistoricalOfficeSupply.id)).all()
        totals["office_supplies"] = index_batches(
            (historical_office_supply_document(item) for item in office_items),
            "Fournitures de bureau",
        )

        security_items = db.scalars(
            select(HistoricalSecurityIncident).order_by(HistoricalSecurityIncident.id)
        ).all()
        totals["security_incidents"] = index_batches(
            (historical_security_document(item) for item in security_items),
            "Incidents Himaya",
        )

    print("\n" + "=" * 68)
    print("RAPPORT D'INDEXATION HISTORIQUE")
    print("=" * 68)
    for name, count in totals.items():
        print(f"{name:<40} {count:>8}")
    print("-" * 68)
    print(f"{'Documents Qdrant':<40} {collection_points_count():>8}")
    print("=" * 68)


if __name__ == "__main__":
    main()
