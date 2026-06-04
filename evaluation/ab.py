"""A/B retrieval scoring: rank the gold chunk (keyed by source#position) for each question.

Compares two ingest configs (e.g. enrichment off vs on) on the *same* questions, at two stages:
the retriever's candidate pool, and the cross-encoder-reranked ordering (end-to-end). The gold key
is stable across re-ingests, so the only thing that changes between arms is the chunk embedding —
which is exactly what enrichment alters.
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluation.datasets import QAPair
from evaluation.metrics import recall_at_k, retrieval_metrics
from rerank.base import Reranker
from retrieval.hybrid import HybridRetriever
from retrieval.query_rewrite import QueryTransformer

RECALL_KS = (1, 3, 5, 10, 20)


@dataclass(frozen=True)
class ABScores:
    """Retrieval quality for one arm; the gold chunk is identified by source#position."""

    recall: dict[int, float]  # k -> recall@k over RECALL_KS
    mrr: float
    ndcg: float
    n: int


def gold_key(source: str, position: int) -> str:
    """Stable cross-ingest identity for a chunk (uuids change on re-ingest; this does not)."""
    return f"{source}#{position}"


def _scores(results: list[tuple[list[str], str]]) -> ABScores:
    rm = retrieval_metrics(results)
    return ABScores({k: recall_at_k(results, k) for k in RECALL_KS}, rm.mrr, rm.ndcg, rm.n)


async def score_retrieval(
    retriever: HybridRetriever, qa_pairs: list[QAPair], transform: QueryTransformer | None = None
) -> ABScores:
    """Score where each question's gold chunk ranks in the retriever's candidate pool."""
    results: list[tuple[list[str], str]] = []
    for qa in qa_pairs:
        q = await transform.transform(qa.question) if transform else qa.question
        hits = await retriever.retrieve(q)
        results.append(([gold_key(h.source, h.position) for h in hits], qa.chunk_id))
    return _scores(results)


async def score_reranked(
    retriever: HybridRetriever,
    reranker: Reranker,
    qa_pairs: list[QAPair],
    transform: QueryTransformer | None = None,
) -> ABScores:
    """Score the gold chunk's rank after the cross-encoder reorders the pool (end-to-end)."""
    results: list[tuple[list[str], str]] = []
    for qa in qa_pairs:
        q = await transform.transform(qa.question) if transform else qa.question
        hits = await retriever.retrieve(q)
        ranked = await reranker.rerank(qa.question, hits, len(hits))
        results.append(([gold_key(h.source, h.position) for h in ranked], qa.chunk_id))
    return _scores(results)


def _norm(text: str) -> str:
    return " ".join(text.split()).lower()


async def score_containment(
    retriever: HybridRetriever, qa_pairs: list[QAPair], reranker: Reranker | None = None
) -> ABScores:
    """Chunker-agnostic: score by whether a top-k chunk *contains* the verbatim answer span.

    Chunk identity is meaningless across chunkers, so the gold is the answer text itself: a query
    "hits" at the rank of the first retrieved chunk that contains the span.
    """
    results: list[tuple[list[str], str]] = []
    for qa in qa_pairs:
        span = _norm(qa.answer)
        hits = await retriever.retrieve(qa.question)
        if reranker is not None:
            hits = await reranker.rerank(qa.question, hits, len(hits))
        marks = [
            "HIT" if span and span in _norm(h.text) else f"MISS{i}" for i, h in enumerate(hits)
        ]
        results.append((marks, "HIT"))
    return _scores(results)
