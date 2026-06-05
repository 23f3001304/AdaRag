"""Phase 5 optimizer run: tune rerank_candidates for the best nDCG/latency trade-off.

Ingests the corpus once, builds (and caches) a golden query set, then runs an Optuna multi-objective
search over the candidate-pool size, reporting the Pareto front and the lowest-latency config that
holds baseline relevance. Local GPU; trials are free.

Env: OPT_MAX_CHUNKS (cap corpus, default 300), OPT_QA (max queries, 60), OPT_TRIALS (budget, 25).
Run: uv run python scripts/optimize.py   (delete data/_opt_queries.json to regenerate queries)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chunking.naive import NaiveChunker  # noqa: E402
from core.config import Settings  # noqa: E402
from core.db import Database  # noqa: E402
from core.pipeline import IngestService  # noqa: E402
from evaluation.ab import gold_key  # noqa: E402
from evaluation.datasets import QAGenerator, QAPair  # noqa: E402
from evaluation.reset import reset_corpus  # noqa: E402
from index.qdrant_client import create_qdrant  # noqa: E402
from index.qdrant_hybrid import QdrantIndex  # noqa: E402
from providers.factory import ProviderFactory  # noqa: E402
from rerank.cross_encoder import CrossEncoderReranker  # noqa: E402
from tuning.optimizer import PipelineOptimizer, best_at_relevance, pareto_front  # noqa: E402

_CACHE = ROOT / "data" / "_opt_queries.json"


def _load_corpus(chunker: NaiveChunker, max_chunks: int) -> list[tuple[str, str]]:
    """Corpus docs, capped to ~max_chunks (biggest first) so the candidate pool isn't saturated."""
    paths = sorted((ROOT / "evaluation" / "corpus").glob("*.txt"))
    docs = [(p.name, p.read_text(encoding="utf-8")) for p in paths]
    if not max_chunks:
        return docs
    docs.sort(key=lambda d: len(d[1]), reverse=True)
    kept: list[tuple[str, str]] = []
    total = 0
    for doc in docs:
        kept.append(doc)
        total += len(chunker.chunk(doc[1]))
        if total >= max_chunks:
            break
    return kept


async def _build_queries(gen: QAGenerator, docs, chunker: NaiveChunker, limit: int) -> list[QAPair]:
    """Topic-named golden queries (cached to disk; delete the cache file to regenerate)."""
    if _CACHE.exists():
        return [QAPair(**row) for row in json.loads(_CACHE.read_text(encoding="utf-8"))]
    qa: list[QAPair] = []
    for source, text in docs:
        for ch in chunker.chunk(text):
            if len(qa) >= limit:
                break
            pair = await gen.hard_from_chunk(gold_key(source, ch.index), source, text, ch.text)
            if pair is not None:
                qa.append(pair)
        if len(qa) >= limit:
            break
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE.write_text(json.dumps([p.__dict__ for p in qa]), encoding="utf-8")
    return qa


async def main() -> None:
    s = Settings()
    qdrant = create_qdrant(s.qdrant_url)
    db = Database(s.database_url)
    await db.create_all()
    index = QdrantIndex(qdrant, s.qdrant_collection)
    embedder = ProviderFactory(s).embeddings()
    reranker = CrossEncoderReranker(s.rerank_model)
    chunker = NaiveChunker(s.chunk_size, s.chunk_overlap)

    docs = _load_corpus(chunker, int(os.environ.get("OPT_MAX_CHUNKS", "300")))
    qa_limit = int(os.environ.get("OPT_QA", "60"))
    qa = await _build_queries(QAGenerator(ProviderFactory(s).llm()), docs, chunker, qa_limit)

    await reset_corpus(qdrant, db, s.qdrant_collection)
    ingest = IngestService(chunker, embedder, index, db)
    for source, text in docs:
        await ingest.ingest(source, text)

    opt = PipelineOptimizer(embedder, index, reranker, qa)
    await opt.evaluate(s.rerank_candidates)  # cold warmup so the baseline is timed warm
    baseline = await opt.evaluate(s.rerank_candidates)
    trials = await opt.optimize(int(os.environ.get("OPT_TRIALS", "25")))
    front = pareto_front([baseline, *trials])
    peak = max(trials, key=lambda t: t.ndcg)  # the relevance-max config (naive "crank up K")
    knee = best_at_relevance(trials, peak.ndcg)  # cheapest config still at ~peak relevance

    bl = baseline
    print(f"\ncorpus: {len(docs)} docs | queries: {len(qa)} | trials: {len(trials)}")
    print(f"default K={bl.rerank_candidates} -> nDCG={bl.ndcg:.3f} at {bl.latency_ms:.1f} ms/query")
    print("\npareto front (relevance vs latency):")
    for t in front:
        print(f"  K={t.rerank_candidates:>2}  nDCG={t.ndcg:.3f}  {t.latency_ms:>6.1f} ms")
    if knee is not None and knee.rerank_candidates != peak.rerank_candidates:
        dlat = (knee.latency_ms - peak.latency_ms) / peak.latency_ms * 100
        print(
            f"\nHEADLINE: K={knee.rerank_candidates} hits ~peak nDCG {knee.ndcg:.3f} "
            f"(max {peak.ndcg:.3f} at K={peak.rerank_candidates}) at {dlat:+.1f}% latency"
        )
    await db.dispose()
    await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
