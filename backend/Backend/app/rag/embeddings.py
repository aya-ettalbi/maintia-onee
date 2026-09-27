from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    print(f"[RAG] Chargement du modèle : {settings.RAG_EMBEDDING_MODEL}")
    return SentenceTransformer(settings.RAG_EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    clean_texts = [text.strip() for text in texts if isinstance(text, str) and text.strip()]
    if not clean_texts:
        return []

    vectors = get_embedding_model().encode(
        clean_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
        batch_size=settings.RAG_BATCH_SIZE,
    )
    return vectors.astype("float32").tolist()


def embed_query(question: str) -> list[float]:
    question = question.strip()
    if not question:
        raise ValueError("La question ne peut pas être vide.")
    return embed_texts([question])[0]


def embedding_dimension() -> int:
    model = get_embedding_model()
    if hasattr(model, "get_embedding_dimension"):
        dimension = model.get_embedding_dimension()
    else:
        dimension = model.get_sentence_embedding_dimension()
    return int(dimension or len(embed_query("test")))
