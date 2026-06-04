"""A/B: naive vs adaptive chunking on the same queries (answer-containment) — the Phase 3 gate.

Generates one verbatim-span query set, ingests the corpus twice (naive, then adaptive), and scores
by whether a top-k retrieved chunk *contains* the answer span — a gold independent of how the text
was split. Enrichment is off so the only difference between arms is the chunker.

Run: uv run python scripts/eval_chunking.py
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
from evaluation.ab import RECALL_KS, ABScores, gold_key, score_containment  # noqa: E402
from evaluation.datasets import QAGenerator, QAPair  # noqa: E402
from evaluation.reset import reset_corpus  # noqa: E402
from index.qdrant_client import create_qdrant  # noqa: E402
from index.qdrant_hybrid import QdrantIndex  # noqa: E402
from providers.factory import ProviderFactory  # noqa: E402
from rerank.cross_encoder import CrossEncoderReranker  # noqa: E402
from retrieval.hybrid import HybridRetriever  # noqa: E402

QA_LIMIT = 120


def _norm(text: str) -> str:
    return " ".join(text.split()).lower()


async def _build_spans(
    gen: QAGenerator, docs: list[tuple[str, str]], chunker: Chunker, per_doc: int = 2
) -> list[QAPair]:
    """Verbatim-span QA, up to per_doc per doc (even coverage); skip spans not found verbatim."""
    qa: list[QAPair] = []
    for source, text in docs:
        doc_norm = _norm(text)
        taken = 0
        for ch in chunker.chunk(text):
            if taken >= per_doc or len(qa) >= QA_LIMIT:
                break
            try:
                pair = await gen.span_from_chunk(gold_key(source, ch.index), source, ch.text)
            except Exception:  # a flaky CLI call shouldn't abort the whole eval
                continue
            if pair is not None and _norm(pair.answer) in doc_norm:
                qa.append(pair)
                taken += 1
    return qa


async def _ingest_all(ingest: IngestService, docs: list[tuple[str, str]]) -> None:
    for source, text in docs:
        await ingest.ingest(source, text)


def _table(naive: ABScores, adaptive: ABScores) -> None:
    print(f"\nanswer-containment  (n={naive.n})")
    print(f"{'metric':<12}{'naive':>8}{'adaptive':>10}{'delta':>9}")
    rows = [(f"recall@{k}", naive.recall[k], adaptive.recall[k]) for k in RECALL_KS]
    rows += [("mrr", naive.mrr, adaptive.mrr), ("ndcg", naive.ndcg, adaptive.ndcg)]
    for name, a, b in rows:
        print(f"{name:<12}{a:>8.3f}{b:>10.3f}{b - a:>+9.3f}")


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
    naive = build_chunker(s.chunk_size, s.chunk_overlap, adaptive=False)
    adaptive = build_chunker(s.chunk_size, s.chunk_overlap, adaptive=True)

    corpus = sorted((ROOT / "evaluation" / "corpus").glob("*.txt"))
    docs = [(p.name, p.read_text(encoding="utf-8")) for p in corpus]
    qa = await _build_spans(QAGenerator(llm), docs, naive)
    print(f"queries={len(qa)} (verbatim spans)")

    await reset_corpus(qdrant, db, s.qdrant_collection)
    await _ingest_all(IngestService(naive, embedder, index, db), docs)
    naive_scores = await score_containment(retriever, qa, reranker)

    await reset_corpus(qdrant, db, s.qdrant_collection)
    await _ingest_all(IngestService(adaptive, embedder, index, db), docs)
    adaptive_scores = await score_containment(retriever, qa, reranker)

    _table(naive_scores, adaptive_scores)
    await db.dispose()
    await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
