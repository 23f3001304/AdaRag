"""Hybrid retrieval: a retriever that embeds the query and RRF-fuses dense + sparse hits.

It returns a candidate pool; the cross-encoder reranker (1.3) reorders and trims it.
"""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import models

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
    modality: str = "text"  # text/pdf/image/audio/video — the source's modality
    original_path: str | None = None  # preserved original (image/audio/...) for the answer


class HybridRetriever:
    """Embeds the query (dense + sparse) and returns up to ``limit`` RRF-fused candidates."""

    def __init__(self, embedder: EmbeddingProvider, index: QdrantIndex, limit: int) -> None:
        self._embedder = embedder
        self._index = index
        self._limit = limit

    async def retrieve(
        self, query: str, query_filter: models.Filter | None = None
    ) -> list[Retrieved]:
        dense, sparse = await self._embedder.embed_hybrid([query])
        points = await self._index.search(dense[0], sparse[0], self._limit, query_filter)
        return [
            Retrieved(
                chunk_id=str(p.id),
                score=float(p.score),
                text=p.payload.get("text", ""),
                source=p.payload.get("source", ""),
                position=p.payload.get("position", -1),
                context=p.payload.get("context", ""),
                modality=p.payload.get("modality", "text"),
                original_path=p.payload.get("original_path"),
            )
            for p in points
        ]
