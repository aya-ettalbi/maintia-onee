from __future__ import annotations

import os
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Iterator, Sequence

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_core import EquipmentHistoricalLink
from app.models.equipment import Equipment
from app.models.historical import HistoricalRequest, HistoricalTask


DEFAULT_COLLECTION = "maintenance_onee_rag"
DEFAULT_QDRANT_URL = "http://127.0.0.1:6333"
DEFAULT_EMBEDDING_MODEL = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)
POINT_NAMESPACE = uuid.UUID("b854cf81-dacc-4ebc-809e-b9806a3272c8")


@dataclass(frozen=True)
class RagDocument:
    point_id: str
    text: str
    payload: dict


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _date_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _safe_settings_value(name: str, fallback: str) -> str:
    """
    Lit d'abord app.core.config.settings, puis l'environnement,
    puis une valeur par défaut.
    """
    try:
        from app.core.config import settings

        value = getattr(settings, name, None)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, fallback)


def get_qdrant_url() -> str:
    return _safe_settings_value(
        "QDRANT_URL",
        DEFAULT_QDRANT_URL,
    )


def get_collection_name() -> str:
    return _safe_settings_value(
        "QDRANT_COLLECTION",
        DEFAULT_COLLECTION,
    )


def get_embedding_model_name() -> str:
    return _safe_settings_value(
        "EMBEDDING_MODEL",
        DEFAULT_EMBEDDING_MODEL,
    )


def make_point_id(source_type: str, source_id: str) -> str:
    return str(
        uuid.uuid5(
            POINT_NAMESPACE,
            f"{source_type}:{source_id}",
        )
    )


def load_tasks_by_request(
    db: Session,
) -> dict[str, list[HistoricalTask]]:
    """
    Charge les tâches une seule fois puis les regroupe par numéro de demande.
    Cela évite une requête SQL pour chaque demande.
    """
    grouped: dict[str, list[HistoricalTask]] = defaultdict(list)

    tasks = db.scalars(
        select(HistoricalTask).order_by(
            HistoricalTask.numero_demande,
            HistoricalTask.date_creation_tache,
            HistoricalTask.id,
        )
    ).all()

    for task in tasks:
        if task.numero_demande:
            grouped[task.numero_demande].append(task)

    return grouped


def load_equipment_by_request_id(
    db: Session,
) -> dict[int, Equipment]:
    """
    Charge uniquement les liens validés automatiquement ou manuellement.
    """
    rows = db.execute(
        select(
            EquipmentHistoricalLink.historical_request_id,
            Equipment,
        )
        .join(
            Equipment,
            Equipment.id == EquipmentHistoricalLink.equipment_id,
        )
        .where(
            EquipmentHistoricalLink.validation_status.in_(
                ["AUTO", "VALIDE"]
            )
        )
    ).all()

    result: dict[int, Equipment] = {}

    for historical_request_id, equipment in rows:
        result[historical_request_id] = equipment

    return result


def build_task_text(tasks: Sequence[HistoricalTask]) -> str:
    parts: list[str] = []

    for index, task in enumerate(tasks[:20], start=1):
        detail = " | ".join(
            item
            for item in [
                _clean(task.description_tache),
                _clean(task.classification_tache),
                _clean(task.motif_rejet),
            ]
            if item
        )

        if detail:
            parts.append(f"Tâche {index}: {detail}")

    if len(tasks) > 20:
        parts.append(
            f"{len(tasks) - 20} tâche(s) supplémentaire(s) non affichée(s)."
        )

    return "\n".join(parts)


def build_request_document(
    request: HistoricalRequest,
    tasks: Sequence[HistoricalTask],
    equipment: Equipment | None,
) -> RagDocument:
    """
    Construit un document technique sans email, nom complet ni matricule.
    """
    lines = [
        "Type de source: demande historique de maintenance",
        f"Référence demande: {_clean(request.numero_demande)}",
    ]

    if request.date_creation_demande:
        lines.append(
            "Date de création: "
            f"{request.date_creation_demande.date().isoformat()}"
        )

    for label, value in [
        ("Nature", request.nature_demande),
        ("Classification", request.classification),
        ("Détail classification", request.detail_classification),
        ("Description", request.description_demande),
        ("Symptôme", request.symptome),
        ("Cause", request.cause),
        ("Solution", request.solution),
        ("Statut", request.statut),
    ]:
        clean_value = _clean(value)
        if clean_value:
            lines.append(f"{label}: {clean_value}")

    if equipment is not None:
        lines.extend(
            [
                f"Équipement code: {_clean(equipment.code)}",
                f"Équipement marque: {_clean(equipment.brand)}",
                f"Équipement modèle: {_clean(equipment.model)}",
                f"Équipement numéro de série: {_clean(equipment.serial_number)}",
                f"Équipement statut: {_clean(equipment.status)}",
            ]
        )

    task_text = build_task_text(tasks)
    if task_text:
        lines.append("Actions et tâches historiques:")
        lines.append(task_text)

    text = "\n".join(line for line in lines if line.strip())

    payload = {
        "source_type": "historical_request",
        "source_id": str(request.id),
        "reference": request.numero_demande,
        "numero_demande": request.numero_demande,
        "classification": request.classification,
        "detail_classification": request.detail_classification,
        "nature_demande": request.nature_demande,
        "statut": request.statut,
        "created_at": _date_to_iso(request.date_creation_demande),
        "resolved_at": _date_to_iso(request.date_resolution_demande),
        "equipment_id": equipment.id if equipment else None,
        "equipment_code": equipment.code if equipment else None,
        "equipment_brand": equipment.brand if equipment else None,
        "equipment_model": equipment.model if equipment else None,
        "task_count": len(tasks),
        "content": text,
    }

    return RagDocument(
        point_id=make_point_id(
            "historical_request",
            str(request.id),
        ),
        text=text,
        payload=payload,
    )


def iter_request_documents(
    db: Session,
) -> Iterator[RagDocument]:
    tasks_by_request = load_tasks_by_request(db)
    equipment_by_request = load_equipment_by_request_id(db)

    requests = db.scalars(
        select(HistoricalRequest).order_by(
            HistoricalRequest.id
        )
    ).all()

    for request in requests:
        tasks = tasks_by_request.get(
            request.numero_demande,
            [],
        )
        equipment = equipment_by_request.get(request.id)

        yield build_request_document(
            request,
            tasks,
            equipment,
        )


def batched(
    values: Iterable[RagDocument],
    batch_size: int,
) -> Iterator[list[RagDocument]]:
    batch: list[RagDocument] = []

    for value in values:
        batch.append(value)
        if len(batch) >= batch_size:
            yield batch
            batch = []

    if batch:
        yield batch


class OneeRagIndexer:
    def __init__(
        self,
        *,
        qdrant_url: str | None = None,
        collection_name: str | None = None,
        embedding_model_name: str | None = None,
    ) -> None:
        self.qdrant_url = qdrant_url or get_qdrant_url()
        self.collection_name = (
            collection_name or get_collection_name()
        )
        self.embedding_model_name = (
            embedding_model_name or get_embedding_model_name()
        )

        self.client = QdrantClient(url=self.qdrant_url)
        self.model = SentenceTransformer(
            self.embedding_model_name
        )
        self.vector_size = int(
            self.model.get_sentence_embedding_dimension()
        )

    def collection_exists(self) -> bool:
        try:
            return bool(
                self.client.collection_exists(
                    self.collection_name
                )
            )
        except AttributeError:
            try:
                self.client.get_collection(
                    self.collection_name
                )
                return True
            except Exception:
                return False

    def ensure_collection(
        self,
        *,
        recreate: bool = False,
    ) -> None:
        exists = self.collection_exists()

        if recreate and exists:
            self.client.delete_collection(
                collection_name=self.collection_name
            )
            exists = False

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="source_type",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="reference",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="equipment_id",
                field_schema=models.PayloadSchemaType.INTEGER,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="equipment_code",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="classification",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

    def index_documents(
        self,
        documents: Iterable[RagDocument],
        *,
        encode_batch_size: int = 64,
        upsert_batch_size: int = 128,
        show_progress: bool = True,
    ) -> int:
        indexed = 0

        for batch_number, document_batch in enumerate(
            batched(documents, upsert_batch_size),
            start=1,
        ):
            texts = [
                document.text
                for document in document_batch
            ]
            vectors = self.model.encode(
                texts,
                batch_size=encode_batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            points = [
                models.PointStruct(
                    id=document.point_id,
                    vector=vector.tolist(),
                    payload=document.payload,
                )
                for document, vector in zip(
                    document_batch,
                    vectors,
                    strict=True,
                )
            ]

            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )

            indexed += len(points)

            if show_progress:
                print(
                    f"[QDRANT] Lot {batch_number} "
                    f"| total indexé: {indexed}"
                )

        return indexed

    def count_points(self) -> int:
        result = self.client.count(
            collection_name=self.collection_name,
            exact=True,
        )
        return int(result.count)

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        equipment_id: int | None = None,
        score_threshold: float | None = None,
    ) -> list:
        query_vector = self.model.encode(
            [query],
            normalize_embeddings=True,
        )[0].tolist()

        query_filter = None
        if equipment_id is not None:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="equipment_id",
                        match=models.MatchValue(
                            value=equipment_id
                        ),
                    )
                ]
            )

        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                score_threshold=score_threshold,
            )
            return list(response.points)

        return list(
            self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                score_threshold=score_threshold,
            )
        )
