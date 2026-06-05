"""Clarifications API: list pending ingest disambiguation questions and answer / dismiss them."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["clarifications"])


class AnswerRequest(BaseModel):
    entity: str


def _row(c) -> dict:
    return {
        "id": c.id,
        "bucket": c.bucket,
        "source": c.source,
        "modality": c.modality,
        "subject": c.subject,
        "question": c.question,
        "candidates": json.loads(c.candidates or "[]"),
        "status": c.status,
    }


@router.get("/clarifications")
async def list_clarifications(request: Request, bucket: str | None = None) -> dict:
    """Pending clarifications (optionally one bucket), each with candidate answers."""
    items = await request.app.state.buckets.clarifications.list_pending(bucket)
    return {"clarifications": [_row(c) for c in items]}


@router.post("/clarifications/{cid}/answer")
async def answer_clarification(cid: str, body: AnswerRequest, request: Request) -> dict:
    """Apply an answer: tag the file's chunks with the chosen entity and resolve the question."""
    entity = body.entity.strip()
    if not entity:
        raise HTTPException(status_code=400, detail="entity is required")
    buckets = request.app.state.buckets
    clarification = await buckets.clarifications.get(cid)
    if clarification is None or clarification.status != "pending":
        raise HTTPException(status_code=404, detail="clarification not found")
    updated = await buckets.retag(clarification.bucket, clarification.document_id, entity)
    await buckets.clarifications.resolve(cid, "answered", entity)
    return {"ok": True, "chunks_updated": updated}


@router.post("/clarifications/{cid}/dismiss")
async def dismiss_clarification(cid: str, request: Request) -> dict:
    """Dismiss a clarification without tagging anything."""
    await request.app.state.buckets.clarifications.resolve(cid, "dismissed")
    return {"ok": True}
