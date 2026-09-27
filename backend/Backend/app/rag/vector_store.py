from functools import lru_cache
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.rag.embeddings import embedding_dimension


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


def collection_exists() -> bool:
    names = {item.name for item in get_qdrant_client().get_collections().collections}
    return settings.QDRANT_COLLECTION in names


def ensure_collection() -> None:
    if collection_exists():
        return
    get_qdrant_client().create_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config=VectorParams(size=embedding_dimension(), distance=Distance.COSINE),
    )
    print(f"[RAG] Collection créée : {settings.QDRANT_COLLECTION}")


def reset_collection() -> None:
    client = get_qdrant_client()
    if collection_exists():
        client.delete_collection(settings.QDRANT_COLLECTION)
    client.create_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config=VectorParams(size=embedding_dimension(), distance=Distance.COSINE),
    )
    print(f"[RAG] Collection recréée : {settings.QDRANT_COLLECTION}")


def make_point_id(source_type: str, source_id: int | str) -> str:
    return str(uuid5(NAMESPACE_URL, f"maintenance-onee:{source_type}:{source_id}"))


def upsert_documents(documents: list[dict], vectors: list[list[float]]) -> None:
    if len(documents) != len(vectors):
        raise ValueError("Le nombre de documents et de vecteurs doit être identique.")
    if not documents:
        return
    ensure_collection()
    points = [
        PointStruct(
            id=make_point_id(str(document["source_type"]), document["source_id"]),
            vector=vector,
            payload=document,
        )
        for document, vector in zip(documents, vectors)
    ]
    get_qdrant_client().upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=points,
        wait=True,
    )


def search_documents(vector: list[float], limit: int = 8, min_score: float | None = None) -> list[dict]:
    ensure_collection()
    threshold = settings.RAG_MIN_SCORE if min_score is None else min_score
    response = get_qdrant_client().query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=vector,
        limit=limit,
        with_payload=True,
    )
    results = []
    for point in response.points:
        if float(point.score) < threshold:
            continue
        payload = dict(point.payload or {})
        payload["similarity"] = float(point.score)
        results.append(payload)
    return results


def collection_points_count() -> int:
    ensure_collection()
    info = get_qdrant_client().get_collection(settings.QDRANT_COLLECTION)
    return int(info.points_count or 0)
