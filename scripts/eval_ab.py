"""A/B: compare two enrichment configs on the same queries — the Phase 2 retrieval gate.

Generates one query set, ingests the corpus twice (two enrichment configs), and scores where each
query's gold chunk ranks — in the retriever's candidate pool and after cross-encoder reranking. Only
the ingest config differs between arms. Configurable via env:
  AB_OFF / AB_ON : arm specs, any of none | ctx | meta | ctx+meta   (default none / ctx)
  AB_QUERY       : hard (topic-named) | term (exact-term)           (default hard)

Run: uv run python scripts/eval_ab.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chunking.base import Chunker  # noqa: E402
from chunking.naive import NaiveChunker  # noqa: E402
from core.config import Settings  # noqa: E402
from core.db import Database  # noqa: E402
from core.interfaces import LLMProvider  # noqa: E402
from core.pipeline import IngestService  # noqa: E402
from enrichment.contextual import ContextualEnricher  # noqa: E402
from enrichment.metadata import MetadataEnricher  # noqa: E402
from evaluation.ab import (  # noqa: E402
    RECALL_KS,
    ABScores,
    gold_key,
    score_reranked,
    score_retrieval,
)
from evaluation.datasets import QAGenerator, QAPair  # noqa: E402
from evaluation.reset import reset_corpus  # noqa: E402
from index.qdrant_client import create_qdrant  # noqa: E402
from index.qdrant_hybrid import QdrantIndex  # noqa: E402
from providers.factory import ProviderFactory  # noqa: E402
from rerank.cross_encoder import CrossEncoderReranker  # noqa: E402
from retrieval.hybrid import HybridRetriever  # noqa: E402

QA_LIMIT = 120


def _enrichers(
    spec: str, llm: LLMProvider
) -> tuple[ContextualEnricher | None, MetadataEnricher | None]:
    """Map an arm spec ('none'|'ctx'|'meta'|'ctx+meta') to (contextual, metadata) enrichers."""
    ctx = ContextualEnricher(llm) if "ctx" in spec else None
    meta = MetadataEnricher(llm) if "meta" in spec else None
    return ctx, meta


async def _build_qa(
    generator: QAGenerator, docs: list[tuple[str, str]], chunker: Chunker, mode: str
) -> list[QAPair]:
    """Generate one query per chunk; mode 'hard' = topic-named, 'term' = exact-term."""
    qa: list[QAPair] = []
    for source, text in docs:
        for ch in chunker.chunk(text):
            if len(qa) >= QA_LIMIT:
                return qa
            key = gold_key(source, ch.index)
            if mode == "term":
                pair = await generator.term_from_chunk(key, source, ch.text)
            else:
                pair = await generator.hard_from_chunk(key, source, text, ch.text)
            if pair is not None:
                qa.append(pair)
    return qa


async def _ingest_all(ingest: IngestService, docs: list[tuple[str, str]]) -> None:
    for source, text in docs:
        await ingest.ingest(source, text)


def _table(title: str, off: ABScores, on: ABScores) -> None:
    print(f"\n{title}  (n={off.n})")
    print(f"{'metric':<12}{'OFF':>8}{'ON':>8}{'delta':>9}")
    rows = [(f"recall@{k}", off.recall[k], on.recall[k]) for k in RECALL_KS]
    rows += [("mrr", off.mrr, on.mrr), ("ndcg", off.ndcg, on.ndcg)]
    for name, a, b in rows:
        print(f"{name:<12}{a:>8.3f}{b:>8.3f}{b - a:>+9.3f}")


async def main() -> None:
    s = Settings()
    off_spec = os.environ.get("AB_OFF", "none")
    on_spec = os.environ.get("AB_ON", "ctx")
    mode = os.environ.get("AB_QUERY", "hard")
    qdrant = create_qdrant(s.qdrant_url)
    db = Database(s.database_url)
    await db.create_all()
    index = QdrantIndex(qdrant, s.qdrant_collection)
    embedder = ProviderFactory(s).embeddings()
    llm = ProviderFactory(s).llm()
    chunker = NaiveChunker(s.chunk_size, s.chunk_overlap)
    retriever = HybridRetriever(embedder, index, s.rerank_candidates)
    reranker = CrossEncoderReranker(s.rerank_model)

    corpus = sorted((ROOT / "evaluation" / "corpus").glob("*.txt"))
    docs = [(p.name, p.read_text(encoding="utf-8")) for p in corpus]
    max_chunks = int(os.environ.get("AB_MAX_CHUNKS", "0"))
    if max_chunks:  # cap the corpus (biggest docs first) so per-chunk enrichment stays tractable
        docs.sort(key=lambda d: len(d[1]), reverse=True)
        kept: list[tuple[str, str]] = []
        total = 0
        for doc in docs:
            kept.append(doc)
            total += len(chunker.chunk(doc[1]))
            if total >= max_chunks:
                break
        docs = kept
        print(f"capped to {len(docs)} docs (~{total} chunks)")
    qa = await _build_qa(QAGenerator(llm), docs, chunker, mode)
    print(f"arms: OFF={off_spec}  ON={on_spec}  queries={mode}")

    await reset_corpus(qdrant, db, s.qdrant_collection)
    off_ctx, off_meta = _enrichers(off_spec, llm)
    await _ingest_all(IngestService(chunker, embedder, index, db, off_ctx, off_meta), docs)
    off_retr = await score_retrieval(retriever, qa)
    off_rank = await score_reranked(retriever, reranker, qa)

    await reset_corpus(qdrant, db, s.qdrant_collection)
    on_ctx, on_meta = _enrichers(on_spec, llm)
    await _ingest_all(IngestService(chunker, embedder, index, db, on_ctx, on_meta), docs)
    on_retr = await score_retrieval(retriever, qa)
    on_rank = await score_reranked(retriever, reranker, qa)

    _table(f"retriever ({off_spec} vs {on_spec})", off_retr, on_retr)
    _table(f"reranked ({off_spec} vs {on_spec})", off_rank, on_rank)
    await db.dispose()
    await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
