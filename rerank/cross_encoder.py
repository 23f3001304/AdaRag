"""Cross-encoder reranking with bge-reranker-v2-m3: reorder fused candidates by true relevance.

Uses sentence-transformers' CrossEncoder (FlagEmbedding's reranker breaks on transformers 5.x).
"""

from __future__ import annotations

import asyncio
import math
from typing import Any

from retrieval.hybrid import Retrieved


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class CrossEncoderReranker:
    """bge-reranker-v2-m3 cross-encoder. Loads lazily on first use; uses CUDA when available."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        self._model_name = model_name
        self._model: Any | None = None
        self.device = "cpu"

    def _load(self) -> Any:
        if self._model is None:
            import torch  # heavy import, deferred
            from sentence_transformers import CrossEncoder

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = CrossEncoder(self._model_name, device=self.device)
        return self._model

    @staticmethod
    def _passage(h: Retrieved) -> str:
        """Score the chunk together with its situating context, when enrichment supplied one."""
        return f"{h.context}\n\n{h.text}" if h.context else h.text

    def _rerank(self, query: str, hits: list[Retrieved], top_k: int) -> list[Retrieved]:
        scores = self._load().predict([[query, self._passage(h)] for h in hits])
        ranked = sorted(zip(hits, scores, strict=True), key=lambda hs: hs[1], reverse=True)
        return [
            Retrieved(
                h.chunk_id,
                _sigmoid(float(s)),
                h.text,
                h.source,
                h.position,
                h.context,
                h.modality,
                h.original_path,
            )
            for h, s in ranked[:top_k]
        ]

    async def rerank(self, query: str, hits: list[Retrieved], top_k: int) -> list[Retrieved]:
        """Reorder hits by relevance, keep top_k (blocking model call runs in a thread)."""
        if not hits:
            return []
        return await asyncio.to_thread(self._rerank, query, hits, top_k)
