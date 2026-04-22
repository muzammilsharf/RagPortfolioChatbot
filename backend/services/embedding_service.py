from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def embed_query(text: str) -> list[float]:
    vec = _model().encode([text], normalize_embeddings=True)[0]
    return vec.tolist()
