"""A/B: naive vs adaptive chunking by generated-answer quality (faithfulness + relevance).

Generates questions once, answers each over a naive-ingested vs adaptive-ingested corpus, and judges
both answers — testing whether coherent chunks give the generator better context. Enrichment off, so
the only difference between arms is the chunker. This is the metric sentence-containment can't see.

Run: uv run python scripts/eval_chunk_quality.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from chunking.base import Chunker  # noqa: E402
from chunking.registry import build_chunker  # noqa: E402
from core.config import Settings  # noqa: E402
from core.db import Database  # noqa: E402
from core.models import Chunk as ChunkRow  # noqa: E402
from core.pipeline import AnswerService, IngestService  # noqa: E402
from evaluation.datasets import QAGenerator, QAPair  # noqa: E402
from evaluation.judge import AnswerJudge  # noqa: E402
from evaluation.reset import reset_corpus  # noqa: E402
from index.qdrant_client import create_qdrant  # noqa: E402
from index.qdrant_hybrid import QdrantIndex  # noqa: E402
from providers.factory import ProviderFactory  # noqa: E402
from rerank.cross_encoder import CrossEncoderReranker  # noqa: E402
from retrieval.hybrid import HybridRetriever  # noqa: E402

PER_DOC = 1


async def _build_questions(
    gen: QAGenerator, docs: list[tuple[str, str]], chunker: Chunker
) -> list[QAPair]:
    """One topic-named question per doc (covers all docs); skip unusable generations."""
    qa: list[QAPair] = []
    for source, text in docs:
        taken = 0
        for ch in chunker.chunk(text):
            if taken >= PER_DOC:
                break
            try:
                pair = await gen.hard_from_chunk(f"{source}#{ch.index}", source, text, ch.text)
            except Exception:
                continue
            if pair is not None:
                qa.append(pair)
                taken += 1
    return qa


async def _ingest_all(ingest: IngestService, docs: list[tuple[str, str]]) -> None:
    for source, text in docs:
        await ingest.ingest(source, text)


async def _context_for(db: Database, citations: list[dict]) -> str:
    ids = [c["chunk_id"] for c in citations]
    if not ids:
        return ""
    async with db.session() as session:
        rows = (await session.execute(select(ChunkRow).where(ChunkRow.id.in_(ids)))).scalars().all()
    return "\n\n".join(r.text for r in rows)


async def _judge_arm(
    questions: list[QAPair], answer: AnswerService, judge: AnswerJudge, db: Database
) -> tuple[float, float]:
    faith = rel = 0.0
    for q in questions:
        result = await answer.answer(q.question)
        context = await _context_for(db, result["citations"])
        scores = await judge.score(q.question, context, result["answer"])
        faith += scores.faithfulness
        rel += scores.answer_relevance
    n = len(questions) or 1
    return faith / n, rel / n


async def main() -> None:
    s = Settings()
    qdrant = create_qdrant(s.qdrant_url)
    db = Database(s.database_url)
    await db.create_all()
    index = QdrantIndex(qdrant, s.qdrant_collection)
    embedder = ProviderFactory(s).embeddings()
    llm = ProviderFactory(s).llm()
    retriever = HybridRetriever(embedder, index, s.rerank_candidates)
    answer = AnswerService(retriever, CrossEncoderReranker(s.rerank_model), llm, s.top_k)
    judge = AnswerJudge(llm)
    naive = build_chunker(s.chunk_size, s.chunk_overlap, adaptive=False)
    adaptive = build_chunker(s.chunk_size, s.chunk_overlap, adaptive=True)

    corpus = sorted((ROOT / "evaluation" / "corpus").glob("*.txt"))
    docs = [(p.name, p.read_text(encoding="utf-8")) for p in corpus]
    questions = await _build_questions(QAGenerator(llm), docs, naive)
    print(f"questions={len(questions)}")

    await reset_corpus(qdrant, db, s.qdrant_collection)
    await _ingest_all(IngestService(naive, embedder, index, db), docs)
    nf, nr = await _judge_arm(questions, answer, judge, db)

    await reset_corpus(qdrant, db, s.qdrant_collection)
    await _ingest_all(IngestService(adaptive, embedder, index, db), docs)
    af, ar = await _judge_arm(questions, answer, judge, db)

    print(f"\nanswer quality  (n={len(questions)})")
    print(f"{'metric':<14}{'naive':>8}{'adaptive':>10}{'delta':>9}")
    print(f"{'faithfulness':<14}{nf:>8.3f}{af:>10.3f}{af - nf:>+9.3f}")
    print(f"{'relevance':<14}{nr:>8.3f}{ar:>10.3f}{ar - nr:>+9.3f}")

    await db.dispose()
    await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
