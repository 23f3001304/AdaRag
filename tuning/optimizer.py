"""Optuna pipeline optimizer (Phase 5): tune query-time knobs for the best relevance/latency trade.

Multi-objective — maximize retrieval nDCG, minimize mean retrieve+rerank latency — so the result is
a Pareto front, not one config. The headline ('baseline nDCG at N% lower latency') is the Pareto
point that holds relevance while cutting latency. Runs on the local GPU over an already-ingested
index, so trials are fast and free. `rerank_candidates` is the lever: the cross-encoder cost grows
with the pool, while recall saturates — so there is a real knee to find.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import optuna

from core.interfaces import EmbeddingProvider
from evaluation.ab import score_reranked
from evaluation.datasets import QAPair
from index.qdrant_hybrid import QdrantIndex
from rerank.base import Reranker
from retrieval.hybrid import HybridRetriever

optuna.logging.set_verbosity(optuna.logging.WARNING)


@dataclass(frozen=True)
class TrialResult:
    """One evaluated configuration: its knob value and the two objective scores."""

    rerank_candidates: int
    ndcg: float
    latency_ms: float


class PipelineOptimizer:
    """Searches rerank_candidates for max nDCG at min retrieve+rerank latency (Optuna ask/tell)."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        index: QdrantIndex,
        reranker: Reranker,
        qa_pairs: list[QAPair],
        *,
        min_candidates: int = 5,
        max_candidates: int = 48,
    ) -> None:
        self._embedder = embedder
        self._index = index
        self._reranker = reranker
        self._qa = qa_pairs
        self._min = min_candidates
        self._max = max_candidates

    async def evaluate(self, rerank_candidates: int) -> TrialResult:
        """Score nDCG and mean per-query latency (retrieve + rerank) for one candidate-pool size."""
        retriever = HybridRetriever(self._embedder, self._index, rerank_candidates)
        start = time.perf_counter()
        scores = await score_reranked(retriever, self._reranker, self._qa)
        latency_ms = (time.perf_counter() - start) / max(1, len(self._qa)) * 1000
        return TrialResult(rerank_candidates, scores.ndcg, latency_ms)

    async def optimize(self, n_trials: int, seed: int = 7) -> list[TrialResult]:
        """Run an Optuna multi-objective search; returns every evaluated trial."""
        await self.evaluate(self._max)  # warm up GPU/models so the first real timing isn't skewed
        study = optuna.create_study(
            directions=["maximize", "minimize"],
            sampler=optuna.samplers.TPESampler(seed=seed),
        )
        trials: list[TrialResult] = []
        for _ in range(n_trials):
            ask = study.ask()
            k = ask.suggest_int("rerank_candidates", self._min, self._max)
            result = await self.evaluate(k)
            study.tell(ask, [result.ndcg, result.latency_ms])
            trials.append(result)
        return trials


def _dominates(a: TrialResult, b: TrialResult) -> bool:
    """True if a is at least as good as b on both objectives and strictly better on one."""
    return (
        a.ndcg >= b.ndcg
        and a.latency_ms <= b.latency_ms
        and (a.ndcg > b.ndcg or a.latency_ms < b.latency_ms)
    )


def pareto_front(trials: list[TrialResult]) -> list[TrialResult]:
    """Non-dominated trials (deduped per knob, keeping best nDCG), sorted by latency."""
    front = [t for t in trials if not any(_dominates(o, t) for o in trials)]
    by_knob = {t.rerank_candidates: t for t in sorted(front, key=lambda t: t.ndcg)}
    return sorted(by_knob.values(), key=lambda t: t.latency_ms)


def best_at_relevance(
    trials: list[TrialResult], target_ndcg: float, tolerance: float = 0.01
) -> TrialResult | None:
    """Lowest-latency trial holding nDCG within `tolerance` of the target (the headline pick)."""
    holding = [t for t in trials if t.ndcg >= target_ndcg - tolerance]
    return min(holding, key=lambda t: t.latency_ms) if holding else None
