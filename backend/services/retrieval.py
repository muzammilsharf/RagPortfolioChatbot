from __future__ import annotations

from dataclasses import dataclass
import re

from database import get_chroma


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    source: str
    score: float


class VectorStoreRepository:
    """
    Repository abstraction so swapping Chroma -> Pinecone/etc is config-level later.
    """

    def similarity_search(self, query_embedding: list[float], *, top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        *,
        top_k: int,
        candidate_k: int,
        vector_weight: float,
        keyword_weight: float,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "at",
    "by",
    "from",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "it",
    "this",
    "that",
    "i",
    "you",
    "we",
    "they",
    "my",
    "your",
    "our",
    "their",
}


def _keywords(query: str) -> list[str]:
    toks = [t.lower() for t in re.findall(r"[a-zA-Z0-9_+-]{2,}", query)]
    toks = [t for t in toks if t not in _STOPWORDS]
    uniq: list[str] = []
    for t in toks:
        if t not in uniq:
            uniq.append(t)
        if len(uniq) >= 8:
            break
    return uniq


def _keyword_score(text: str, kws: list[str]) -> float:
    if not kws:
        return 0.0
    hay = text.lower()
    hits = sum(1 for k in kws if k in hay)
    return hits / max(1, len(kws))


class ChromaVectorStoreRepository(VectorStoreRepository):
    def similarity_search(self, query_embedding: list[float], *, top_k: int) -> list[RetrievedChunk]:
        chroma = get_chroma()
        res = chroma.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        out: list[RetrievedChunk] = []
        for i, doc, meta, dist in zip(ids, docs, metas, dists, strict=False):
            # Chroma distance is smaller=closer for cosine in HNSW; convert to similarity-ish.
            score = 1.0 - float(dist) if dist is not None else 0.0
            source = ""
            if isinstance(meta, dict):
                source = str(meta.get("source", ""))
            out.append(RetrievedChunk(id=str(i), text=str(doc), source=source, score=score))
        return out

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        *,
        top_k: int,
        candidate_k: int,
        vector_weight: float,
        keyword_weight: float,
    ) -> list[RetrievedChunk]:
        chroma = get_chroma()
        kws = _keywords(query_text)

        # 1) Semantic candidates
        semantic = self.similarity_search(query_embedding, top_k=max(candidate_k, top_k))
        sem_map = {c.id: c for c in semantic}

        # 2) Lexical candidates (helps names/tech keywords). Keep small for latency.
        lexical: dict[str, RetrievedChunk] = {}
        for kw in kws[:3]:
            try:
                got = chroma.collection.get(
                    where_document={"$contains": kw},
                    include=["documents", "metadatas"],
                    limit=min(20, candidate_k),
                )
            except Exception:
                continue

            ids = got.get("ids") or []
            docs = got.get("documents") or []
            metas = got.get("metadatas") or []
            for i, doc, meta in zip(ids, docs, metas, strict=False):
                source = ""
                if isinstance(meta, dict):
                    source = str(meta.get("source", ""))
                lexical[str(i)] = RetrievedChunk(id=str(i), text=str(doc), source=source, score=0.0)

        # Merge pool
        pool: dict[str, RetrievedChunk] = {}
        for c in semantic:
            pool[c.id] = c
        for cid, c in lexical.items():
            pool.setdefault(cid, c)

        # Rerank by weighted hybrid score
        out: list[RetrievedChunk] = []
        for cid, c in pool.items():
            sem = sem_map.get(cid).score if cid in sem_map else 0.0
            lex = _keyword_score(c.text, kws)
            score = (vector_weight * sem) + (keyword_weight * lex)
            out.append(RetrievedChunk(id=cid, text=c.text, source=c.source, score=score))

        out.sort(key=lambda x: x.score, reverse=True)
        return out[:top_k]
