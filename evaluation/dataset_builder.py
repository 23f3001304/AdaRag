"""Build and persist the golden eval set: generate one QA pair per stored chunk."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from core.db import Database
from core.models import Chunk, EvalQuestion
from evaluation.datasets import QAGenerator


class EvalSetBuilder:
    """Reads ingested chunks, generates a QA pair for each, and persists them as eval questions."""

    def __init__(self, generator: QAGenerator, db: Database) -> None:
        self._gen = generator
        self._db = db

    async def build(self, limit: int = 50) -> int:
        """Generate + persist QA pairs for up to ``limit`` chunks; returns how many were stored."""
        async with self._db.session() as session:
            chunks = (await session.execute(select(Chunk).limit(limit))).scalars().all()

        stored = 0
        async with self._db.session() as session:
            for ch in chunks:
                qa = await self._gen.from_chunk(ch.id, "", ch.text)
                if qa is None:
                    continue
                session.add(
                    EvalQuestion(
                        id=str(uuid.uuid4()),
                        document_id=ch.document_id,
                        chunk_id=ch.id,
                        question=qa.question,
                        answer=qa.answer,
                    )
                )
                stored += 1
            await session.commit()
        return stored
