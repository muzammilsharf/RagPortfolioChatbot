from __future__ import annotations

import hashlib
from pathlib import Path

from sentence_transformers import SentenceTransformer

from core import settings
from database import get_chroma
from utils import chunk_text_semantic, extract_pdf_text


class Embedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]


def _doc_id(source: str, chunk_index: int, text: str) -> str:
    h = hashlib.sha256()
    h.update(source.encode("utf-8"))
    h.update(b":")
    h.update(str(chunk_index).encode("utf-8"))
    h.update(b":")
    h.update(text.encode("utf-8"))
    return h.hexdigest()[:32]


class IngestService:
    def __init__(self) -> None:
        self._embedder = Embedder()

    def ingest_all_pdfs(self) -> dict:
        raw_dir = Path(settings.raw_documents_dir)
        raw_dir.mkdir(parents=True, exist_ok=True)

        pdfs = sorted(raw_dir.glob("**/*.pdf"))
        chroma = get_chroma()

        total_chunks = 0
        upserted = 0

        for pdf in pdfs:
            text = extract_pdf_text(pdf)
            if not text:
                continue

            chunks = chunk_text_semantic(
                text,
                chunk_size_tokens=settings.chunk_size_tokens,
                chunk_overlap_tokens=settings.chunk_overlap_tokens,
            )
            if not chunks:
                continue

            docs = [c.text for c in chunks]
            ids = [_doc_id(str(pdf), idx, c.text) for idx, c in enumerate(chunks)]
            metas = [
                {
                    "source": str(pdf).replace("\\", "/"),
                    "chunk_index": idx,
                    "start_token": c.start_token,
                    "end_token": c.end_token,
                }
                for idx, c in enumerate(chunks)
            ]
            embeds = self._embedder.embed(docs)

            chroma.collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
            total_chunks += len(chunks)
            upserted += len(ids)

        return {"pdfs_found": len(pdfs), "chunks_total": total_chunks, "chunks_upserted": upserted}
