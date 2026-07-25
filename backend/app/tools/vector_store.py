"""Chroma-backed vector store for SourceDoc snippets and retrieval."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from functools import lru_cache

import chromadb

from app.core.config import settings
from app.services.gemini_api import GeminiAPIClient

logger = logging.getLogger(__name__)


class _HashEmbeddingFallback:
    def __init__(self, dimension: int = 256):
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            index = int(digest, 16) % self.dimension
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class VectorStore:
    async def upsert(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        raise NotImplementedError

    async def query(self, text: str, top_k: int = 5) -> list[str]:
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    def __init__(self):
        if not settings.chroma_path:
            raise RuntimeError("CHROMA_PATH is not configured.")
        self._client = chromadb.PersistentClient(path=settings.chroma_path)
        self._collection = self._client.get_or_create_collection(name=settings.chroma_collection)
        self._fallback = _HashEmbeddingFallback()
        self._gemini = GeminiAPIClient()

    async def _embed(self, text: str) -> list[float]:
        if self._gemini.is_configured:
            try:
                return await self._gemini.embed_text(text)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Gemini embedding failed, using local fallback: %s", exc)
        return self._fallback.embed(text)

    async def upsert(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        embedding = await self._embed(text)
        await asyncio.to_thread(
            self._collection.upsert,
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
            embeddings=[embedding],
        )

    async def query(self, text: str, top_k: int = 5) -> list[str]:
        embedding = await self._embed(text)
        results = await asyncio.to_thread(
            self._collection.query,
            query_embeddings=[embedding],
            n_results=top_k,
        )
        return list((results.get("ids") or [[]])[0])


@lru_cache(maxsize=1)
def get_vector_store() -> ChromaVectorStore | None:
    if not settings.chroma_path:
        return None
    return ChromaVectorStore()