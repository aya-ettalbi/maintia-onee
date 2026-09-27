from __future__ import annotations

from qdrant_client import QdrantClient

from app.rag.onee_indexer import (
    get_collection_name,
    get_qdrant_url,
)


def main() -> None:
    client = QdrantClient(url=get_qdrant_url())
    collection_name = get_collection_name()

    print("Qdrant :", get_qdrant_url())
    print("Collection :", collection_name)

    if not client.collection_exists(collection_name):
        print("Collection absente.")
        return

    info = client.get_collection(collection_name)
    count = client.count(
        collection_name=collection_name,
        exact=True,
    ).count

    print("Statut :", info.status)
    print("Points :", count)
    print("Dimension :", info.config.params.vectors.size)
    print("Distance :", info.config.params.vectors.distance)


if __name__ == "__main__":
    main()
