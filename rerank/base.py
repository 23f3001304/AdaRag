"""Reranking contract: reorder retrieved candidates by true relevance to the query."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from retrieval.hybrid import Retrieved


@runtime_checkable
class Reranker(Protocol):
    """A reranking strategy over retrieved candidates."""

    async def rerank(self, query: str, hits: list[Retrieved], top_k: int) -> list[Retrieved]:
        """Reorder hits by relevance to the query and return the top_k."""
        ...
