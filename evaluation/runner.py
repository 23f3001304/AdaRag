"""Eval runner: score retrieval (recall@k/MRR/nDCG) and generation (faithfulness/relevance)."""

from __future__ import annotations

from sqlalchemy import select

from core.db import Database
from core.models import Chunk, EvalQuestion
from core.pipeline import AnswerService
from evaluation.judge import AnswerJudge, GenerationScores
from evaluation.metrics import RetrievalMetrics, retrieval_metrics
from retrieval.hybrid import HybridRetriever


class EvalRunner:
    """Runs the golden questions through the pipeline and scores retrieval + generation."""

    def __init__(
        self, retriever: HybridRetriever, answer: AnswerService, judge: AnswerJudge, db: Database
    ) -> None:
        self._retriever = retriever
        self._answer = answer
        self._judge = judge
        self._db = db

    async def _questions(self) -> list[EvalQuestion]:
        async with self._db.session() as session:
            return list((await session.execute(select(EvalQuestion))).scalars().all())

    async def run_retrieval(self) -> RetrievalMetrics:
        """For each question, retrieve and check where its relevant chunk lands."""
        results: list[tuple[list[str], str]] = []
        for q in await self._questions():
            hits = await self._retriever.retrieve(q.question)
            results.append(([h.chunk_id for h in hits], q.chunk_id))
        return retrieval_metrics(results)

    async def run_generation(self) -> GenerationScores:
        """For each question, generate an answer and judge its faithfulness + relevance."""
        questions = await self._questions()
        if not questions:
            return GenerationScores(0.0, 0.0)
        faith = relevance = 0.0
        for q in questions:
            result = await self._answer.answer(q.question)
            context = await self._context_for(result["citations"])
            scores = await self._judge.score(q.question, context, result["answer"])
            faith += scores.faithfulness
            relevance += scores.answer_relevance
        n = len(questions)
        return GenerationScores(faith / n, relevance / n)

    async def _context_for(self, citations: list[dict]) -> str:
        ids = [c["chunk_id"] for c in citations]
        async with self._db.session() as session:
            rows = (await session.execute(select(Chunk).where(Chunk.id.in_(ids)))).scalars().all()
        return "\n\n".join(r.text for r in rows)
