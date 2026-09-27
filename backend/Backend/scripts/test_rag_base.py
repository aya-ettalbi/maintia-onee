from pprint import pprint

from app.rag.embeddings import (
    embed_query,
    embed_texts,
)
from app.rag.vector_store import (
    search_documents,
    upsert_documents,
)


documents = [
    {
        "source_type": "test_request",
        "source_id": 1,
        "reference": "REQ-TEST-001",
        "title": "Écran noir au démarrage",
        "content": (
            "Ordinateur avec écran noir au démarrage. "
            "Cause observée : mémoire RAM mal installée. "
            "Solution : retirer, nettoyer puis réinstaller "
            "les barrettes de mémoire RAM."
        ),
        "status": "RESOLU",
    },
    {
        "source_type": "test_request",
        "source_id": 2,
        "reference": "REQ-TEST-002",
        "title": "Bourrage papier imprimante",
        "content": (
            "Imprimante avec bourrage papier. "
            "Cause : papier bloqué dans les rouleaux. "
            "Solution : retirer le papier et nettoyer "
            "les rouleaux d'entraînement."
        ),
        "status": "RESOLU",
    },
    {
        "source_type": "test_request",
        "source_id": 3,
        "reference": "REQ-TEST-003",
        "title": "Connexion réseau indisponible",
        "content": (
            "Le poste ne peut pas accéder au réseau. "
            "Cause : câble Ethernet endommagé. "
            "Solution : remplacement du câble réseau."
        ),
        "status": "RESOLU",
    },
]


def main() -> None:
    vectors = embed_texts(
        [document["content"] for document in documents]
    )

    upsert_documents(
        documents=documents,
        vectors=vectors,
    )

    question = (
        "Que faire pour un ordinateur "
        "qui affiche un écran noir ?"
    )

    question_vector = embed_query(question)

    results = search_documents(
        vector=question_vector,
        limit=3,
    )

    print("\nQUESTION")
    print(question)

    print("\nRÉSULTATS RAG")
    pprint(results)


if __name__ == "__main__":
    main()
