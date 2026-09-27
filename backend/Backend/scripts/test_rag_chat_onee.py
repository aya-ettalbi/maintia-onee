from __future__ import annotations

import argparse
import asyncio
import json

from app.services.rag_chat import answer_with_rag


async def run(
    question: str,
    candidate_k: int,
    top_k: int,
) -> None:
    response = await answer_with_rag(
        message=question,
        candidate_k=candidate_k,
        top_k=top_k,
    )

    print(
        json.dumps(
            response.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Teste le chatbot RAG + OpenRouter "
            "sans passer par FastAPI."
        )
    )
    parser.add_argument("question")
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=6,
    )
    args = parser.parse_args()

    asyncio.run(
        run(
            args.question,
            args.candidate_k,
            args.top_k,
        )
    )


if __name__ == "__main__":
    main()
