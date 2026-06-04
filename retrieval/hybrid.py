"""Hybrid retrieval: embed the query (dense + sparse) and fuse candidates via RRF.

A cross-encoder reranker reorders these results in step 1.3.
"""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient

from core.interfaces import EmbeddingProvider
from index.qdrant_hybrid import hybrid_search


@dataclass(frozen=True)
class Retrieved:
    """A retrieved chunk with its fused relevance score and provenance."""

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
    """Embed the query (dense + sparse) and return the RRF-fused top-k chunks."""
    dense, sparse = await embedder.embed_hybrid([query])
    points = await hybrid_search(qdrant, collection, dense[0], sparse[0], top_k)
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
