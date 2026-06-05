"""Background study runner: tune a bucket's rerank depth from the frontend, with live progress.

Builds a small golden set from the bucket's own chunks (topic-named queries via the LLM), then runs
the Optuna nDCG/latency search over rerank_candidates, exposing progress for polling. One study runs
at a time, in-process on the shared GPU models.
"""

from __future__ import annotations

import asyncio

from core.buckets import BucketManager, collection_name
from core.config import Settings
from evaluation.ab import gold_key
from evaluation.datasets import QAGenerator, QAPair
from index.qdrant_hybrid import QdrantIndex
from tuning.optimizer import PipelineOptimizer, TrialResult, best_at_relevance, pareto_front


def _trial_dict(t: TrialResult) -> dict:
    return {"k": t.rerank_candidates, "ndcg": round(t.ndcg, 4), "ms": round(t.latency_ms, 1)}


class StudyRunner:
    """Runs one bucket-tuning study at a time and tracks its progress for polling."""

    def __init__(self, buckets: BucketManager, qdrant, settings: Settings) -> None:
        self._buckets = buckets
        self._qdrant = qdrant
        self._s = settings
        self._task: asyncio.Task | None = None
        self.state: dict = {"status": "idle"}

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self, bucket: str, trials: int, max_queries: int) -> bool:
        """Kick off a study in the background; returns False if one is already running."""
        if self.running:
            return False
        trials = max(5, min(trials, 40))
        max_queries = max(3, min(max_queries, 30))
        self.state = {
            "status": "starting",
            "bucket": bucket,
            "trials_done": 0,
            "trials_total": trials,
        }
        self._task = asyncio.create_task(self._run(bucket, trials, max_queries))
        return True

    async def _run(self, bucket: str, trials: int, max_queries: int) -> None:
        try:
            self.state = {"status": "building_queries", "bucket": bucket, "trials_total": trials}
            qa = await self._build_queries(bucket, max_queries)
            if len(qa) < 3:
                self.state = {
                    "status": "error",
                    "bucket": bucket,
                    "error": f"only {len(qa)} queries could be built; ingest more into this bucket",
                }
                return
            index = QdrantIndex(self._qdrant, collection_name(self._s.qdrant_collection, bucket))
            opt = PipelineOptimizer(self._buckets.embedder, index, self._buckets.reranker, qa)
            self.state = {
                "status": "running",
                "bucket": bucket,
                "queries": len(qa),
                "trials_done": 0,
                "trials_total": trials,
                "trials": [],
            }
            await opt.evaluate(self._s.rerank_candidates)  # cold load borne here
            baseline = await opt.evaluate(self._s.rerank_candidates)  # warm baseline
            results: list[TrialResult] = []

            def on_trial(t: TrialResult, done: int) -> None:
                results.append(t)
                self.state["trials_done"] = done
                self.state["trials"] = [_trial_dict(x) for x in results]

            await opt.optimize(trials, on_trial=on_trial)
            peak = max(results, key=lambda t: t.ndcg)
            knee = best_at_relevance(results, peak.ndcg)
            self.state = {
                "status": "done",
                "bucket": bucket,
                "queries": len(qa),
                "trials_total": trials,
                "trials_done": trials,
                "trials": [_trial_dict(x) for x in results],
                "baseline": _trial_dict(baseline),
                "front": [_trial_dict(x) for x in pareto_front([baseline, *results])],
                "headline": _headline(baseline, peak, knee),
            }
        except Exception as exc:  # surface the failure to the poller instead of dying silently
            self.state = {"status": "error", "bucket": bucket, "error": str(exc)}

    async def _build_queries(self, bucket: str, max_queries: int) -> list[QAPair]:
        """Topic-named golden queries from the bucket's own chunks (one LLM call per kept query)."""
        collection = collection_name(self._s.qdrant_collection, bucket)
        chunks: list[dict] = []
        offset = None
        while True:
            try:
                points, offset = await self._qdrant.scroll(
                    collection_name=collection,
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
            except Exception:
                break
            for p in points:
                payload = p.payload or {}
                if payload.get("text"):
                    chunks.append(
                        {
                            "source": str(payload.get("source", "")),
                            "position": int(payload.get("position", -1)),
                            "text": str(payload["text"]),
                        }
                    )
            if offset is None:
                break
        by_source: dict[str, list[dict]] = {}
        for c in chunks:
            by_source.setdefault(c["source"], []).append(c)
        doc_text = {
            s: "\n\n".join(x["text"] for x in sorted(cs, key=lambda x: x["position"]))
            for s, cs in by_source.items()
        }
        gen = QAGenerator(self._buckets.llm)
        qa: list[QAPair] = []
        for c in chunks:
            if len(qa) >= max_queries:
                break
            try:
                pair = await gen.hard_from_chunk(
                    gold_key(c["source"], c["position"]),
                    c["source"],
                    doc_text[c["source"]],
                    c["text"],
                )
            except Exception:
                pair = None
            if pair is not None:
                qa.append(pair)
        return qa


def _headline(baseline: TrialResult, peak: TrialResult, knee: TrialResult | None) -> str:
    """One-line takeaway: the diminishing-returns knee vs the relevance-max config."""
    if knee is None or knee.rerank_candidates == peak.rerank_candidates:
        return (
            f"Peak nDCG {peak.ndcg:.3f} at K={peak.rerank_candidates}; "
            f"default K={baseline.rerank_candidates} scores {baseline.ndcg:.3f}."
        )
    dlat = (knee.latency_ms - peak.latency_ms) / max(1.0, peak.latency_ms) * 100
    return (
        f"K={knee.rerank_candidates} holds ~peak nDCG {knee.ndcg:.3f} "
        f"(max {peak.ndcg:.3f} at K={peak.rerank_candidates}) at {dlat:+.0f}% latency."
    )
