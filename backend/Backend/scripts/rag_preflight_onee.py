from __future__ import annotations

import importlib
from sqlalchemy import text

from app.db.session import engine
from app.rag.onee_indexer import OneeRagIndexer


def package_version(package: str) -> str:
    module = importlib.import_module(package)
    return str(getattr(module, "__version__", "inconnue"))


def main() -> None:
    print("Versions")
    print("--------")
    print("qdrant_client :", package_version("qdrant_client"))
    print(
        "sentence_transformers :",
        package_version("sentence_transformers"),
    )

    with engine.connect() as connection:
        print()
        print("PostgreSQL")
        print("----------")
        print(
            "Base :",
            connection.execute(
                text("SELECT current_database()")
            ).scalar(),
        )
        print(
            "Demandes historiques :",
            connection.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM historical_requests"
                )
            ).scalar(),
        )
        print(
            "Liens équipement-historique :",
            connection.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM equipment_historical_links"
                )
            ).scalar(),
        )

    indexer = OneeRagIndexer()

    print()
    print("RAG")
    print("---")
    print("URL Qdrant :", indexer.qdrant_url)
    print("Collection :", indexer.collection_name)
    print("Modèle :", indexer.embedding_model_name)
    print("Dimension :", indexer.vector_size)
    print(
        "Collection existante :",
        indexer.collection_exists(),
    )


if __name__ == "__main__":
    main()
