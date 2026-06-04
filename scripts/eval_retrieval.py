"""Reset the corpus, ingest the sample doc, build a QA eval set, and score retrieval + generation.

Run: uv run python scripts/eval_retrieval.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from chunking.naive import NaiveChunker  # noqa: E402
from core.config import Settings  # noqa: E402
from core.db import Database  # noqa: E402
from core.pipeline import AnswerService, IngestService  # noqa: E402
from evaluation.dataset_builder import EvalSetBuilder  # noqa: E402
from evaluation.datasets import QAGenerator  # noqa: E402
from evaluation.judge import AnswerJudge  # noqa: E402
from evaluation.runner import EvalRunner  # noqa: E402
from index.qdrant_client import create_qdrant  # noqa: E402
from index.qdrant_hybrid import QdrantIndex  # noqa: E402
from providers.factory import ProviderFactory  # noqa: E402
from rerank.cross_encoder import CrossEncoderReranker  # noqa: E402
from retrieval.hybrid import HybridRetriever  # noqa: E402


async def main() -> None:
    s = Settings()
    qdrant = create_qdrant(s.qdrant_url)
    db = Database(s.database_url)
    await db.create_all()
    index = QdrantIndex(qdrant, s.qdrant_collection)
    embedder = ProviderFactory(s).embeddings()
    llm = ProviderFactory(s).llm()

    # reset to a clean, known corpus
    try:
        await qdrant.delete_collection(s.qdrant_collection)
    except Exception:  # best-effort reset
        pass
    async with db.session() as session:
        await session.execute(text("TRUNCATE documents, chunks, eval_questions CASCADE"))
        await session.commit()

    ingest = IngestService(NaiveChunker(s.chunk_size, s.chunk_overlap), embedder, index, db)
    await ingest.ingest("sample.txt", (ROOT / "data" / "sample.txt").read_text(encoding="utf-8"))
    n = await EvalSetBuilder(QAGenerator(llm), db).build()

    retriever = HybridRetriever(embedder, index, s.rerank_candidates)
    answer = AnswerService(retriever, CrossEncoderReranker(s.rerank_model), llm, s.top_k)
    runner = EvalRunner(retriever, answer, AnswerJudge(llm), db)
    rm = await runner.run_retrieval()
    gm = await runner.run_generation()

    print(f"questions={n}")
    print(f"retrieval  recall={rm.recall_at_k:.2f}  mrr={rm.mrr:.2f}  ndcg={rm.ndcg:.2f}")
    print(f"generation faithfulness={gm.faithfulness:.2f}  relevance={gm.answer_relevance:.2f}")

    await db.dispose()
    await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
