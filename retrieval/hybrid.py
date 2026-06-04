"""Hybrid retrieval: a retriever that embeds the query and RRF-fuses dense + sparse hits.

A cross-encoder reranker reorders these results in step 1.3.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.interfaces import EmbeddingProvider
from index.qdrant_hybrid import QdrantIndex


@dataclass(frozen=True)
class Retrieved:
    """A retrieved chunk with its fused relevance score and provenance."""

    chunk_id: str
    score: float
    text: str
    source: str
    position: int


class HybridRetriever:
    """Embeds the query (dense + sparse) and returns the RRF-fused top-k chunks."""

    def __init__(self, embedder: EmbeddingProvider, index: QdrantIndex, top_k: int) -> None:
        self._embedder = embedder
        self._index = index
        self._top_k = top_k

    async def retrieve(self, query: str) -> list[Retrieved]:
        dense, sparse = await self._embedder.embed_hybrid([query])
        points = await self._index.search(dense[0], sparse[0], self._top_k)
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
