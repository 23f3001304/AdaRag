"""Eval runner: push the golden questions through retrieval and score recall@k / MRR / nDCG."""

from __future__ import annotations

from sqlalchemy import select

from core.db import Database
from core.models import EvalQuestion
from evaluation.metrics import RetrievalMetrics, retrieval_metrics
from retrieval.hybrid import HybridRetriever


class EvalRunner:
    """Runs the stored eval questions through the retriever and computes retrieval metrics."""

    def __init__(self, retriever: HybridRetriever, db: Database) -> None:
        self._retriever = retriever
        self._db = db

    async def run_retrieval(self) -> RetrievalMetrics:
        """For each eval question, retrieve and check where its relevant chunk lands."""
        async with self._db.session() as session:
            questions = (await session.execute(select(EvalQuestion))).scalars().all()
        results: list[tuple[list[str], str]] = []
        for q in questions:
            hits = await self._retriever.retrieve(q.question)
            results.append(([h.chunk_id for h in hits], q.chunk_id))
        return retrieval_metrics(results)
