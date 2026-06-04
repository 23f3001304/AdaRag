"""Query endpoint: retrieve relevant chunks and generate a cited answer."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str


@router.post("/query")
async def query(request: Request, body: QueryRequest) -> dict:
    """Answer a question over the ingested corpus, with citations to source chunks."""
    return await request.app.state.answer.answer(body.query)
