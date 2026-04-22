from __future__ import annotations

from dataclasses import dataclass

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from core import settings


@dataclass(frozen=True)
class ChromaHandle:
    client: ClientAPI
    collection: Collection


def get_chroma() -> ChromaHandle:
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collection = client.get_or_create_collection(name=settings.chroma_collection, metadata={"hnsw:space": "cosine"})
    return ChromaHandle(client=client, collection=collection)
