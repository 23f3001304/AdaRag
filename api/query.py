"""Query endpoint: retrieve relevant chunks and generate a cited answer."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str
    bucket: str = "default"


@router.post("/query")
async def query(request: Request, body: QueryRequest) -> dict:
    """Answer a question over a bucket's corpus, with citations to source chunks."""
    answer = request.app.state.buckets.services(body.bucket).answer
    return await answer.answer(body.query)
