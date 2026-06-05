"""Store for ingest-time clarifications: pending "who or what is this file about?" questions.

A clarification is created when the ambiguity detector can't pin a file's subject to a name. It is
answered later from the Ingest tab, which tags the document's chunks with the chosen entity so
retrieval can tell two people's photos apart (the answer/apply path lands in slice 2).
"""

from __future__ import annotations

import uuid

from core.db import Database
from core.models import Clarification


class ClarificationStore:
    """CRUD over pending clarifications, backed by Postgres."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(
        self, bucket: str, document_id: str, source: str, modality: str, subject: str, question: str
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
                )
            )
            await session.commit()
        return cid
