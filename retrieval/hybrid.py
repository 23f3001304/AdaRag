"""Hybrid retrieval: a retriever that embeds the query and RRF-fuses dense + sparse hits.

It returns a candidate pool; the cross-encoder reranker (1.3) reorders and trims it.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.interfaces import EmbeddingProvider
from index.qdrant_hybrid import QdrantIndex


@dataclass(frozen=True)
class Retrieved:
    """A retrieved chunk with its relevance score and provenance."""

    chunk_id: str
    score: float
    text: str
    source: str
    position: int
    context: str = ""  # situating context (enrichment); scored at rerank, never displayed/cited


class HybridRetriever:
    """Embeds the query (dense + sparse) and returns up to ``limit`` RRF-fused candidates."""

    def __init__(self, embedder: EmbeddingProvider, index: QdrantIndex, limit: int) -> None:
        self._embedder = embedder
        self._index = index
        self._limit = limit

    async def retrieve(self, query: str) -> list[Retrieved]:
        dense, sparse = await self._embedder.embed_hybrid([query])
        points = await self._index.search(dense[0], sparse[0], self._limit)
        return [
            Retrieved(
                chunk_id=str(p.id),
                score=float(p.score),
                text=p.payload.get("text", ""),
                source=p.payload.get("source", ""),
                position=p.payload.get("position", -1),
                context=p.payload.get("context", ""),
            )
            for p in points
        ]
