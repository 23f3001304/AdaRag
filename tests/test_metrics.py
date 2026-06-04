"""Unit tests for retrieval metrics (recall@k, MRR, nDCG)."""

from __future__ import annotations

import math

from evaluation.metrics import retrieval_metrics


def test_perfect_rank_one():
    m = retrieval_metrics([(["a", "b", "c"], "a")])
    assert (m.recall_at_k, m.mrr, m.ndcg, m.n) == (1.0, 1.0, 1.0, 1)


def test_relevant_at_rank_two():
    m = retrieval_metrics([(["x", "a", "y"], "a")])
    assert m.recall_at_k == 1.0
    assert m.mrr == 0.5
    assert math.isclose(m.ndcg, 1 / math.log2(3))


def test_missing_relevant_scores_zero():
    m = retrieval_metrics([(["x", "y"], "a")])
    assert (m.recall_at_k, m.mrr, m.ndcg) == (0.0, 0.0, 0.0)


def test_averages_across_queries():
    m = retrieval_metrics([(["a"], "a"), (["x"], "a")])  # one hit, one miss
    assert m.recall_at_k == 0.5
    assert m.mrr == 0.5
    assert m.n == 2


def test_empty_results():
    m = retrieval_metrics([])
    assert m.n == 0
    assert m.recall_at_k == 0.0
