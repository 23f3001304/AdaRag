"""Retrieval metrics: recall@k, MRR, and nDCG against a single relevant chunk per query."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalMetrics:
    recall_at_k: float
    mrr: float
    ndcg: float
    n: int


def _rank(retrieved_ids: list[str], relevant_id: str) -> int | None:
    """1-based rank of the relevant id among the retrieved ids, or None if absent."""
    for i, rid in enumerate(retrieved_ids):
        if rid == relevant_id:
            return i + 1
    return None


def retrieval_metrics(results: list[tuple[list[str], str]]) -> RetrievalMetrics:
    """Average recall@k / MRR / nDCG over (retrieved_ids in rank order, relevant_id) pairs."""
    if not results:
        return RetrievalMetrics(0.0, 0.0, 0.0, 0)
    recall = mrr = ndcg = 0.0
    for retrieved, relevant in results:
        rank = _rank(retrieved, relevant)
        if rank:
            recall += 1.0
            mrr += 1.0 / rank
            ndcg += 1.0 / math.log2(rank + 1)  # single relevant item: IDCG == 1
    n = len(results)
    return RetrievalMetrics(recall / n, mrr / n, ndcg / n, n)
