"""Query-transform A/B: bare query vs rewrite vs HyDE, end-to-end (retrieve + rerank) — Phase 4.

Ingests the corpus once (no enrichment), then scores the same questions retrieving with the bare
query, the rewritten query, and a HyDE probe. Run: uv run python scripts/eval_query.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chunking.base import Chunker  # noqa: E402
from chunking.registry import build_chunker  # noqa: E402
from core.config import Settings  # noqa: E402
from core.db import Database  # noqa: E402
from core.pipeline import IngestService  # noqa: E402
from evaluation.ab import RECALL_KS, ABScores, gold_key, score_reranked  # noqa: E402
from evaluation.datasets import QAGenerator, QAPair  # noqa: E402
from evaluation.reset import reset_corpus  # noqa: E402
from index.qdrant_client import create_qdrant  # noqa: E402
from index.qdrant_hybrid import QdrantIndex  # noqa: E402
from providers.factory import ProviderFactory  # noqa: E402
from rerank.cross_encoder import CrossEncoderReranker  # noqa: E402
from retrieval.hybrid import HybridRetriever  # noqa: E402
from retrieval.query_rewrite import HydeTransformer, QueryRewriter  # noqa: E402

QA_LIMIT = 60
MAX_CHUNKS = 400


async def _build_qa(
    gen: QAGenerator, docs: list[tuple[str, str]], chunker: Chunker
) -> list[QAPair]:
    qa: list[QAPair] = []
    for source, text in docs:
        for ch in chunker.chunk(text):
            if len(qa) >= QA_LIMIT:
                return qa
            try:
                pair = await gen.hard_from_chunk(gold_key(source, ch.index), source, text, ch.text)
            except Exception:
                continue
            if pair is not None:
                qa.append(pair)
    return qa


def _cap(docs: list[tuple[str, str]], chunker: Chunker) -> list[tuple[str, str]]:
    docs = sorted(docs, key=lambda d: len(d[1]), reverse=True)
    kept: list[tuple[str, str]] = []
    total = 0
    for doc in docs:
        kept.append(doc)
        total += len(chunker.chunk(doc[1]))
        if total >= MAX_CHUNKS:
            break
    print(f"corpus: {len(kept)} docs (~{total} chunks)")
    return kept


def _row(name: str, base: float, rew: float, hyde: float) -> str:
    return f"{name:<12}{base:>8.3f}{rew:>8.3f}{rew - base:>+7.3f}{hyde:>8.3f}{hyde - base:>+7.3f}"


def _report(base: ABScores, rew: ABScores, hyde: ABScores) -> None:
    print(f"\nend-to-end  (n={base.n})")
    print(f"{'metric':<12}{'base':>8}{'rewrite':>8}{'+/-':>7}{'hyde':>8}{'+/-':>7}")
    for k in RECALL_KS:
        print(_row(f"recall@{k}", base.recall[k], rew.recall[k], hyde.recall[k]))
    print(_row("mrr", base.mrr, rew.mrr, hyde.mrr))
    print(_row("ndcg", base.ndcg, rew.ndcg, hyde.ndcg))


async def main() -> None:
    s = Settings()
    qdrant = create_qdrant(s.qdrant_url)
    db = Database(s.database_url)
    await db.create_all()
    index = QdrantIndex(qdrant, s.qdrant_collection)
    embedder = ProviderFactory(s).embeddings()
    llm = ProviderFactory(s).llm()
    retriever = HybridRetriever(embedder, index, s.rerank_candidates)
    reranker = CrossEncoderReranker(s.rerank_model)
    chunker = build_chunker(s.chunk_size, s.chunk_overlap, s.adaptive_chunking)

    corpus = sorted((ROOT / "evaluation" / "corpus").glob("*.txt"))
    docs = _cap([(p.name, p.read_text(encoding="utf-8")) for p in corpus], chunker)
    qa = await _build_qa(QAGenerator(llm), docs, chunker)
    print(f"questions={len(qa)}")

    await reset_corpus(qdrant, db, s.qdrant_collection)
    for source, text in docs:
        await IngestService(chunker, embedder, index, db).ingest(source, text)

    base = await score_reranked(retriever, reranker, qa)
    rew = await score_reranked(retriever, reranker, qa, QueryRewriter(llm))
    hyde = await score_reranked(retriever, reranker, qa, HydeTransformer(llm))

    _report(base, rew, hyde)
    await db.dispose()
    await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
