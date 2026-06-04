"""Dense retrieval: embed the query and fetch the nearest chunks from Qdrant.

Phase 1 adds sparse fusion (RRF) and a cross-encoder reranker on top of this.
"""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient

from core.interfaces import EmbeddingProvider
from index.qdrant_hybrid import search_dense


@dataclass(frozen=True)
class Retrieved:
    """A retrieved chunk with its relevance score and provenance."""

    chunk_id: str
    score: float
    text: str
    source: str
    position: int


async def retrieve(
    query: str,
    *,
    embedder: EmbeddingProvider,
    qdrant: AsyncQdrantClient,
    collection: str,
    top_k: int,
) -> list[Retrieved]:
    """Embed the query and return the top-k nearest chunks (dense only for now)."""
    vector = (await embedder.embed([query]))[0]
    points = await search_dense(qdrant, collection, vector, top_k)
    return [
        Retrieved(
            chunk_id=str(p.id),
            score=float(p.score),
            text=p.payload.get("text", ""),
            source=p.payload.get("source", ""),
            position=p.payload.get("position", -1),
        )
        for p in points
    ]
