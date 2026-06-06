"""Store for ingest-time clarifications: pending "who or what is this file about?" questions.

A clarification is created when the ambiguity detector can't pin a file's subject to a name. It is
answered later from the Ingest tab, which tags the document's chunks with the chosen entity so
retrieval can tell two people's photos apart (the answer/apply path lands in slice 2).
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select

from core.db import Database
from core.models import Clarification


class ClarificationStore:
    """CRUD over pending clarifications, backed by Postgres."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(
        self,
        bucket: str,
        document_id: str,
        source: str,
        modality: str,
        subject: str,
        question: str,
        candidates: list[str] | None = None,
    ) -> str:
        """Record a pending clarification for a file; returns its id."""
        cid = str(uuid.uuid4())
        async with self._db.session() as session:
            session.add(
                Clarification(
                    id=cid,
                    bucket=bucket,
                    document_id=document_id,
                    source=source,
                    modality=modality,
                    subject=subject,
                    question=question,
                    candidates=json.dumps(candidates or []),
                )
            )
            await session.commit()
        return cid

    async def list_pending(self, bucket: str | None = None) -> list[Clarification]:
        """Pending clarifications, oldest first, optionally scoped to one bucket."""
        query = select(Clarification).where(Clarification.status == "pending")
        if bucket:
            query = query.where(Clarification.bucket == bucket)
        async with self._db.session() as session:
            return list((await session.execute(query.order_by(Clarification.created_at))).scalars())

    async def get(self, cid: str) -> Clarification | None:
        async with self._db.session() as session:
            return await session.get(Clarification, cid)

    async def resolve(self, cid: str, status: str, answer: str = "") -> Clarification | None:
        """Mark a clarification answered or dismissed; returns the updated row (None if missing)."""
        async with self._db.session() as session:
            row = await session.get(Clarification, cid)
            if row is not None:
                row.status = status
                row.answer = answer
                await session.commit()
                await session.refresh(row)
            return row

    async def purge(self, bucket: str, source: str | None = None) -> None:
        """Drop clarifications for a deleted bucket (or one source within it)."""
        query = select(Clarification).where(Clarification.bucket == bucket)
        if source is not None:
            query = query.where(Clarification.source == source)
        async with self._db.session() as session:
            for row in (await session.execute(query)).scalars():
                await session.delete(row)
            await session.commit()

    async def drop_pending(self, bucket: str, source: str) -> None:
        """Drop pending clarifications for a (bucket, source) - used when re-ingesting a file.

        Answered/dismissed rows stay (their retag is applied to the new doc by the user's choice).
        """
        query = (
            select(Clarification)
            .where(Clarification.bucket == bucket)
            .where(Clarification.source == source)
            .where(Clarification.status == "pending")
        )
        async with self._db.session() as session:
            for row in (await session.execute(query)).scalars():
                await session.delete(row)
            await session.commit()
