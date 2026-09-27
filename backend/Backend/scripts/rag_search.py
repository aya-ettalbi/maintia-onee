from __future__ import annotations

import argparse
from pprint import pprint

from app.rag.embeddings import embed_query
from app.rag.vector_store import search_documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Recherche dans le RAG ONEE")
    parser.add_argument("question", nargs="?", default="ordinateur avec écran noir")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=0.30)
    args = parser.parse_args()

    results = search_documents(
        embed_query(args.question),
        limit=args.limit,
        min_score=args.min_score,
    )
    print("\nQUESTION")
    print(args.question)
    print("\nRÉSULTATS")
    pprint(results)


if __name__ == "__main__":
    main()
