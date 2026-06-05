"""Unit tests for the Phase 5 optimizer's Pareto helpers (pure functions, no GPU/index)."""

from __future__ import annotations

from tuning.optimizer import TrialResult, best_at_relevance, pareto_front


def _t(k: int, ndcg: float, latency: float) -> TrialResult:
    return TrialResult(k, ndcg, latency)


def test_pareto_front_drops_dominated():
    # K=22 has lower nDCG AND higher latency than K=20 -> dominated, off the front.
    front = pareto_front([_t(8, 0.18, 80), _t(20, 0.23, 140), _t(22, 0.20, 150)])
    assert {t.rerank_candidates for t in front} == {8, 20}


def test_pareto_front_sorted_by_latency():
    front = pareto_front([_t(20, 0.23, 140), _t(8, 0.18, 80), _t(40, 0.28, 250)])
    assert [t.latency_ms for t in front] == sorted(t.latency_ms for t in front)


def test_best_at_relevance_picks_cheapest_holding_target():
    trials = [_t(36, 0.27, 220), _t(42, 0.28, 252), _t(20, 0.23, 140)]
    # within 0.01 of 0.28 -> {0.27, 0.28}; cheapest of those is K=36.
    assert best_at_relevance(trials, target_ndcg=0.28, tolerance=0.01).rerank_candidates == 36


def test_best_at_relevance_none_when_target_unreachable():
    assert best_at_relevance([_t(8, 0.18, 80)], target_ndcg=0.5) is None
